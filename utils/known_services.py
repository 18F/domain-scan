import re

######################################
#
# Bible of known third party services.
#
######################################

known_services = {
    'Google Analytics': ['www.google-analytics.com'],
    'Google Fonts': [
        'fonts.googleapis.com',
        'fonts.gstatic.com',
    ],
    'Google Custom Search Engine': ['cse.google.com'],
    'DoubleClick': ['stats.g.doubleclick.net'],

    'Digital Analytics Program': ['dap.digitalgov.gov'],
    'DigitalGov Search': ['search.usa.gov'],

    'RawGit CDN': ['cdn.rawgit.com'],
    'GitHub': ['raw.githubusercontent.com'],
    'Google CDN': ['ajax.googleapis.com'],
    'Bootstrap CDN': [
        re.compile('bootstrapcdn\.com$'),
    ],

    'GovDelivery': ['content.govdelivery.com'],
    'Facebook': [
        re.compile('facebook\.net$'),
        re.compile('facebook\.com$'),
        re.compile('fbcdn\.net$'),
    ],
    'Twitter': [
        re.compile('twitter\.com$'),
    ],
    'MixPanel': [
        re.compile('mixpanel\.com$'),
        re.compile('mxpnl\.com$'),
    ],

    'Brightcove': [
        re.compile('brightcove\.com$'),
    ],
    'AddThis': [
        re.compile('addthis\.com$'),
        re.compile('addthisedge\.com$'),
    ],
    'LinkedIn': [
        re.compile('linkedin\.com$'),
    ],
    'Pinterest': [
        re.compile('pinterest\.com$'),
    ],
    'Amazon S3': ['s3.amazonaws.com'],
}
