## A domain scanner

Scans domains for data on their:

* HTTP, HTTPS, and [HSTS](https://https.cio.gov/hsts/) configuration, using [`site-inspector`](https://github.com/benbalter/site-inspector-ruby).
* Detailed TLS configuration, using the [SSL Labs API](https://github.com/ssllabs/ssllabs-scan).
* Whether a domain participates in the [Digital Analytics Program](https://analytics.usa.gov). (This one's U.S. government-specific for now, but can be ignored.)

Most of the work is farmed out to other tools. The point of this scanner is to coordinate those tools and produce consistent data output.

Can be used with any domain, or CSV where domains are the first column, such as the [official .gov domain list](https://github.com/GSA/data/tree/gh-pages/dotgov-domains).

### Requirements

* **Python 3**.
* **[site-inspector](https://github.com/benbalter/site-inspector)**, version **1.0.2 only**.
* **[ssllabs-scan](https://github.com/ssllabs/ssllabs-scan)**, stable branch.

Override the path to the `site-inspector` executable by setting the `SITE_INSPECTOR_PATH` environment variable.

Override the path to the `ssllabs-scan` executable by setting the `SSLLABS_PATH` environment variable.

### Usage

Scan a domain. You must specify at least one "scanner" with `--scan`.

```bash
./scan whitehouse.gov --scan=inspect
```

Scan a list of domains from a CSV. The CSV's header row will be ignored if the first cell starts with "Domain" (case-insensitive).

```bash
./scan domains.csv --scan=inspect
```

Run multiple scanners on each domain:

```bash
./scan whitehouse.gov --scan=inspect,tls
```

##### Parallelization

It's important to understand that **scans run in parallel by default**, and so **the order of result data is unpredictable**.

By default, each scanner will run up to 10 parallel tasks, which you can override with `--workers`.

Some scanners may limit this. For example, the `tls` scanner, which hits the SSL Labs API, maxes out at 5 tasks at once (which cannot be overridden with `--workers`).

To disable this and run sequentially through each domain (1 worker), use `--serial`.

##### Options

**Scanners:**

* `inspect` - HTTP/HTTPS/HSTS configuration.
* `tls` - TLS configuration.
* `analytics` - Participation in an analytics program.

**Options:**

* `--scan` - **Required.** Comma-separated names of one or more scanners.
* `--serial` - Disable parallelization, force each task to be done simultaneously. Helpful for testing and debugging.
* `--debug` - Print out more stuff. Useful with `--serial`.
* `--workers` - Limit parallel threads per-scanner to a number.
* `--output` - Where to output the `cache/` and `results/` directories. Defaults to `./`.
* `--force` - Ignore cached data and force scans to hit the network.
* `--suffix` - Add a suffix to all input domains. For example, a `--suffix` of `virginia.gov` will add `.virginia.gov` to the end of all input domains.
* `--analytics` - Required if using the `analytics` scanner. Point this to the CSV of participating domains.

### Output

All output files are placed into `cache/` and `results/` directories, whose location defaults to the current directory (`./`). Override the output home with `--output`.

* **Cached full scan data** about each domain is saved in the `cache/` directory, named after each scan and each domain, in JSON.

Example: `cache/inspect/whitehouse.gov.json`

* **Formal output data** in CSV form about all domains are saved in the `results/` directory in CSV form, named after each scan.

Example: `results/inspect.csv`

You can override the output directory by specifying `--output`.

It's possible for scans to save multiple CSV rows per-domain. For example, the `tls` scan may have a row with details for each detected TLS "endpoint".

* **Scan metadata** with the start time, end time, and scan command will be placed in the `results/` directory as `meta.json`.

Example: `results/meta.json`

### Using with Docker

If using [Docker Compose](https://docs.docker.com/compose/), it is as simple as cloning this GitHub repository and running:

```bash
docker-compose up
```

Then to scan, prefix commands with `docker-compose run`, like:

```bash
docker-compose run scan <domain> --scan=<scanner>
```

### TODOs

Some high-priority TODOs here:

* **Parallelization.** There's no risk of DoS to target domains, because it's spread out naturally. The SSL Labs API used by the `tls` scanner has parameters and guidelines for batch work to avoid over-hammering their service.
* **JSON output**. Refactor scanners to return a dict instead of a row. Have scanners specify both JSON-style field headers *and* CSV-style column headers in a 2-dimensional array. Use this to make it so JSON and CSV can both be serialized with appropriate fields and in the right order. Include JSON results in the `results/` dir.
* **Handle network loss gracefully.** Right now, the scanner will assume that a domain is "down" if the network is down, and cache that. That makes trusting the results of a batch run iffy. I don't know the best way to distinguish between a domain being unreachable, and the network *making* the domain unreachable.
* **Upgrade to site-inspector 2.x.** This repo depends on site-inspector 1.0.2, which is behind the times. But, site-inspector 2 needs more testing and work first. site-inspector 2 also is not backwards-compatible, in CLI syntax or in result format.

### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
