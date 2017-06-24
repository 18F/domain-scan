import unittest

from scripts.a11y.process_a11y import A11yProcessor


class ProcessA11yTestCase(unittest.TestCase):
    a11y_filename = 'tests/data/a11y.csv'
    domain_filename = 'tests/data/domains.csv'

    def setUp(self):
        self.a11y = A11yProcessor(self.a11y_filename, self.domain_filename)

    def test_branch_lookup(self):
        branch_lookup = self.a11y.agency_to_branch
        self.assertEqual(branch_lookup.get('U.S. Capitol Police'), 'Legislative')
        self.assertEqual(branch_lookup.get('U.S Courts'), 'Judicial')
        self.assertIsNone(branch_lookup.get('foo'))

    def test_agency_lookup(self):
        agency_lookup = self.a11y.domain_to_agency
        self.assertEqual(agency_lookup.get('achp.gov'), 'Advisory Council on Historic Preservation')
        self.assertEqual(agency_lookup.get('acus.gov'), 'Administrative Conference of the United States')

    def test_row_cleaner(self):
        clean = self.a11y.clean_row(self.a11y.a11y_raw[0])
        self.assertEqual(clean['agency'], 'Administrative Conference of the United States')
        self.assertEqual(clean['branch'], 'Executive')
        self.assertEqual(clean['error'], 'Missing Image Descriptions')
        self.assertEqual(
            clean['error_details']['code'],
            'WCAG2AA.Principle1.Guideline1_1.1_1_1.H30.2'
        )

    def test_error_lookup(self):
        error_lookup = self.a11y.get_error_category
        self.assertEqual(
            error_lookup('WCAG2AA.Principle1.Guideline1_1.1_1_1.H30.2'),
            'Missing Image Descriptions'
        )
        self.assertEqual(
            error_lookup('other.error.Guideline123_456.1_1_1.H30.2'),
            'Other Errors'
        )


if __name__ == '__main__':
    unittest.main()
