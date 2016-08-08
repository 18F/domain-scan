## Hostname gathering

Making it easy to gather hostnames that match a certain pattern.

Requires **Python 3**, install dependencies with `pip install -r requirements.txt`.

Run commands from the root of the project, for example:

```bash
python -m scripts.filter [options]
```

### Filtering a large data file into a CSV of hostnames

Given:

* a large input text file
* where each line ends with a hostname pattern
* a suffix to match against each line

Produce:

* a one-column CSV of each hostname matched against that filter

Normal options:

* input file (required)
* `--name`: name of dataset (e.g. `rdns`, `ct`)
* `--filter`: name of filter to apply (defaults to value of `--name`)
* `--suffix`: suffix to filter on (e.g. `.gov`)
* `--encoding`: input file encoding (defaults to `latin-1`)

Helpful for debugging:

* `--max`: stop after this many lines
* `--debug`: display output when matching each line (slow)

##### Examples

Filter for `.gov` domains in the first 1000 records in a locally downloaded [Rapid7 Reverse DNS](https://scans.io/study/sonar.rdns) export:

```bash
python -m scripts.filter --name=rdns --filter=ip_pair ~/data/domains/20160608-rdns --suffix=.gov --max=1000
```

Will produce `scripts/hostnames/rdns.csv`.

### Downloading hostnames from the Censys.io certificates API

Given:

* a suffix
* how many pages of results (100 per page) you want

Produce:

* a one-column CSV of hostnames matching that suffix from certificates

To configure, set two environment variables from [your Censys account page](https://censys.io/account):

* `CENSYS_UID`: Your Censys API ID.
* `CENSYS_API_KEY`: Your Censys secret.

Normal options:

* `--start`: Page number to start on (defaults to `1`)
* `--end`: Page number to end on (defaults to value of `--start`)
* `--suffix`: suffix to filter on (e.g. `.gov`)
* `--delay`: Sleep between pages, to meet API limits. Defaults to 5s. If you have researcher access, shorten to 2s.

Helpful for debugging:

* `--debug`: display output when matching each cert (slow)

##### Examples

Find `.gov` certificates in the first 2 pages of Censys API results, waiting 5 seconds between pages:

```bash
python -m scripts.censys_api --suffix=.gov --start=1 --end=2 --delay=5
```
