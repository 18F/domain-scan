[![Code Climate](https://codeclimate.com/github/18F/domain-scan/badges/gpa.svg)](https://codeclimate.com/github/18F/domain-scan) [![Dependency Status](https://gemnasium.com/badges/github.com/18F/domain-scan.svg)](https://gemnasium.com/github.com/18F/domain-scan)


## A domain scanner

Scans domains for data on their HTTPS and email configuration, third party service usage, accessibility, and other things. Adding new scanners is relatively straightforward.

All scanners can be run locally using **native Python multi-threading**.

Some scanners can be executed **inside Amazon Lambda** for much higher levels of parallelization.

Most scanners work by using **specialized third party tools**, such as [`SSLyze`](https://github.com/nabla-c0d3/sslyze) or [`trustymail`](https://github.com/dhs-ncats/trustymail). Each scanner in this repo is meant to add the smallest wrapper possible around the responses returned from these tools.

The point of this project is to **coordinate** and **parallelize** those tools and produce **consistent data output**.

Can be used with any domain, or any CSV where domains are the first column, such as the [official .gov domain list](https://github.com/GSA/data/raw/master/dotgov-domains/current-full.csv).

### Requirements

`domain-scan` requires **Python 3.5 and up**. To install dependencies:

```bash
pip install -r requirements.txt
```

This will automatically allow the use of two scanners:

* `pshtt` - A scanner that uses the [`pshtt`](https://github.com/dhs-ncats/pshtt) Python package from the [Department of Homeland Security's NCATS team](https://github.com/dhs-ncats).
* `sslyze` - A scanner that uses the [`sslyze`](https://github.com/nabla-c0d3/sslyze) Python package maintained by Alban Diquet.

Other individual scanners will require additional externally installed dependencies:

* `trustymail`: The `trustymail` command, available from the [`trustymail`](https://github.com/dhs-ncats/trustymail) Python package from the [Department of Homeland Security's NCATS team](https://github.com/dhs-ncats). (Override path by setting the `TRUSTYMAIL_PATH` environment variable.)
* `a11y`: The `pa11y` command, available from the [`pa11y`](https://www.npmjs.com/package/pa11y) Node package. (Override path by setting the `PA11Y_PATH` environment variable.)
* `third_parties`: The `phantomas` command, available from the [`phantomas`](https://www.npmjs.com/package/phantomas) Node package. (Override path by setting the `PHANTOMAS_PATH` environment variable.)


### Usage

Scan a domain. You must specify at least one "scanner" with `--scan`.

```bash
./scan whitehouse.gov --scan=pshtt
```

Scan a list of domains from a CSV. The CSV's header row will be ignored if the first cell starts with "Domain" (case-insensitive).

```bash
./scan domains.csv --scan=pshtt
```

Run multiple scanners on each domain:

```bash
./scan whitehouse.gov --scan=pshtt,sslyze
```

##### Parallelization

It's important to understand that **scans run in parallel by default**, and **data is streamed to disk immediately** after each scan is done.

This makes domain-scan fast, as well as memory-efficient (the entire dataset doesn't need to be read into memory), but **the order of result data is unpredictable**.

By default, each scanner will spin up 10 parallel threads. You can override this value with `--workers`. To disable this and run sequentially through each domain (1 worker), use `--serial`.

If row order is important to you, either disable parallelization, or use the `--sort` parameter to sort the resulting CSVs once the scans have completed. (**Note:** Using `--sort` will cause the entire dataset to be read into memory.)

### Lambda

The domain-scan tool can execute certain compatible scanners in Amazon Lambda, instead of locally.

This can allow the use of hundreds of parallel workers, and can speed up large scans by orders of magnitude. (Assuming that the domains you're scanning are disparate enough to avoid DDoS-ing any particular service!)

See [`docs/lambda.md`](docs/lambda.md) for instructions on configuring scanners for use with Amazon Lambda.

Once configured, scans be run in Lambda using the `--lambda` flag, like so:

```bash
./scan example.com --scan=pshtt,sslyze --lambda
```

##### Options

**Scanners:**

* `pshtt` - HTTP/HTTPS/HSTS configuration, using [`pshtt`](https://github.com/dhs-ncats/pshtt).
* `trustymail` - MX/SPF/STARTTLS/DMARC configuration, using [`trustymail`](https://github.com/dhs-ncats/trustymail).
* `sslyze` - TLS/SSL configuration, using [`sslyze`](https://github.com/nabla-c0d3/sslyze).
* `third_parties` - What third party web services are in use, using [`phantomas`](https://www.npmjs.com/packages/phantomas), a headless web browser that executes JavaScript and traps outgoing requests.
* `a11y` - Accessibility issues, using [`pa11y`](https://github.com/pa11y/pa11y).
* `noop` - Test scanner (no-op) used for development and debugging. Does nothing.

**General options:**

* `--scan` - **Required.** Comma-separated names of one or more scanners.
* `--sort` - Sort result CSVs by domain name, alphabetically. (**Note:** this causes the entire dataset to be read into memory.)
* `--serial` - Disable parallelization, force each task to be done simultaneously. Helpful for testing and debugging.
* `--debug` - Print out more stuff. Useful with `--serial`.
* `--workers` - Limit parallel threads per-scanner to a number.
* `--output` - Where to output the `cache/` and `results/` directories. Defaults to `./`.
* `--cache` - Use previously cached scan data to avoid scans hitting the network where possible.
* `--suffix` - Add a suffix to all input domains. For example, a `--suffix` of `virginia.gov` will add `.virginia.gov` to the end of all input domains.
* `--lambda` - Run certain scanners inside Amazon Lambda instead of locally. (See [the Lambda instructions](docs/lambda.md) for how to use this.)
* `--meta` - Append some additional columns to each row with information about the scan itself. This includes start/end times and durations, as well as any encountered errors. When using `--lambda`, additional Lambda-specific information will be appended.

### Output

All output files are placed into `cache/` and `results/` directories, whose location defaults to the current directory (`./`). Override the output home with `--output`.

* **Cached full scan data** about each domain is saved in the `cache/` directory, named after each scan and each domain, in JSON.

Example: `cache/pshtt/whitehouse.gov.json`

* **Formal output data** in CSV form about all domains are saved in the `results/` directory in CSV form, named after each scan.

Example: `results/pshtt.csv`

You can override the output directory by specifying `--output`.

It's possible for scans to save multiple CSV rows per-domain. For example, the `a11y` scan will have a row with details for each detected accessibility error.

* **Scan metadata** with the start time, end time, and scan command will be placed in the `results/` directory as `meta.json`.

Example: `results/meta.json`

### Using with Docker

If you're using [Docker Compose](https://docs.docker.com/compose/), run:

```bash
docker-compose up
```

(You may need to use `sudo`.)

To scan, prefix commands with `docker-compose run`:

```bash
docker-compose run scan <domain> --scan=<scanner>
```

## Gathering hostnames

This tool also includes a facility for gathering domain names that end in a given suffix (e.g. `.gov`) from various sources.

By default, only fetches third-level and higher domains (excluding second-level domains).

Usage:

```bash
./gather [source] [options]
```

Or gather hostnames from multiple sources separated by commas:

```bash
./gather [source1,source2,...,sourceN] [options]
```

Right now there's one specific source (Censys.io), and then a general way of sourcing URLs or files by whatever name is convenient.

**Censys.io** - The `censys` gatherer uses the [Censys.io API](https://censys.io/api), which has hostnames gathered from observed certificates. Censys provides certificates observed from a nightly zmap scan of the IPv4 space, as well as certificates published to public Certificate Transparency logs. Use `--export` to use the [Censys.io Export API](https://censys.io/api/v1/docs/export), which is faster and more complete but requires researcher credentials.

**Remote or local CSV** - By using any other name besides `censys`, this will define a gatherer based on an HTTP/HTTPS URL or local path to a CSV. Its only option is a flag named after itself. For example, using a gatherer name of `dap` will mean that domain-scan expects `--dap` to point to the URL or local file.

Hostnames found from multiple sources are deduped, and filtered by suffix or base domain according to the options given.

The resulting `gathered.csv` will have the following columns:

* the hostname
* the hostname's base domain
* one column for each checked source, with a value of True/False based on the hostname's presence in each source

See [specific usage examples](#gathering-usage-examples) below.

General options:

* `--suffix`: **Required.** suffix to filter on (e.g. `.gov`)
* `--parents`: A path or URL to a CSV whose first column is second-level domains. Any subdomain not contained within these second-level domains will be excluded.
* `--include-parents`: Include second-level domains. (Defaults to false.)
* `--ignore-www`: Ignore the `www.` prefixes of hostnames. If `www.staging.example.com` is found, it will be treated as `staging.example.com`.
* `--debug`: display extra output

### `censys`: the Censys.io API

To configure, set two environment variables from [your Censys account page](https://censys.io/account):

* `CENSYS_UID`: Your Censys API ID.
* `CENSYS_API_KEY`: Your Censys secret.

Options:

* `--start`: Page number to start on (defaults to `1`)
* `--end`: Page number to end on (defaults to value of `--start`)
* `--delay`: Sleep between pages, to meet API limits. Defaults to 5s. If you have researcher access, shorten to 2s.
* `--query`: Specify the Censys.io search query to use (overwrites the default one based on `--suffix`)

To use the SQL export (which "researcher" accounts can do):

* `--export`: Turn on export mode.
* `--timeout`: Override timeout for waiting on job completion (in seconds).
* `--force`: Ignore cached export data.

**Example:**

Find `.gov` certificates in the first 2 pages of Censys API results, waiting 5 seconds between pages:

```bash
./gather censys --suffix=.gov --start=1 --end=2 --delay=5
```

### Gathering Usage Examples

To gather .gov hostnames from [Censys.io's Export API](https://censys.io/api/v1/docs/export):

```bash
./gather censys --suffix=.gov --export --debug
```

To gather .gov hostnames from a hosted CSV, such as one from the [Digital Analytics Program](https://analytics.usa.gov):

```bash
./gather dap --suffix=.gov --dap=https://analytics.usa.gov/data/live/sites-extended.csv
```

Or to gather federal-only .gov hostnames from [Censys.io's Export API](https://censys.io/api/v1/docs/export), a remote CSV, and a local CSV:

```bash
./gather censys,dap,private --suffix=.gov --dap=https://analytics.usa.gov/data/live/sites-extended.csv --private=/path/to/private-research.csv --parents=https://github.com/GSA/data/raw/master/dotgov-domains/current-federal.csv --export
```

### a11y setup

`pa11y` expects a config file at `config/pa11y_config.json`. Details and documentation for this config can be found in the [pa11y repo](https://github.com/pa11y/pa11y#configuration).

---

A brief note on redirects:

For the accessibility scans we're running at 18F, we're using the `pshtt` scanner to follow redirects _before_ the accessibility scan runs.  Pulse.cio.gov is set up to show accessibility scans for live, non-redirecting sites.  For example, if aaa.gov redirects to bbb.gov, we will show results for bbb.gov on the site, but not aaa.gov.

However, if you want to include results for redirecting site, note the following.  For example, if aaa.gov redirects to bbb.gov, `pa11y` will run against bbb.gov (but the result will be recorded for aaa.gov).

In order to get the benefits of the `pshtt` scanner, all `a11y` scans must include it. For example, to scan gsa.gov:

```
./scan gsa.gov --scanner=pshtt,a11y
```

Because of `domain-scan`'s caching, all the results of an `pshtt` scan will be saved in the `cache/pshtt` folder, and probably does not need to be re-run for every single `ally` scan.

---

### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
