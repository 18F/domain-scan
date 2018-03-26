import csv
from py._path import local
import pytest
from runner import runner


class MockScanner:
    headers = ['field_a', 'field_b']


@pytest.fixture
def output_file(tmpdir):
    return str(tmpdir.join('output.csv'))


def test_write_rows(output_file):
    data = [
        ['value 1', 'value 2'],
        ['value 3', 'value 4'],
    ]
    with open(output_file, 'w') as output_file_obj:
        csv_writer = csv.writer(output_file_obj)
        runner.write_rows(data, 'foo.gov', 'foo.gov', MockScanner(), csv_writer)

    with open(output_file, 'r') as file_object:
        reader = csv.DictReader(file_object, ['domain', 'base_domain', 'A', 'B'])
        result = [dict(row) for row in reader]

    assert result == [
        {'domain': 'foo.gov', 'base_domain': 'foo.gov', 'A': 'value 1', 'B': 'value 2'},
        {'domain': 'foo.gov', 'base_domain': 'foo.gov', 'A': 'value 3', 'B': 'value 4'},
    ]


def test_write_rows_no_data(output_file):
    with open(output_file, 'w') as output_file_obj:
        csv_writer = csv.writer(output_file_obj)
        runner.write_rows(None, 'foo.gov', 'foo.gov', MockScanner(), csv_writer)

    with open(output_file, 'r') as file_object:
        reader = csv.DictReader(file_object, ['domain', 'base_domain', 'A', 'B'])
        result = [dict(row) for row in reader]

    assert result == [
        {'domain': 'foo.gov', 'base_domain': 'foo.gov', 'A': '', 'B': ''}
    ]


def test_write_rows_with_meta(output_file):
    data = [
        ['value 1', 'value 2'],
    ]

    meta = {
        'errors': ['error1'],
        'start_time': 1521990106,
        'end_time': 1521990206,
        'duration': 100
    }

    with open(output_file, 'w') as output_file_obj:
        csv_writer = csv.writer(output_file_obj)
        runner.write_rows(data, 'foo.gov', 'foo.gov', MockScanner(), csv_writer, meta=meta)

    with open(output_file, 'r') as file_object:
        fields = ['domain', 'base_domain', 'A', 'B', 'errors', 'start_time', 'end_time', 'duration']
        reader = csv.DictReader(file_object, fields)
        result = [dict(row) for row in reader]

    assert result == [{
        'domain': 'foo.gov',
        'base_domain': 'foo.gov',
        'A': 'value 1',
        'B': 'value 2',
        'errors': 'error1',
        'start_time': '2018-03-25T15:01:46Z',
        'end_time': '2018-03-25T15:03:26Z',
        'duration': '100.000000'
    }]


def test_rows_with_lambda_meta(output_file):
    data = [
        ['value 1', 'value 2'],
    ]

    meta = {
        'errors': ['error1'],
        'start_time': 1521990106,
        'end_time': 1521990206,
        'duration': 100,
        'lambda': {
            'request_id': 1,
            'log_group_name': 'group',
            'log_stream_name': 'stream',
            'start_time': 1521990107,
            'end_time': 1521990205,
            'memory_limit': 100,
            'measured_duration': 98,
        }
    }

    with open(output_file, 'w') as output_file_obj:
        csv_writer = csv.writer(output_file_obj)
        runner.write_rows(data, 'foo.gov', 'foo.gov', MockScanner(), csv_writer, meta=meta)

    with open(output_file, 'r') as file_object:
        fields = ['domain', 'base_domain', 'A', 'B', 'errors', 'start_time', 'end_time', 'duration',
                  'request_id', 'log_group_name', 'log_stream_name', 'lambda_start_time', 'lambda_end_time',
                  'memory_limit', 'measured_duration']
        reader = csv.DictReader(file_object, fields)
        result = [dict(row) for row in reader]

    assert result == [{
        'domain': 'foo.gov',
        'base_domain': 'foo.gov',
        'A': 'value 1',
        'B': 'value 2',
        'errors': 'error1',
        'start_time': '2018-03-25T15:01:46Z',
        'end_time': '2018-03-25T15:03:26Z',
        'duration': '100.000000',
        'lambda_end_time': '2018-03-25T15:03:25Z',
        'lambda_start_time': '2018-03-25T15:01:47Z',
        'log_group_name': 'group',
        'log_stream_name': 'stream',
        'measured_duration': '98.000000',
        'memory_limit': '100',
        'request_id': '1',
    }]
