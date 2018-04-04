import os
import pytest
from pathlib import Path
from .context import utils, scanners  # noqa
from utils import scan_utils
from scanners import noop, noopabc


@pytest.mark.parametrize("names,expected", [
    (
        ["noop", "noopabc"],
        ([noopabc.Scanner], [noop])
    )
])
def test_build_scan_lists(names, expected):
    assert scan_utils.build_scan_lists(names) == expected


@pytest.mark.xfail(raises=ImportError)
@pytest.mark.parametrize("names", [
    ["asdf"],
    ["missing_scanner"],
])
def test_build_scan_lists_import_error(names):
    scan_utils.build_scan_lists(names)


@pytest.mark.parametrize("arg,suffix,expected", [
    (
        "whatever",
        None,
        ["whatever"]
    ),
    (
        Path(Path(__file__).parent, "data", "domains.csv"),
        None,
        ["achp.gov", "acus.gov"]
    ),
    (
        Path(Path(__file__).parent, "data",
             "domains_no_suffixes.csv"),
        ".gov",
        ["achp.gov", "acus.gov"]
    ),
    (
        Path(Path(__file__).parent, "data",
             "domains_no_suffixes.csv"),
        "gov",
        ["achp.gov", "acus.gov"]
    ),
])
def test_domains_from(arg, suffix, expected):
    result = list(scan_utils.domains_from(arg, domain_suffix=suffix))
    assert result == expected


@pytest.mark.parametrize("arg,suffix,expected", [
    (
        Path(Path(__file__).parent, "data",
             "domains_no_suffixes.tab"),
        "gov",
        ["achp.gov", "acus.gov"]
    ),
])
@pytest.mark.xfail(raises=TypeError)
def test_domains_from_type_error(arg, suffix, expected):
    list(scan_utils.domains_from(arg, domain_suffix=suffix))


@pytest.mark.parametrize("domains,cache,expected", [
    (
        "whatever.gov",
        "cache",
        "whatever.gov"
    ),
    (
        "tests/data/domains.csv",
        "cache",
        Path(os.path.curdir, "tests/data/domains.csv").resolve()
    ),
])
def test_handle_domains_argument(domains, cache, expected):
    result = scan_utils.handle_domains_argument(domains, cache)
    assert result == expected


@pytest.mark.xfail(raises=IOError)
def test_handle_domains_argument_io_error():
    scan_utils.handle_domains_argument("http://thing.notarealtld", "./cache")


@pytest.mark.xfail(raises=FileNotFoundError)
def test_handle_domains_argument_fnf_error():
    scan_utils.handle_domains_argument("notarealfile.csv", "./cache")
