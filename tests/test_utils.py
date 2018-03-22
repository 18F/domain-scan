import argparse
import sys
import pytest
from .context import utils  # noqa
from utils import utils as subutils


def get_gather_default_false_values():
    # Get these from the parser rather than having to keep a manual list.
    parser = subutils.build_gather_options_parser([])
    optional_actions = parser._get_optional_actions()
    default_false_values = {}
    for oa in optional_actions:
        if oa.nargs == 0 and oa.const is True and oa.default is False:
            default_false_values.update(**{oa.dest: False})
    return default_false_values


def get_gather_args_with_mandatory_values():
    # Get these from the parser rather than having to keep a manual list.
    parser = subutils.build_gather_options_parser([])
    optional_actions = parser._get_optional_actions()
    mandatory_value_args = []
    for oa in optional_actions:
        if oa.nargs in ("?", "+", 1):
            mandatory_value_args.append(oa.dest)
    return mandatory_value_args


gather_default_false_values = get_gather_default_false_values()
gather_args_with_mandatory_values = get_gather_args_with_mandatory_values()


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
            " --cache",
        ]),
        {
            '_': ['dap'],
            **gather_default_false_values,
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'cache': True,
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
])
@pytest.mark.xfail(raises=argparse.ArgumentTypeError)
def test_options_for_gather_arg_mismatch(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options_for_gather()


@pytest.mark.parametrize("args", gather_args_with_mandatory_values)
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_for_gather_missing_mandatory(monkeypatch, args):
    command = f"./gather censys --suffix=.gov --{args}"
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_gather()
    command = f"./gather censys --suffix=.gov --{args}="
    monkeypatch.setattr(sys, "argv", command.split(" "))
    subutils.options_for_gather()
