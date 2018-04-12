import pytest
from argparse import ArgumentTypeError

from scanners import analytics


@pytest.mark.parametrize("opts,args,correct_opts, correct_unknown", [
    (
        ["--analytics", "tests/data/domains.csv"],
        {},
        {"analytics_domains": ["achp.gov", "acus.gov"]},
        [],
    ),
    (
        ["--noop-delay", "4", "--analytics", "tests/data/domains.csv"],
        {"something": "else"},
        {
            "analytics_domains": ["achp.gov", "acus.gov"],
        },
        ["--noop-delay", "4"],
    ),
])
def test_handle_scanner_args(args, opts, correct_opts, correct_unknown):
    # This only handles a basic case and makes sure it's handed off correctly;
    # tests for the scanner argument parsers themselves should be in the tests
    # for those scanners.
    opts, unknown = analytics.handle_scanner_args(opts, args)
    # pytest.set_trace()
    assert opts == correct_opts
    assert unknown == correct_unknown


@pytest.mark.parametrize("opts,args,correct_opts, correct_unknown", [
    (
        ["--analytics", "tests/data/domains.tsv"],
        {},
        {"analytics_domains": ["achp.gov", "acus.gov"]},
        [],
    ),
])
@pytest.mark.xfail(raises=ArgumentTypeError)
def test_handle_scanner_args_notcsv(args, opts, correct_opts, correct_unknown):
    # This only handles a basic case and makes sure it's handed off correctly;
    # tests for the scanner argument parsers themselves should be in the tests
    # for those scanners.
    opts, unknown = analytics.handle_scanner_args(opts, args)
    assert opts == correct_opts
    assert unknown == correct_unknown


@pytest.mark.parametrize("opts,args,correct_opts, correct_unknown", [
    (
        ["--noop-delay", "4", "--analytics", "path/to/nowhere.csv"],
        {"something": "else"},
        {
            "analytics_domains": ["achp.gov", "acus.gov"],
        },
        ["--noop-delay", "4"],
    ),
])
@pytest.mark.xfail(raises=FileNotFoundError)
def test_handle_scanner_args_fnf(args, opts, correct_opts, correct_unknown):
    # This only handles a basic case and makes sure it's handed off correctly;
    # tests for the scanner argument parsers themselves should be in the tests
    # for those scanners.
    opts, unknown = analytics.handle_scanner_args(opts, args)
    assert opts == correct_opts
    assert unknown == correct_unknown
