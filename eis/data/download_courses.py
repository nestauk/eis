import requests
import cachecontrol
from bs4 import BeautifulSoup
from sortedcontainers import SortedList
from collections import defaultdict
import os
import json

DATA_PATH = '../../data/raw/courses/'  # Path for writing data to
BACHELOR_DISCIPLINES_URL = "https://www.bachelorsportal.com/disciplines/"
SEARCH_FACETS_URL = "https://search-facets.prtl.co"
SEARCH_URL = "https://search.prtl.co/2018-07-23/"
PAGE_SIZE = 10  # This is fixed, nothing I can do about it


def discover_disciplines(session, url, section_id='DisciplineSpotlight', parent=None):
    """Recursively discover all disciplines on studyportal.

    Args:
        session (requests.Session, or equivalent): session for making requests.
        url (str): A valid studyportal disciplines URL.
        section_id (str): Do not change this, it is used for recursion.
        parent (int): Do not change this, it is used for recursion.
    Returns:
        disciplines (list of dict): Discipline metadata, including parent
                                    metadata if applicable.
    """
    # Parse the HTML for this URL
    r = session.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, features="lxml")
    # Extract discipline metadata from the indicated section
    disciplines = []
    section = soup.find('section', id=section_id)
    for item in section.find_all('li'):
        anchor = item.find('a', href=True)
        href = anchor['href']
        this_discipline = {'discipline_id': int(href.split('/')[-2]),  # The discipline ID is hidden in the href
                           'discipline_title': anchor.text.strip(),
                           'parent': parent}
        disciplines.append(this_discipline)
        # For disciplines (rather than subdisciplines), extract subdisciplines
        if parent is None:
            disciplines += discover_disciplines(session, href,
                                                section_id='SubdisciplinesList', parent=this_discipline)
    return disciplines


def discover_level_count(session, discipline_id):
    """Discover degree level counts by discipline.

    Args:
        session (requests.Session, or equivalent): session for making requests.
        discipline_id (int): studyportal discipline id.
    Returns:
        (degree_level, count) (str, int): Degree level (e.g. bachelor, master, etc),
                                          and the count of that degree level for
                                          the specified discipline id.
    """
    r = session.get(SEARCH_FACETS_URL, params={"q": f"di-{discipline_id}", "facets": '["lv"]'})
    r.raise_for_status()
    for degree_level, count in r.json()['lv'].items():
        yield degree_level, count


def _discover_courses(session, di, lvl, total):
    """Hidden method for discovering courses on studyportal.

    Args:
        session (requests.Session, or equivalent): session for making requests.
        di (int): Discipline id number.
        lvl (str): Degree level string (e.g. bachelor, master, etc)
        total (int): The total number of courses for this combination of (di, lvl).
    Yields:
        course (dict): Raw course data, for an individual course from studyportal.
    """
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
    """Write data to json at a given path.

    Args:
        data (json-like): Data to write as json.
        path_to_filename (str): Path to the filename, including the filename.
    """
    with open(path_to_filename, 'w') as f:
        _data = json.dumps(data)
        f.write(_data)


def flush(courses, di, lvl, count):
    """Write to disk under the path di/lvl/di-lvl-count.json

    Args:
        courses (list of dict): List of rawish course data.
        di (int): Discipline id number.
        lvl (str): Degree level string (e.g. bachelor, master, etc)
        count (int): Count to label the output file with.
    """
    path = f'{DATA_PATH}/{di}/{lvl}/'
    if not os.path.exists(path):
        os.makedirs(path)
    write_json(courses[(di, lvl)], f'{path}/{di}-{lvl}-{count}.json')


def discover_courses(session, disciplines, boring_fields=("listing_type", "enhanced", "logo")):
    """
    Discover all courses on study portal.

    Args:
        session (requests.Session or equivalent): session for making requests.
        disciplines (list of dict): As returned from discover_disciplines.
        boring_fields (tuple): Iterable of keys to ignore in the course data.
                               These are likely to be uninteresting data fields.
    yields:
        (key, course) (tuple, dict): A composite key indicating the discipline id
                                     and degree level, and rawish course data
                                     for an individual course from studyportal
                                     (rawish as it additionally has discipline info)
    """
    for d in disciplines:
        if d['parent'] is None:
            continue
        di = d['discipline_id']
        for degree_level, count in discover_level_count(session, di):
            key = (di, degree_level)
            for course in _discover_courses(session, di, degree_level, count):
                # Ignore boring fields
                for field in boring_fields:
                    try:
                        course.pop(field)
                    except KeyError:
                        pass
                # Append discipline metadata
                course['discipline_title'] = d['discipline_title']
                course['discipline_id'] = di
                yield key, course


def standardise_ddsl(ddsl):
    """Converts defauldict(SortedList) to dict of list, ready for json serialization"""
    return {k: list(v) for k, v in ddsl.items()}


def download_courses(flush_count=1000):
    """Downloads all studyportal course data to the global DATA_PATH path,
    including metadata for convenience analysis of course data. The output
    directory structure under DATA_PATH/courses will look like:

    38                               <--- discipline #38
    ├── bachelor
    │   ├── 38-bachelor-1000.json    <--- the first 1000 BACHELOR courses for discipline #38
    │   └── 38-bachelor-2000.json    <--- up to the next 1000 BACHELOR courses for discipline #38
    ├── master
    │   ├── 38-master-1000.json      <--- the first 1000 MASTER courses for discipline #38
    │   └── 38-master-2000.json      <--- up to the next 1000 MASTER courses for discipline #38
    ├── phd
    │   └── 38-phd-1000.json         <--- up to the first 1000 PHD courses for discipline #38
    ├── preparation
    │   └── 38-preparation-1000.json <--- up to the first 1000 PREPARATION courses for discipline #38
    └── short
        └── 38-short-1000.json       <--- up to the first 1000 SHORT courses for discipline #38


    Important/interesting notes:
    1) Courses can have multiple disciplines. The average number of disciplines per course is 1.79.
    2) There are over 170k courses, and over 200 disciplines.
    3) The same discipline ontology is used for all course levels (Bachelor, PhD, etc)
    4) The discipline ontology is nested at 2 levels.

    There are three metadata files to help you navigate the data:

    1) discipline_dictionary.json: Metadata for disciplines, including disclipline name and parent name
    2) course_discipline_lookup.json: Look-up table of course_id --> [discipline ids]
    3) discipline_course_lookup.json: Look-up table of discipline_id --> [course ids]

    Args:
        flush_count (int): Maximum number of courses in any file saved to disk.
    """
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
        # Flush if threshold count is reached
        if len(courses[key]) == flush_count:
            course_count[key] += flush_count
            flush(courses, di, lvl, course_count[key])
            del courses[key]  # Now we've flushed, free up some memory
    # Flush remaining collections of courses that never went over flush threshold
    for (di, lvl) in courses:
        key = (di, lvl)
        flush(courses, di, lvl, course_count[key] + flush_count)
        del courses[key]  # Not really necessary, but not unnecessary

    # Reformat defaultdict(SortedList) ready for json serialization
    course_discipline_lookup = standardise_ddsl(course_discipline_lookup)
    discipline_course_lookup = standardise_ddsl(discipline_course_lookup)

    # Save the handy lookup tables
    write_json(course_discipline_lookup, f'{DATA_PATH}/course_discipline_lookup.json')
    write_json(discipline_course_lookup, f'{DATA_PATH}/discipline_course_lookup.json')
    write_json(disciplines, f'{DATA_PATH}/discipline_dictionary.json')


if __name__ == '__main__':
    # Example of how to run this script...
    download_courses()
