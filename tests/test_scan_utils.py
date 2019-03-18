import os
import sys
from collections import namedtuple
from pathlib import Path
from .context import utils, scanners  # noqa
from utils import scan_utils
from scanners import analytics, noop

import pytest

MockScanner = namedtuple("MockScanner", ["workers"])


@pytest.mark.parametrize("names,expected", [
    (
        ["noop"],
        ([noop])
    )
])
def test_build_scanner_list(names, expected):
    assert scan_utils.build_scanner_list(names) == expected


@pytest.mark.xfail(raises=ImportError)
@pytest.mark.parametrize("names", [
    ["asdf"],
    ["missing_scanner"],
])
def test_build_scan_lists_import_error(names):
    scan_utils.build_scanner_list(names)


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


@pytest.mark.parametrize("scans,opts,args,correct_opts, correct_unknown", [
    (
        [noop],
        {},
        ["--noop-delay", "4"],
        {"noop_delay": 4},
        [],
    ),
    (
        [noop, analytics],
        {"something": "else"},
        ["--noop-delay", "4", "--analytics", "tests/data/domains.csv"],
        {
            "analytics_domains": ["achp.gov", "acus.gov"],
            "noop_delay": 4,
            "something": "else"
        },
        [],
    ),
])
def test_handle_scanner_arguments(scans, opts, args, correct_opts, correct_unknown):
    # This only handles a basic case and makes sure it's handed off correctly;
    # tests for the scanner argument parsers themselves should be in the tests
    # for those scanners.
    opts, unknown = scan_utils.handle_scanner_arguments(scans, opts, args)
    assert opts == correct_opts
    assert unknown == correct_unknown


@pytest.mark.parametrize("scanner,options,w_default,w_max,expected", [
    (
        MockScanner(workers=23),
        {},
        5,
        100,
        23,
    ),
    (
        MockScanner(workers=23),
        {"serial": True},
        5,
        100,
        1,
    ),
    (
        (1, 2),
        {"serial": False},
        5,
        4,
        4,
    ),
    (
        (1, 2),
        {"serial": False},
        3,
        4,
        3,
    ),
])
def test_determine_scan_workers(scanner, options, w_default, w_max, expected):
    result = scan_utils.determine_scan_workers(scanner, options, w_default,
                                               w_max)
    assert result == expected


@pytest.mark.parametrize("args,expected", [
    (
        "./scan 18f.gsa.gov --scan=analytics --analytics=http://us.ie/de.csv",
        (
            {
                "domains": "18f.gsa.gov",
                "cache": False,
                "debug": False,
                "lambda": False,
                "meta": False,
                "scan": "analytics",
                "no_fast_cache": False,
                "serial": False,
                "sort": False,
                "dmarc": False,
                "mx": False,
                "starttls": False,
                "spf": False,
                "output": "./",
                "_": {
                    "cache_dir": "./cache",
                    "report_dir": "./",
                    "results_dir": "./results"
                }
            },
            ["--analytics=http://us.ie/de.csv"]
        )
    ),
    (
        "./scan tests/data/domains.csv --scan=noopabc",
        (
            {
                "domains": "tests/data/domains.csv",
                "cache": False,
                "debug": False,
                "lambda": False,
                "meta": False,
                "scan": "noopabc",
                "no_fast_cache": False,
                "serial": False,
                "sort": False,
                "dmarc": False,
                "mx": False,
                "starttls": False,
                "spf": False,
                "output": "./",
                "_": {
                    "cache_dir": "./cache",
                    "report_dir": "./",
                    "results_dir": "./results"
                }
            },
            []
        )
    ),
])
def test_options(monkeypatch, args, expected):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    result = scan_utils.options()
    assert result == expected
