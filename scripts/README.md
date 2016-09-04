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

