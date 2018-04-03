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
            '{"timestamp":"1510189589","name":"148.165.34.19","value":"www.bart.gov","type":"ptr"}',
            '{"timestamp":"1510189590","name":"166.2.164.127","value":"z-166-2-164-127.ip.fs.fed.us","type":"ptr"}',
            '{"timestamp":"1510189590","name":"199.131.187.116","value":"z-199-131-187-116.ip.fs.fed.us","type":"ptr"}',
            '{"timestamp":"1510189590","name":"199.156.215.172","value":"199.156.215.172.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189591","name":"137.79.24.39","value":"wildcard.jpl.nasa.gov","type":"ptr"}',
            '{"timestamp":"1510189591","name":"152.132.2.60","value":"152-132-2-60.tic.va.gov","type":"ptr"}',
            '{"timestamp":"1510189591","name":"166.3.217.20","value":"z-166-3-217-20.ip.fs.fed.us","type":"ptr"}',
            '{"timestamp":"1510189591","name":"167.253.203.215","value":"167-253-203-215-gov.emcbc.doe.gov","type":"ptr"}',
            '{"timestamp":"1510189591","name":"199.153.160.221","value":"199.153.160.221.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189592","name":"140.215.230.154","value":"140-215-230-154.usbr.gov","type":"ptr"}',
            '{"timestamp":"1510189593","name":"166.6.157.98","value":"z-166-6-157-98.ip.fs.fed.us","type":"ptr"}',
            '{"timestamp":"1510189595","name":"130.20.175.6","value":"130.20.175.6.pnnl.gov","type":"ptr"}',
            '{"timestamp":"1510189595","name":"199.149.248.138","value":"199.149.248.138.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189595","name":"199.159.207.25","value":"199.159.207.25.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189596","name":"199.145.148.196","value":"199.145.148.196.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189597","name":"159.142.211.155","value":"host.159-142-211-155.gsa.gov","type":"ptr"}',
            '{"timestamp":"1510189597","name":"159.189.28.97","value":"u-159-189-28-97.xr.usgs.gov","type":"ptr"}',
            '{"timestamp":"1510189598","name":"139.169.172.113","value":"host.jsc.nasa.gov","type":"ptr"}',
            '{"timestamp":"1510189599","name":"134.67.230.238","value":"unassigned.epa.gov","type":"ptr"}',
            '{"timestamp":"1510189600","name":"130.118.135.187","value":"u-130-118-135-187.xr.usgs.gov","type":"ptr"}',
            '{"timestamp":"1510189600","name":"140.214.229.183","value":"140-214-229-183.usbr.gov","type":"ptr"}',
            '{"timestamp":"1510189600","name":"199.148.94.97","value":"199.148.94.97.4k.usda.gov","type":"ptr"}',
            '{"timestamp":"1510189601","name":"170.144.139.133","value":"z-170-144-139-133.ip.fs.fed.us","type":"ptr"}',
        ],
        [
            "18f.gov",
            "something.fed.us",
            "18f.gsa.gov",
            "www.bart.gov",
            "wildcard.jpl.nasa.gov",
            # "host.159-142-211-155.gsa.gov",  TODO: currently gets stripped, but should it?
            "host.jsc.nasa.gov",
            "unassigned.epa.gov",
        ]
    ),
])
def test_query_for(data, expected):
    result = rdns.process_lines(data, rdns.ip_filter, rdns.number_filter)
    assert list(result) == expected
