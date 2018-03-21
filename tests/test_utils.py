import argparse
import sys
import pytest
from .context import utils  # noqa
from utils import utils as subutils


@pytest.mark.parametrize("args,expected", [
    ("gather dap", {"_": ["dap"]}),
    (
        "".join([
            "gather dap --suffix=.gov --dap=",
            "https://analytics.usa.gov/data/live/sites-extended.csv"]),
        {
            "_": ["dap"],
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
            " --a11y_config=something.json"
        ]),
        {
            '_': ['censys,dap,private'],
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'private': '/path/to/private-research.csv',
            'parents': 'https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv',
            'a11y_config': 'something.json'
        }
    ),
])
def test_options(monkeypatch, args, expected):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    result = subutils.options()
    assert result == expected


@pytest.mark.parametrize("args", [
    "./gather a11y --suffix=.gov --a11y_config=shouldbejson.fail",
    "./gather a11y --suffix=.gov --a11y_redirects=shouldbeyml.fail",
])
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_bad_arg(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options()


@pytest.mark.parametrize("args", [
    "./gather a11y --a11y_config",
    "./gather a11y --a11y_redirects",
    "./gather a11y --analytics",
])
@pytest.mark.xfail(raises=argparse.ArgumentError)
def test_options_missing_arg_parameter(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    subutils.options()
