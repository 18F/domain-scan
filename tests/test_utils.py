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
            " --private=/path/to/private-research.csv --parents="
            "https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv",
            " --export"
        ]),
        {
            '_': ['censys,dap,private'],
            'suffix': '.gov',
            'dap': 'https://analytics.usa.gov/data/live/sites-extended.csv',
            'private': '/path/to/private-research.csv',
            'parents': 'https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv',
            'export': True
        }
    ),
])
def test_options(monkeypatch, args, expected):
    monkeypatch.setattr(sys, "argv", args.split(" "))
    result = subutils.options()
    pytest.set_trace()
    assert result == expected
