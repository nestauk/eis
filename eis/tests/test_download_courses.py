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


def test_urls_are_online():
    for url in (BACHELOR_DISCIPLINES_URL, SEARCH_FACETS_URL, SEARCH_URL):
        r = requests.get(url)
        assert r.status_code != 404, f'{url} giving 404'


def test_page_size_is_ten():
    assert PAGE_SIZE == 10


def test_discover_disciplines():
    # test shape and len are correct
    pass


def test_discover_level_count():
    # assert all elements returned
    pass


def test__discover_courses():
    # test no double-counting
    pass


def test_discover_courses():
    # test boring fields are dropped
    # test additional fields are applied    
    pass


def test_standardise_ddsl():
    # test as expected
    pass


def test_download_courses():
    # test flush count
    # test write_json count
    pass
