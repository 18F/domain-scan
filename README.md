[![Code Climate](https://codeclimate.com/github/18F/domain-scan/badges/gpa.svg)](https://codeclimate.com/github/18F/domain-scan) [![Dependency Status](https://gemnasium.com/badges/github.com/18F/domain-scan.svg)](https://gemnasium.com/github.com/18F/domain-scan)


## A domain scanner

Scans domains for data on their HTTPS and email configuration, third party service usage, accessibility, and other things. [Adding new scanners](#developing-new-scanners) is relatively straightforward.

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

Append columns to each row with metadata about the scan itself, such as how long each individual scan took:

```bash
./scan example.com --scan=pshtt --meta
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

This tool also includes a facility for gathering domain names that end in one or more given suffixes (e.g. `.gov` or `.gov.uk`) from various sources.

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

* `--suffix`: **Required.** One or more suffix to filter on, separated by commas as necessary. (e.g. `.gov` or `.gov,.gov.uk`)
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

### Developing new scanners

Scanners are registered by creating a single Python file in the `scanners/` directory, where the file is given the name of the scanner (plus the `.py` extension).

Each scanner should define a few top-level functions and one variable that will be referenced at different points.

For an example of how a scanner works, start with [`scanners/noop.py`](scanners/noop.py). The `noop` scanner is a test scanner that does nothing (no-op), but it implements and documents a scanner's basic Python contract.

Scanners can implement 4 functions (2 required, 2 optional). In order of being called:

* `init(environment, options)` (Optional)

  The `init()` function will be run only once, before any scans are executed.

  Returning a dict from this function will merge that dict into the `environment` dict passed to all subsequent function calls for every domain.

  Returning `False` from this function indicates that the scanner is unprepared, and the _entire_ scan process (for all scanners) will abort.

  Useful for expensive actions that shouldn't be repeated for each scan, such as downloading supplementary data from a third party service. [See the `pshtt` scanner](scanners/pshtt.py) for an example of downloading the Chrome preload list once, instead of for each scan.

  The `init` function is **always run locally**.

* `init_domain(domain, environment, options)` (Optional)

  The `init_domain()` function will be run once per-domain, before the `scan()` function is executed.

  Returning a dict from this function will merge that dict into the `environment` dict passed to the `scan()` function for that particular domain.

  Returning `False` from this function indicates that the domain should not be scanned. The domain will be skipped and no rows will be added to the resulting CSV. The `scan` function will not be called for this domain, and cached scan data for this domain _will not_ be stored to disk.

  Useful for per-domain preparatory work that needs to be performed locally, such as taking advantage of scan information cached on disk from a prior scan. [See the `sslyze` scanner](scanners/sslyze.py) for an example of using available `pshtt` data to avoid scanning a domain known not to support HTTPS.

  The `init_domain` function is **always run locally**.

* `scan(domain, environment, options)` **(Required)**

  The `scan` function performs the core of the scanning work.

  Returning a dict from this function indicates that the scan has completed successfully, and that the returned dict is the resulting information. This dict will be passed into the `to_rows` function described below, and used to generate one or more rows for the resulting CSV.

  Returning `None` from this function indicates that the scan has completed unsuccessfully. The domain will be skipped, and no rows will be added to the resulting CSV.

  In all cases, cached scan data for the domain _will_ be stored to disk. If a scan was unsuccessful, the cached data will indicate that the scan was unsuccessful. Future scans that rely on cached responses will skip domains for which the cached scan was unsuccessful, and will not execute the `scan` function for those domains.

  The `scan` function is **run either locally or in Lambda**. (See [`docs/lambda.md`](docs/lambda.md) for how to execute functions in Lambda.)

* `to_rows(data)` **(Required)**

  The `to_rows` function converts the data returned by a scan into one or more rows, which will be appended to the resulting CSV.

  The `data` argument passed to the function is the return value of the `scan` function described above.

  The function _must_ return a list of lists, where each contained list is the same length as the `headers` variable described below.

  For example, a `to_rows` function that always returns one row with two values might be as simple as `return [[ data['value1'], data['value2'] ]]`.

  The `to_rows` function is **always run locally**.

And each scanner must define one top-level variable:

* `headers` **(Required)**

  The `headers` variable is a list of strings to use as column headers in the resulting CSV. These headers must be in the same order as the values in the lists returned by the `to_rows` function.

  The `headers` variable is **always referenced locally**.

In all of the above functions that receive it, `environment` is a dict that will contain (at least) a `scan_method` key whose value is either `"local"` or `"lambda"`.

The `environment` dict will also include any key/value pairs returned by previous function calls. This means that data returned from `init` will be contained in the `environment` dict sent to `init_domain`. Similarly, data returned from both `init` and `init_domain` for a particular domain will be contained in the `environment` dict sent to the `scan` method for that domain.

In all of the above functions that receive it, `options` is a dict that contains a direct representation of the command-line flags given to the `./scan` executable.

For example, if the `./scan` command is run with the flags `--scan=pshtt,sslyze --lambda`, they will translate to an `options` dict that contains (at least) `{"scan": "pshtt,sslyze", "lambda": True}`.


### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
