import requests
import cachecontrol
from bs4 import BeautifulSoup
from sortedcontainers import SortedList
from collections import defaultdict
import os
import json

DATA_PATH = '../data/raw/'
BACHELOR_DISCIPLINES_URL = "https://www.bachelorsportal.com/disciplines/"
SEARCH_FACETS_URL = "https://search-facets.prtl.co"
SEARCH_URL = "https://search.prtl.co/2018-07-23/"
PAGE_SIZE = 10  # This is fixed, nothing I can do about it


def discover_disciplines(session, url, section_id='DisciplineSpotlight', parent=None):
    """Returns discipline-->subdiscipline mapping"""
    r = session.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, features="lxml")

    disciplines = []
    section = soup.find('section', id=section_id)
    for item in section.find_all('li'):
        anchor = item.find('a', href=True)
        href = anchor['href']
        this_discipline = {'discipline_id': int(href.split('/')[-2]),
                           'discipline_title': anchor.text.strip(),
                           'parent': parent}
        disciplines.append(this_discipline)
        if parent is None:
            disciplines += discover_disciplines(session, href,
                                                section_id='SubdisciplinesList', parent=this_discipline)
    return disciplines


def discover_level_count(session, discipline_id):
    """Returns degree-level-->total-count mapping by discipline"""
    r = session.get(SEARCH_FACETS_URL, params={"q": f"di-{discipline_id}", "facets": '["lv"]'})
    r.raise_for_status()
    for degree_level, count in r.json()['lv'].items():
        yield degree_level, count


def _discover_courses(session, di, lvl, total):
    """"""
    query_string = '|'.join((f'di-{di}',   # Discipline
                             'en-3002',    # Don't know what this is, could be a mechanism for rate limiting
                             f'lv-{lvl}',  # Degree level
                             'tc-EUR',     # Currency
                             'uc-30',      # Don't know what this is
                             'ur-38'))     # Don't know what this is
    n_pages = (total // PAGE_SIZE) + (total % PAGE_SIZE > 0)
    for page in range(0, n_pages):
        r = session.get(SEARCH_URL, params={'start': page*PAGE_SIZE, 'q': query_string})
        r.raise_for_status()
        for course in r.json():
            # Don't double count sublevels (e.g. preparation is a level & also incl under bachelor)
            if course['level'] != lvl:
                continue
            yield course


def write_json(data, path_to_filename):
    with open(path_to_filename, 'w') as f:
        _data = json.dumps(data)
        f.write(_data)


def flush(courses, di, lvl, count):
    """Write to disk under di/lvl/di-lvl-count.json"""
    path = f'{DATA_PATH}/{di}/{lvl}/'
    if not os.path.exists(path):
        os.makedirs(path)
    write_json(courses[(di, lvl)], f'{path}/{di}-{lvl}-{count}.json')


def discover_courses(session, disciplines, boring_keys=("listing_type", "enhanced", "logo")):
    for d in disciplines:
        if d['parent'] is None:
            continue
        di = d['discipline_id']
        for degree_level, count in discover_level_count(session, di):
            for course in _discover_courses(session, di, degree_level, count):
                for boring_key in boring_keys:
                    course.pop(boring_key)
                course['discipline_title'] = d['discipline_title']
                course['discipline_id'] = di
                key = (di, degree_level)
                yield key, course


def standardise_ddsl(ddsl):
    return {k: list(v) for k, v in ddsl.items()}


def download_courses(flush_count=1000):
    if not os.path.exists(DATA_PATH):
        raise OSError(f'Output path {DATA_PATH} does not exist')

    session = cachecontrol.CacheControl(requests.Session())
    disciplines = discover_disciplines(session, BACHELOR_DISCIPLINES_URL)

    # Output containers
    courses = defaultdict(list)  # Flushable course container
    course_count = defaultdict(int)  # Count of all courses, for book-keeping
    course_discipline_lookup = defaultdict(SortedList)  # Course-discipline look-up
    discipline_course_lookup = defaultdict(SortedList)  # ...and the reverse look-up
    for (di, lvl), course in discover_courses(session, disciplines):
        key = (di, lvl)
        ci = course['id']
        courses[key].append(course)
        course_discipline_lookup[ci].add(di)
        discipline_course_lookup[di].add(ci)
        if len(courses[key]) == flush_count:
            course_count[key] += flush_count
            flush(courses, di, lvl, course_count[key])
            del courses[key]
            break
    for (di, lvl) in courses:
        key = (di, lvl)
        flush(courses, di, lvl, course_count[key] + flush_count)

    course_discipline_lookup = standardise_ddsl(course_discipline_lookup)
    discipline_course_lookup = standardise_ddsl(discipline_course_lookup)

    # Save the handy lookup tables
    write_json(course_discipline_lookup, f'{DATA_PATH}/course_discipline_lookup.json')
    write_json(discipline_course_lookup, f'{DATA_PATH}/discipline_course_lookup.json')
    write_json(disciplines, f'{DATA_PATH}/discipline_dictionary.json')


if __name__ == '__main__':
    download_courses()
