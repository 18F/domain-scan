import pytest
from .context import gatherers  # noqa
from gatherers import censys


CENSYS_ONE_SUFFIX_QUERY = "\n".join([
    "SELECT",
    "    parsed.subject.common_name,",
    "    parsed.extensions.subject_alt_name.dns_names",
    "FROM",
    "    `censys-io.certificates_public.certificates`,",
    "    UNNEST(parsed.subject.common_name) AS common_names,",
    "    UNNEST(parsed.extensions.subject_alt_name.dns_names) AS sans",
    "WHERE",
    "    (common_names LIKE \"%.gov\"",
    "      OR sans LIKE \"%.gov\")",
])
CENSYS_TWO_SUFFIX_QUERY = "\n".join([
    "SELECT",
    "    parsed.subject.common_name,",
    "    parsed.extensions.subject_alt_name.dns_names",
    "FROM",
    "    `censys-io.certificates_public.certificates`,",
    "    UNNEST(parsed.subject.common_name) AS common_names,",
    "    UNNEST(parsed.extensions.subject_alt_name.dns_names) AS sans",
    "WHERE",
    "    (common_names LIKE \"%.gov\"",
    "      OR sans LIKE \"%.gov\")",
    "    OR (common_names LIKE \"%.fed.us\"",
    "      OR sans LIKE \"%.fed.us\")",
])


@pytest.mark.parametrize("suffixes,expected", [
    (
        [".gov"],
        CENSYS_ONE_SUFFIX_QUERY
    ),
    (
        [".gov", ".fed.us"],
        CENSYS_TWO_SUFFIX_QUERY
    ),
])
def test_query_for(suffixes, expected):
    result = censys.query_for(suffixes)
    assert result == expected
