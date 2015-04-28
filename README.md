## An HTTPS scanner

Scans domains for data on their:

* HTTP, HTTPS, and [HSTS](https://https.cio.gov/hsts/) configuration, using [`site-inspector`](https://github.com/benbalter/site-inspector-ruby).
* Detailed TLS configuration, using the [SSL Labs API](https://github.com/ssllabs/ssllabs-scan).
* Whether a domain participates in the [Digital Analytics Program](https://analytics.usa.gov). (Government-specific for now.)

Can be used with any domain, or CSV where domains are the first column, such as the [official .gov domain list](https://catalog.data.gov/dataset/gov-domains-api-c9856).

### Usage

Requires **Python 3**. Tested on 3.4.2.

Scan a domain. You must specify at least one "scanner" with `--scan`.

```bash
./scan konklone.com --scan=inspect
```

Scan a list of domains from a CSV. The CSV's header row will be ignored if the first cell starts with "Domain" (case-insensitive).

```bash
./scan domains.csv --scan=inspect
```

Run multiple scanners on each domain:

```bash
./scan whitehouse.gov --scan=inspect,tls
```

**Options:**

* `--scan` - **Required.** Comma-separated names of one or more scanners.
* `--debug` - Print out more stuff.

**Scanners:**

* `inspect` - HTTP/HTTPS/HSTS configuration.
* `tls` - TLS configuration.
* `analytics` - Participation in an analytics program.

### Output

Full scan data about each domain is saved in the `cache/` directory, named after each scan and each domain, in JSON.

* Example: `cache/inspect/whitehouse.gov.json`

Highlights from the scan data about all domains are saved in the `results/` directory, named after each scan, in CSV.

* Example: `results/inspect.csv`

It's possible for scans to save multiple CSV rows per-domain. For example, the `tls` scan may have a row with details for each detected TLS "endpoint".

### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
