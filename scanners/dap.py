from scanners import utils
import logging

# Global cache of DAP domain data, if provided via --dap-file.
dap_domains = None

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

