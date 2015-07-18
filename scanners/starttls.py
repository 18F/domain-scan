from datetime import datetime, timedelta
import logging
import re
import requests
import time

command = None

def starttls_check_url(domain):
    return 'https://starttls.info/api/check/%s' % domain


def poll_starttls_info_status(domain):
    """
    Poll the starttls.info API endpoint until the status of the info for a
    given `domain` is 'DONE'.

    We poll every 5 seconds.
    """
    poll_interval = 5
    max_poll = 300    # 5 minutes
    time_elapsed = 0

    while True:
        if time_elapsed >= max_poll:
            logging.error("Timed out polling for updated info from starttls.info for %s" % domain)
            break

        logging.debug("Checking starttls.info status for %s" % domain)

        start_time = time.clock()

        r = requests.get(starttls_check_url(domain))
        if r.json()['status'] == 'DONE':
            return r

        finish_time = time.clock()
        sleep_time = max(0, poll_interval - (finish_time - start_time))
        time.sleep(sleep_time)
        time_elapsed += time.clock() - start_time


def refresh_starttls_results(domain):
    """
    Send a `reset` POST request to the STARTTLS API endpoint to ask the
    server to refresh the results for `domain`.

    After the reset request is sent, we poll the endpoint until it is done
    refreshing the results, then return the complete set of new results.
    """
    logging.debug('Refreshing STARTTLS results for %s' % domain)
    r = requests.post(starttls_check_url(domain), data={ 'reset': 'true' })
    return poll_starttls_info_status(domain)


def scan(domain, options):
    logging.debug("[%s][starttls]" % domain)

    # Query the starttls.info API endpoint
    r = requests.get(starttls_check_url(domain))

    # It's possible to query the endpoint while it is re-checking the results
    # for this domain. In this case, poll until the scan is done so we get
    # complete and up-to-date results.
    if r.json()['status'] == 'IN PROGRESS':
        r = poll_starttls_info_status(domain)

    # starttls.info doesn't automatically re-check domains, but we can ask it
    # to do so if the results aren't fresh enough.

    # A 1-day refresh rate is arbitrary. We want to encourage people to use
    # this dashboard as a way to track their progress on implementing
    # improvements to their security, and it'll be more effective as
    # encouragement if we reward people's work promptly.
    results_max_age = timedelta(days=1)
    last_updated = datetime.strptime(r.json()['status_changed'],
                                     "%Y-%m-%dT%H:%M:%S.%fZ")
    if last_updated < datetime.utcnow() - results_max_age:
        r = refresh_starttls_results(domain)

    # The STARTTLS.info API is not great, and returns most of its useful info
    # in a big blob of HTML instead of a nice JSON data model. We'll use
    # regexes to parse it for now :'(. Hopefully once starttls.info is open
    # sourced, we will be able to contribute and improve this state of affairs.

    # starttls.info can return multiple rows, one for each MX endpoint
    for mx in r.json()['actual_targets']:
        description = mx['description']

        if mx['failed'] == True:
            # 'failed' is true for tests that fail (e.g. because they could
            # not connect to the SMTP port on the given MX host) *and* for
            # tests that succeed, but determine that STARTTLS is disabled. This
            # is sort of annoying, but we can't do anything about it now.
            # Hopefully we can help clean up the API once the project is open
            # source.
            yield [ r.json()['status_changed'], mx['name'], not mx['failed'],
                    mx['description'], None, None, None, None, None ]
        else:
            # TODO: starttls.info doesn't indicate the key *type*, and seems to
            # assume everything is using RSA. Does anybody use ECC for
            # STARTTLS?
            key_size_re = r'Key size is ([0-9]+) bits'
            key_size = re.search(key_size_re, description)
            if key_size is not None:
                key_size = key_size.group(1)

            # Since the API is not documented, I am inferring how to determine
            # whether the certificate is valid from some sample queries.
            #
            # It appears that if the certificate is valid, the "Certificate"
            # section says "No remarks". For example, see
            # https://starttls.info/api/check/nytimes.com.
            #
            # If the certificate is invalid, it says "The certificate is not
            # valid for the server's hostname.". For example, see
            # https://starttls.info/api/check/theguardian.com.
            #
            # There are probably other values for this that I simply haven't
            # encountered yet in my limited testing. We really need the API to
            # be documented or the code to be open sourced to know for sure.
            #
            # I'm guessing that there are multiple reasons why the cert might
            # be invalid (e.g. self-signed, doesn't match hostname, expired,
            # etc.) which will result in different messages. However, the
            # format of the HTML suggests they will always show the "There are
            # validity issues for the certificate." for invalid certs, so I'm
            # going to use that as the indicator for now.
            invalid_cert_re = r'There are validity issues for the certificate.'
            valid_cert = not re.search(invalid_cert_re, description)

            sslv3_re = r'Supports SSLV3.'
            sslv3 = bool(re.search(sslv3_re, description))

            tlsv12_re = r'Supports TLSV1.2'
            tlsv12 = bool(re.search(tlsv12_re, description))

        yield [
            r.json()['status_changed'],
            mx['name'],
            not mx['failed'],
            None,
            mx['score'],
            key_size,
            valid_cert,
            sslv3,
            tlsv12
        ]


headers = [
    "Status Changed",
    "MX Hostname",
    "STARTTLS Supported",
    "Reason check failed",
    "starttls.info Score",
    "Key Size",
    "Valid Certificate",
    "SSLv3",
    "TLSv1.2",
]
