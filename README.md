## An HTTPS scanner

Scans domains for data on their:

* HTTP, HTTPS, and [HSTS](https://https.cio.gov/hsts/) configuration, using [`site-inspector`](https://github.com/benbalter/site-inspector-ruby).
* Detailed TLS configuration, using the [SSL Labs API](https://github.com/ssllabs/ssllabs-scan).
* Whether a domain participates in the [Digital Analytics Program](https://analytics.usa.gov). (Government-specific.)

Can be used with any domain, or CSV where domains are the first column, such as the [official .gov domain list](https://catalog.data.gov/dataset/gov-domains-api-c9856).

### Usage

Requires **Python 3**. Tested on 3.4.2.

Scan a domain.

```bash
./scan konklone.com
```

Scan a list of domains from a CSV. CSV header rows will be ignored if the first cell starts with "Domain" (case-insensitive).

```bash
./scan domains.csv
```

## Order of events

First, every given domain is run through [`site-inspector`](https://github.com/benbalter/site-inspector-ruby).

* Results stored in JSON per-domain in `cache/inspect/[domain].json`.
* Results stored in CSV for all domains at `results/inspect.csv`.

Next, every domain site-inspector saw as _live_ and _HTTPS-enabled_ will be run through [`ssllabs-scan`](https://github.com/ssllabs/ssllabs-scan), which uses the SSL Labs API and is subject to their [Terms and Conditions](https://github.com/ssllabs/ssllabs-scan/blob/master/ssllabs-api-docs.md#terms-and-conditions).

* Results stored in JSON per-domain in `cache/tls/[domain].json`.
* Results stored in CSV for all domains at `results/tls.csv`.


### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
