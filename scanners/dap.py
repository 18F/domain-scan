# Evaluate DAP participation using Chrome headless.

# Can also be run in Lambda.
lambda_support = True

# Signal that this is a JS-based scan using headless Chrome.
# The scan method will be defined in dap.js instead.
scan_headless = True


# make sure we have the domain/url stuff set up properly
def init_domain(domain, environment, options):
    # To scan, we need a URL, not just a domain.
    url = None
    if not (domain.startswith('http://') or domain.startswith('https://')):
        url = 'https://' + domain
    else:
        url = domain

    # Standardize by ending with a /.
    url = url + "/"

    return {'url': url}


# Gets the return value of scan(), convert to a CSV row.
def to_rows(data):
    row = []
    for i in headers:
        row.extend([data[i]])
    return [row]


# CSV headers for each row of data. Referenced locally.
headers = [
    "domain",
    "status_code",
    "dap_detected",
    "dap_parameters",
    "final_url",
    "final_url_in_same_domain",
    "redirect",
    "redirects_to"
]
