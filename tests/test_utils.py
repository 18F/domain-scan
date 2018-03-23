import argparse
import sys
import pytest
from .context import utils  # noqa
from utils import utils as subutils


def get_default_false_values(parser):
    # Get these from the parser rather than having to keep a manual list.
    optional_actions = parser._get_optional_actions()
    default_false_values = {}
    for oa in optional_actions:
        if oa.nargs == 0 and oa.const is True and oa.default is False:
            default_false_values.update(**{oa.dest: False})
    return default_false_values


def get_args_with_mandatory_values(parser):
    # Get these from the parser rather than having to keep a manual list.
    optional_actions = parser._get_optional_actions()
    mandatory_value_args = []
    for oa in optional_actions:
        if oa.nargs in ("?", "+", 1):
            mandatory_value_args.append(oa.dest)
    return mandatory_value_args


gather_default_false_values = get_default_false_values(
    subutils.build_gather_options_parser([]))
gather_args_with_mandatory_values = get_args_with_mandatory_values(
    subutils.build_gather_options_parser([]))
scan_default_false_values = get_default_false_values(
    subutils.build_scan_options_parser([]))
scan_args_with_mandatory_values = get_args_with_mandatory_values(
    subutils.build_scan_options_parser([]))


@pytest.mark.parametrize("args,expected", [
    (
        "gather dap --dap=someurl --suffix=.gov",
        {
            "_": ["dap"],
            "dap": "someurl",
            "suffix": ".gov",
            **gather_default_false_values,
        }
    ),
    (
        "".join([
            "gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv"]),
        {
            "_": ["dap"],
            **gather_default_false_values,
            "suffix": ".gov",
            "dap": "https://analytics.usa.gov/data/live/sites-extended.csv",
        }
    ),
    (
        "".join([
            "./gather censys,dap,private --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
            " --private=/path/to/private-research.csv --parents=",
            "https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv",
        ]),
        {
            '_': ['censys,dap,private'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'private': '/path/to/private-research.csv',
            'parents': 'https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv',
        }
    ),
    (
        "".join([
            "./gather censys,dap,private --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
            " --private=/path/to/private-research.csv --parents=",
            "https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv",
        ]),
        {
            '_': ['censys,dap,private'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'private': '/path/to/private-research.csv',
            'parents': 'https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv',
        }
    ),
    (
        "".join([
            "./gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
            " --ignore-www",
        ]),
        {
            '_': ['dap'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'ignore_www': True,
        }
    ),
    (
        "".join([
            "./gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
            " --include-parents",
        ]),
        {
            '_': ['dap'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'include_parents': True,
        }
    ),
    (
        "".join([
            "./gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
        ]),
        {
            '_': ['dap'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
        }
    ),
    (
        "".join([
            "./gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv",
            " --debug",
        ]),
        {
            '_': ['dap'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'debug': True,
        }
    ),
])
def test_options_for_gather(monkeypatch, args, expected):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    result = subutils.options_for_gather()
    assert result == expected


@pytest.mark.parametrize("args", [
    "./gather --yo --suffix=.gov",
])
@pytest.mark.xfail(raises=argparse.ArgumentTypeError)
def test_options_for_gather_no_gatherer(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options_for_gather()


@pytest.mark.parametrize("args", [
    "./gather censys --suffix",
    "./gather dap,censys --dap --suffix=.gov",
    "./gather dap --dap --suffix=.gov",
    "./gather dap --dap=something.url --suffix=.gov --parents",
])
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_for_gather_missing_arg_parameter(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options_for_gather()


@pytest.mark.parametrize("args", [
    "./gather censys --a11y_config=file.json --suffix=.gov",
    "./gather dap --dap=file.json --suffix=.gov --cache",
    "./gather dap --dap=file.json --suffix=.gov --timeout=10",
])
@pytest.mark.xfail(raises=argparse.ArgumentTypeError)
def test_options_for_gather_arg_mismatch(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options_for_gather()


@pytest.mark.parametrize("arg", gather_args_with_mandatory_values)
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_for_gather_missing_mandatory(monkeypatch, arg):
    command = "./gather censys --suffix=.gov --%s" % arg.replace("_", "-")
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_gather()
    command = "./gather censys --suffix=.gov --%s=" % arg.replace("_", "-")
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_gather()


@pytest.mark.xfail(raises=argparse.ArgumentTypeError)
def test_options_for_scan_no_target(monkeypatch):
    command = "./scan --scan=a11y"
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_scan()


def test_options_for_scan_basic(monkeypatch):
    command = "./scan example.org --scan=a11y"
    monkeypatch.setattr(sys, "argv", command.split(" "))
    result = subutils.options_for_scan()
    assert result == {
        "_": "example.org",
        "scan": "a11y",
        **scan_default_false_values,
    }


@pytest.mark.parametrize("arg", scan_args_with_mandatory_values)
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_for_scan_missing_mandatory(monkeypatch, arg):
    command = "./gather example.org --scan=a11y --%s" % arg.replace("_", "-")
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_scan()
    command = "./gather example.org --scan=a11y --%s=" % arg.replace("_", "-")
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_scan()


@pytest.mark.xfail(raises=argparse.ArgumentTypeError)
def test_options_for_scan_lambda_profile_no_lambda(monkeypatch):
    command = "./scan example.org --scan=a11y --lambda-profile=something"
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_scan()
