import typing
from utils import utils
from typing_extensions import Protocol


class ScannerProtocol(Protocol):
    headers = []  # type: typing.List[str]


def write_rows(rows: typing.Optional[typing.List[typing.List]],
               domain: str,
               base_domain: str,
               scanner: ScannerProtocol,
               csv_writer: typing.Any,
               meta: typing.Optional[typing.Mapping[str, typing.Any]] = None):

    # If we didn't get any info, we'll still output information about why the scan failed.
    if rows is None:
        empty_row = [None] * len(scanner.headers)
        rows = [empty_row]

    # Always output Domain and Base Domain.
    standard_prefix = [
        domain,
        base_domain,
    ]

    # If requested, add local and Lambda scan data.
    meta_fields = []
    if meta:
        meta_fields.append(" ".join(meta.get('errors', [])))
        meta_fields.append(utils.utc_timestamp(meta.get("start_time")))
        meta_fields.append(utils.utc_timestamp(meta.get("end_time")))
        meta_fields.append(utils.just_microseconds(meta.get("duration")))

        if meta.get("lambda") is not None:
            meta_fields.append(meta['lambda'].get('request_id'))
            meta_fields.append(meta['lambda'].get('log_group_name'))
            meta_fields.append(meta['lambda'].get('log_stream_name'))
            meta_fields.append(utils.utc_timestamp(meta['lambda'].get('start_time')))
            meta_fields.append(utils.utc_timestamp(meta['lambda'].get('end_time')))
            meta_fields.append(meta['lambda'].get('memory_limit'))
            meta_fields.append(utils.just_microseconds(meta['lambda'].get('measured_duration')))

    # Write out prefix, scan data, and meta scan data.
    for row in rows:
        csv_writer.writerow(standard_prefix + row + meta_fields)
