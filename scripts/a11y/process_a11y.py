import argparse
import csv
import json

from collections import defaultdict
from statistics import mean

from scanners.utils import mkdir_p, results_dir


class A11yProcessor(object):
    ERRORS = {
        '1_1': 'Missing Image Descriptions',
        '1_3': 'Form - Initial Findings',
        '1_4': 'Color Contrast - Initial Findings',
        '4_1': 'HTML Attribute - Initial Findings'
    }

    BRANCHES = {
        'Legislative': [
            'Library of Congress',
            'The Legislative Branch (Congress)',
            'Government Printing Office',
            'Government Publishing Office',
            'Congressional Office of Compliance',
            'Stennis Center for Public Service',
            'U.S. Capitol Police',
        ],
        'Judicial': [
            'The Judicial Branch (Courts)',
            'The Supreme Court',
            'U.S Courts',
        ],
        'Non-federal': [
            'Non-Federal Agency',
        ]
    }

    def __init__(self, a11y_path, domains_path):
        self.a11y_raw = self.read_csv(a11y_path)
        self.domain_raw = self.read_csv(domains_path)
        self.domain_to_agency = {d[0].lower(): d[2] for d in self.domain_raw}
        self.agency_to_branch = {a: b for b in self.BRANCHES for a in self.BRANCHES[b]}

    def run(self):
        data = [self.clean_row(d) for d in self.a11y_raw]

        parsed_datasets = [
            ('a11y', self.make_a11y_data(data)),
            ('agencies', self.make_agency_data(data)),
            ('domains', self.make_domain_data(data)),
        ]

        mkdir_p(results_dir())
        for name, data in parsed_datasets:
            path = '{}/{}.json'.format(results_dir(), name)
            with open(path, 'w+') as f:
                json.dump(data, f, indent=2)

    def clean_row(self, row):
        domain = row[0].lower()
        agency = self.domain_to_agency.get(domain, 'N/A')
        code = row[4]

        results = {
            'domain': domain,
            'agency': agency,
            'branch': self.agency_to_branch.get(agency, 'Executive')
        }

        if code:
            results['error'] = self.get_error_category(code)
            results['error_details'] = {
                'code': code,
                'typeCode': row[3],
                'message': row[5],
                'context': row[6],
                'selector': row[7],
            }

        return results

    def make_a11y_data(self, data):
        results = defaultdict(lambda: defaultdict(list))
        for d in data:
            if 'error' in d:
                results[d['domain']][d['error']].append(d['error_details'])
            else:
                results[d['domain']] = {}

        # using json de/encode to convert defaultdicts back to dicts
        return {'data': json.loads(json.dumps(results))}

    def make_agency_data(self, data):
        # first, group domain stats by agency
        data_by_agency = defaultdict(list)
        for d in self.make_domain_data(data)['data']:
            data_by_agency[d['agency']].append(d)

        # then, compute summary stats across groups
        results = []
        for agency, domain_stats in data_by_agency.items():
            pages = len(domain_stats)
            total_errors = sum(d['errors'] for d in domain_stats)
            entry = {
                'agency': agency,
                'pages_count': pages,
                'Average Errors per Page': (
                    'n/a' if pages == 0 else round(float(total_errors) / pages, 2)
                )
            }
            # add in averages by error category
            entry.update({
                e: round(mean([d['errorlist'][e] for d in domain_stats]), 2)
                for e in self.ERRORS.values()
            })
            results.append(entry)

        return {'data': results}

    def make_domain_data(self, data):
        results = {}
        for d in data:
            dom = d['domain']
            if dom not in results:
                results[dom] = {
                    'agency': d['agency'],
                    'branch': d['branch'],
                    'canonical': dom,
                    'domain': dom,
                    'errors': 0,
                    'errorlist': {e: 0 for e in self.ERRORS.values()}
                }
            if 'error' in d:
                results[dom]['errors'] += 1
                results[dom]['errorlist'][d['error']] += 1

        return {'data': list(results.values())}

    def get_error_category(self, code):
        error_id = code.split('.')[2].split('Guideline')[1]
        return self.ERRORS.get(error_id, 'Other Errors')

    @staticmethod
    def read_csv(filename):
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # TODO: make header row skip configurable
            return [row for row in reader]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--a11y', required=True)
    parser.add_argument('--domains', required=True)
    args = parser.parse_args()

    A11yProcessor(args.a11y, args.domains).run()
