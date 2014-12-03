#!/usr/bin/env ruby

# Script by Eric Mill to detect government domains in the Chrome HSTS Preload list.
#
# The Chrome HSTS Preload list is a hardcoded set of domains for which the browser
# will *only* ever access the site using HTTPS. If an http:// link to that site is
# encountered, the browser will just rewrite the URL to https:// before following
# it.
#
# This list is also incorporated into Firefox and Safari, making it a nice list to
# be on.
#
# "Second-level" domains (e.g. agency.gov, website.com) can be submitted to the list
# automatically, using the submission form at https://hstspreload.appspot.com. The
# domain must use the HSTS header, with the `includeSubdomains` flag included.
#
# Third- or fourth-level domains (e.g. 18f.gsa.gov, eric.mill.usesthis.com) must
# be emailed to the Chrome team directly, and added manually.
#
# In October 2014, 18F submitted 18f.gsa.gov and my.usa.gov to the Chrome HSTS
# Preload list, making them the first US government domains in the list. There are
# 3 domains from other governments: 1 from the UK, and 2 from Australia.

# Super-fast JSON parser.
require 'oj'

# Gman is Ben Balter's library to verify whether an email address
# is a government email address or not. This is used inside GitHub
# to determine whether or not user accounts are government users.
require 'gman'

# chrome.json is a snapshot of the "entries" field of the Chrome HSTS list at:
# https://chromium.googlesource.com/chromium/src/+/master/net/http/transport_security_state_static.json
entries = Oj.load(File.read("chrome.json"))
hsts_domains = entries.
  # limit it to entries that are forcing HTTPS (ignore public key pins)
  select {|e| e['mode'] == "force-https"}.
  # get a list of just the domain names
  map {|e| e['name']}

# Match each domain against Gman
matches = hsts_domains.select {|h| Gman.valid?(h) }

# As of 2014-11-09:
#
# [
#   "www.gov.uk",
#   "data.qld.gov.au",
#   "publications.qld.gov.au",
#   "18f.gsa.gov",
#   "my.usa.gov"
# ]
