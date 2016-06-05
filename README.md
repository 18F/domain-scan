## A domain scanner

Scans domains for data on their HTTPS configuration and assorted other things.

**Most of the work is farmed out to other command line tools.** The point of this project is to **coordinate** those tools and produce **consistent data output**.

Can be used with any domain, or CSV where domains are the first column, such as the [official .gov domain list](https://catalog.data.gov/dataset/gov-domains-api-c9856).

### Requirements

The requirements here can be quite diverse, because this tool is just a coordinator for other tools. Communication between tools is handled via CLI and STDOUT.

The overall tool requires **Python 3** and **Docker**. To install dependencies:

```bash
pip install -r requirements.txt
```

### Scanners

* `inspect` scanner: runs **[site-inspector](https://github.com/benbalter/site-inspector)**
* `tls` scanner: runs **[ssllabs-scan](https://github.com/ssllabs/ssllabs-scan)**
* `sslyze` scanner: runs **[sslyze](https://github.com/nabla-c0d3/sslyze)**
* `pageload` scanner: runs **[phantomas](https://www.npmjs.com/package/phantomas)**

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

Parallelization will also cause the resulting domains to be written in an unpredictable order. If the row order is important to you, disable parallelization, or use the `--sort` parameter to sort the resulting CSVs once the scans have completed. (**Note:** Using `--sort` will cause the entire dataset to be read into memory.)

##### Options

**Scanners:**

* `inspect` - HTTP/HTTPS/HSTS configuration.
* `tls` - TLS configuration, using the [SSL Labs API](https://github.com/ssllabs/ssllabs-scan/blob/stable/ssllabs-api-docs.md).
* `sslyze` - TLS configuration, using the local [`sslyze`](https://github.com/nabla-c0d3/sslyze) command line tool.
* `analytics` - Participation in an analytics program.
* `pageload` - Page load and rendering metrics.

**General options:**

* `--scan` - **Required.** Comma-separated names of one or more scanners.
* `--sort` - Sort result CSVs by domain name, alphabetically. (**Note:** this causes the entire dataset to be read into memory.)
* `--serial` - Disable parallelization, force each task to be done simultaneously. Helpful for testing and debugging.
* `--debug` - Print out more stuff. Useful with `--serial`.
* `--workers` - Limit parallel threads per-scanner to a number.
* `--output` - Where to output the `cache/` and `results/` directories. Defaults to `./`.
* `--force` - Ignore cached data and force scans to hit the network. For the `tls` scanner, this also tells SSL Labs to ignore its server-side cache.
* `--suffix` - Add a suffix to all input domains. For example, a `--suffix` of `virginia.gov` will add `.virginia.gov` to the end of all input domains.

**Scanner-specific options**

* `--analytics` - For the `analytics` scanner. Point this to either a file **or** a URL that contains a CSV of participating domains.

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

* **JSON output**. Refactor scanners to return a dict instead of a row. Have scanners specify both JSON-style field headers *and* CSV-style column headers in a 2-dimensional array. Use this to make it so JSON and CSV can both be serialized with appropriate fields and in the right order. Include JSON results in the `results/` dir.
* **Handle network loss gracefully.** Right now, the scanner will assume that a domain is "down" if the network is down, and cache that. That makes trusting the results of a batch run iffy. I don't know the best way to distinguish between a domain being unreachable, and the network *making* the domain unreachable.

### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
