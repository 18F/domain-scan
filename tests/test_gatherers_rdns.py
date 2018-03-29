import pytest
from .context import gatherers  # noqa
from gatherers import rdns



@pytest.mark.parametrize("data,expected", [
    (
        [
            '{"value": "18f.gov"}',
            '{"value": "123.112.18f.gov"}',
            '{"value": "123.112.23.23"}',
            '{"value": "u-123.112.23.23"}',
            '{"value": "123.112.fed.us"}',
            '{"value": "something.fed.us"}',
            '{"value": "18f.gsa.gov"}',
        ],
        [
            "18f.gov",
            "something.fed.us",
            "18f.gsa.gov"
        ]
    ),
])
def test_query_for(data, expected):
    result = rdns.process_lines(data, rdns.ip_filter, rdns.number_filter)
    assert list(result) == expected
