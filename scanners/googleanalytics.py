import logging
import os
import json
import time

from scanners import utils
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

command = None
init = None


class GAChecker:

    def __init__(self):
        d = DesiredCapabilities.PHANTOMJS
        d['loggingPrefs'] = {'browser': 'ALL'}
        self.browser = webdriver.PhantomJS(desired_capabilities=d)

    def get_url(self, url):
        """ Get URL fron browser """
        self.browser.get(url)
        time.sleep(3)

    def run_checker_script(self):
        """ Runs the GA checker script """
        self.browser.execute_script("""
if (typeof ga === "function") {
    console.log('ga_version: Google Analytics Universal');
    console.log('ga_ua_code: ' + ga.getAll()[0].get('trackingId'));
    console.log('ga_anon_ip: ' + ga.getAll()[0].get('anonymizeIp'));
    console.log('ga_force_ssl: ' + ga.getAll()[0].get('forceSSL'));
}
else if (typeof _sendPageview === "function") {
    console.log('ga_version: Google Analytics Legacy');
    console.log('ga_ua_code: ' + _gat._getTrackerByName()._getAccount());
    console.log('ga_anon_ip: Google Analytics Legacy');
    console.log('ga_force_ssl: Google Analytics Legacy');
}
else {
    console.log('ga_version: No Google Analytics');
    console.log('ga_ua_code: No Google Analytics');
    console.log('ga_anon_ip: No Google Analytics');
    console.log('ga_force_ssl: No Google Analytics');
}
        """)

    def clean_message(self, element, message):
        """ Cleans the message log """
        return message.split(element)[-1].replace(' (:)', '').strip(': ')

    def parse_log(self):
        """ Check the log for the GA version """
        data = {}
        for item in self.browser.get_log('browser'):
            message = item.get('message', '')
            if "ga_version:" in message:
                data['ga_version'] = self.clean_message('ga_version', message)
            elif "ga_ua_code:" in message:
                data['ga_ua_code'] = self.clean_message('ga_ua_code', message)
            elif "ga_anon_ip" in message:
                data['ga_anon_ip'] = self.clean_message('ga_anon_ip', message)
            elif "ga_force_ssl" in message:
                data['ga_force_ssl'] = self.clean_message(
                    'ga_force_ssl', message)
        return data

    def organize_data(self, data):
        """ Organize data for export """
        return [data['ga_version'],
                data['ga_ua_code'],
                data['ga_anon_ip'],
                data['ga_force_ssl']]

    def scan(self, url, options):
        """ Check what version of Google Analytics and setting
        this site has """
        cache = utils.cache_path(url, "googleanalytics")
        if (options.get("force", False) is False) and (os.path.exists(cache)):
            logging.debug("\tCached.")
            raw = open(cache).read()
            data = json.loads(raw)
            if data.get('invalid'):
                return None
        else:
            logging.debug("\t %s %s --http" % (command, url))
            self.get_url("http:" + url)
            self.run_checker_script()
            data = self.parse_log()
            if not data:
                utils.write(utils.invalid({}), cache)
                return None
            utils.write(json.dumps(data), cache)

        data = self.organize_data(data)
        return data

    def quit_browser(self):
        """ stops browser """
        self.browser.quit()


scanner = GAChecker()


def scan(domain, options):

    return [scanner.scan(domain, options)]


def clean_up():
    scanner.browser.quit()

headers = ['ga_version', 'ga_ua_code', 'ga_anon_ip', 'ga_force_ssl']
