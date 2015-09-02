import logging
from scanners import utils
import json
import os

import shlex
from subprocess import Popen, PIPE

def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode
    #
    return exitcode, out, err




command = os.environ.get("PA11Y_PATH", "pa11y")
workers = 1

def scan(domain, options):
    command = "pa11y --reporter csv %s" % domain

    cmd = command
    exitcode, out, err = get_exitcode_stdout_stderr(cmd)

    print(out)

    yield [1,2,3]

headers = [
    "Errors",
    "Warnings",
    "Notices"
]