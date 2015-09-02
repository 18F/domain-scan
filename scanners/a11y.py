import logging
from scanners import utils
import json
import os

import shlex
from subprocess import Popen, PIPE
import json

def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out, err


command = os.environ.get("PA11Y_PATH", "pa11y")
workers = 1

PA11Y_STANDARD = 'WCAG2AA'

headers = [
    "type",
    "typeCode",
    "code",
    "message",
    "context",
    "selector"
]

def scan(domain, options):
    print(options)
    command = "pa11y --standard %s --reporter json %s" % (PA11Y_STANDARD, domain)
    exitcode, out, err = get_exitcode_stdout_stderr(command)
    
    reports = json.loads(out.decode("utf-8"))

    for report in reports:
        result = []
        for header in headers:
            result.append(report.get(header))
        yield result
