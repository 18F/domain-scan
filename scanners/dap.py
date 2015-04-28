
from scanners import utils
import logging
import os

command = None
dap_domains = None

def init(options):
    global dap_domains

    dap_file = options.get("dap-csv")
    if (not dap_file) or (not dap_file.endswith(".csv")) or (not os.path.exists(dap_file)):
        logging.error("--dap-csv should point to a CSV file.")
        return False

    dap_domains = utils.load_domains(dap_file)
    return True

###
# Check whether a domain is present in the list of DAP domains,
# as provided through --dap-file.
#
# Assumes dap_domains is preloaded from --dap-file.
###
def scan(domain, options):
    logging.debug("[%s][dap]" % domain)
    logging.debug("\tChecking file.")
    # TODO: have this output JSON anyway.
    yield [(domain in dap_domains)]

headers = ["Participates in DAP"]
