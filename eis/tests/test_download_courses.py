from unittest import mock

# things we're testing
from eis.data.download_courses import BACHELOR_DISCIPLINES_URL
from eis.data.download_courses import SEARCH_FACETS_URL
from eis.data.download_courses import SEARCH_URL
from eis.data.download_courses import PAGE_SIZE
from eis.data.download_courses import discover_disciplines
from eis.data.download_courses import discover_level_count
from eis.data.download_courses import _discover_courses
from eis.data.download_courses import discover_courses
from eis.data.download_courses import standardise_ddsl
from eis.data.download_courses import download_courses

# things we're obviously not testing
from eis.data.download_courses import os
from eis.data.download_courses import requests
from eis.data.download_courses import defaultdict
from eis.data.download_courses import SortedList

PATH = 'eis.data.download_courses.{}'  # For mocking


def test_urls_are_online():
    for url in (BACHELOR_DISCIPLINES_URL, SEARCH_FACETS_URL, SEARCH_URL):
        r = requests.get(url)
        assert r.status_code != 404, f'{url} giving 404'


def test_page_size_is_ten():
    assert PAGE_SIZE == 10


@mock.patch(PATH.format('BeautifulSoup'))
def test_discover_disciplines(_mocked_soup):
    n = 3  # number of results returned each time
    the_id = 123456 # hide this in the URL, and check you find it again
    _mocked_anchor = mock.MagicMock()  # magic to allow subscripting
    _anchor = {'href': f'/a/url/with/{the_id}/hidden'}
    _mocked_anchor.find().__getitem__.side_effect = _anchor.__getitem__
    _mocked_soup().find().find_all.return_value = [_mocked_anchor]*3
    mocked_session = mock.Mock()
    disciplines = discover_disciplines(mocked_session, 'www.example.com')
    n_have_parents = 0
    for d in disciplines:
        assert d['discipline_id'] == the_id
        assert type(d) is dict
        has_parent = type(d['parent']) is dict
        assert has_parent or d['parent'] is None
        n_have_parents += int(has_parent)
    assert len(disciplines) == n*(n + 1)  # 3 sets of 3 children, plus parent per set
    assert n_have_parents == n*n


def test_discover_level_count():
    # assert all elements returned
    mocked_session = mock.MagicMock()  # magic to allow subscripting
    mocked_session.get().json()['lv'].items.return_value = [('bachelor', 20), ('master', 2),
                                                            ('phd', 45), ('other', 22),
                                                            ('otherother', 34)]
    levels, total_count = set(), 0
    for level, count in discover_level_count(mocked_session, 'an_id'):
        levels.add(level)
        total_count += count
    assert levels == {'bachelor', 'master', 'phd', 'other', 'otherother'}
    assert total_count == 123


def test__discover_courses():
    mocked_session = mock.Mock()
    bachelor_courses = [{'level': 'bachelor', 'name': 'physics'},
                        {'level': 'bachelor', 'name': 'maths'}]
    master_courses = [{'level': 'master', 'name': 'physics'},
                      {'level': 'master', 'name': 'chemistry'},
                      {'level': 'master', 'name': 'economics'}]
    mocked_session.get().json.return_value = bachelor_courses + master_courses
    # filter bachelor courses
    for total in range(10, 203):
        n_pages = (total // PAGE_SIZE)+int(total % PAGE_SIZE > 0)
        n = 0
        for course in _discover_courses(mocked_session, di='123', lvl='bachelor', total=total):
            assert course in bachelor_courses
            n += 1
        assert n == n_pages*len(bachelor_courses)

        # filter master courses
        n = 0
        for course in _discover_courses(mocked_session, di='123', lvl='master', total=total):
            assert course in master_courses
            n += 1
        assert n == n_pages*len(master_courses)


@mock.patch(PATH.format('discover_level_count'))
@mock.patch(PATH.format('_discover_courses'))
def test_discover_courses(mocked___discover_courses, mocked_discover_level_count):
    course = {"one_boring_field": "something", "another_boring_field": "something",
              "bonus_field": "something"}
    n_courses = 3
    mocked_discover_level_count.return_value = [('bachelor', 12), ('phd', 21)]
    mocked___discover_courses.return_value = [course.copy() for i in range(0, n_courses)]
    disciplines = [{'discipline_id': 0, 'discipline_title': 'Zero', 'parent': None},
                   {'discipline_id': 1, 'discipline_title': 'One', 'parent': 0},
                   {'discipline_id': 2, 'discipline_title': 'Two', 'parent': 0}]
    n = 0
    keys = set()
    mocked_session = mock.Mock()
    for key, course in discover_courses(mocked_session, disciplines,
                                        boring_fields=('one_boring_field', 'another_boring_field')):
        # Test boring fields dropped, and discipline fields added    
        assert set(course.keys()) == set(['bonus_field', 'discipline_id', 'discipline_title'])
        keys.add(key)
        n += 1
    assert keys == set([(1, 'bachelor'), (2, 'bachelor'),  # Note 'Zero' was dropped as no parent
                        (1, 'phd'), (2, 'phd')])
    assert n == len(keys)*n_courses


def test_standardise_ddsl():
    ddsl = defaultdict(SortedList)
    expected_output = {"a": [1, 2, 3, 4],
                       "b": ["a", "b", "c"]}
    # Insert elements in a jumbled order
    ddsl["a"].add(2)
    ddsl["a"].add(1)
    ddsl["a"].add(3)
    ddsl["a"].add(4)
    ddsl["b"].add('b')
    ddsl["b"].add('c')
    ddsl["b"].add('a')
    assert standardise_ddsl(ddsl) == expected_output
