'use strict';

// Load in known third party service names.
const fs = require('fs');
const path = require('path');
const knownPath = path.join(__dirname, '..', 'utils', 'known_services.json');
const known_services = JSON.parse(fs.readFileSync(knownPath, 'utf8'));

// Used to parse third party hostnames.
const URL = require('url');

// TEST_LOCAL will turn on debug output.
// TODO: Allow --debug to turn on debug output from CLI/Python-land.
// TODO: Move logging functions into base.js where possible.
var debug = false;
if (process.env.TEST_LOCAL) debug = true;

// Default overall timeout, in seconds.
// TODO: make timeout calculation way more sophisticated. :)
// TODO: Move timeout management into base.js where possible.
var default_timeout = 20;


// JS entry point for third party scan.
module.exports = {
  scan: async (domain, environment, options, browser, page) => {
    const url = environment.url;

    var data = {
      url: url,

      external_domains: [],
      external_urls: [],
      internal_domains: [],
      internal_urls: [],
      nearby_urls: [],
      nearby_domains: [],
      known_services: [],
      unknown_services: [],
      page_urls: [],
      page_domains: []
    };

    // Trap each outgoing HTTP request to examine the URL.
    page.on('request', (request) => {
      processUrl(request.url(), url, data);
    });

    // Override puppeteer default of 30, especially since that
    // causes Lambda execution itself to timeout and halt.
    page.setDefaultNavigationTimeout(default_timeout * 1000);

    try {
      await page.goto(url);
    } catch (exc) {
      // if it's a timeout, that's okay, send back what we got.
      if (exc.message.includes("Navigation Timeout Exceeded"))
        return data;

      // otherwise, re-throw and handle higher up.
      else throw exc;
    }

    // find all the URLs/domains on the page
    const html = await page.content();
    data.page_urls = pageurls(html);
    const allpagedomains = data.page_urls.map(getDomainFromURL);
    data.page_domains = [...new Set(allpagedomains)];

    // TODO: make smarter use of timeouts and events to decide 'done'

    return data;
  }
};

var pageurls = (html) => {
  var urlRegex =/(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
  return [...new Set(html.match(urlRegex))];
}

var getDomainFromURL = (href) => {
  var url = URL.parse(href);
  return url.hostname;
}

var processUrl = (href, sourceHref, data) => {
  if (debug) console.log("URI: " + href);

  // Ignore blob: and data: URIs, these do not generate an external request.
  // Catch them before running URL.parse(), since they are not URLs and the
  // URL.parse() function does not parse them correctly.
  var abort = false;
  ["data:", "blob:"].forEach(function(protocol) {
    if (href.toLowerCase().startsWith(protocol)) abort = true;
  });
  if (abort) return;

  var url = URL.parse(href);
  var source = URL.parse(sourceHref);

  // Ignore the original request to the page itself.
  if (href == sourceHref) return;

  let www_host, root_host;

  // Isolate the hostname with or without a www prefix,
  // and treat them effectively as the same hostname.
  if (url.hostname.startsWith("www.")) {
    www_host = url.hostname;
    root_host = www_host.replace(/^www\./, "");
  } else {
    www_host = "www." + url.hostname;
    root_host = url.hostname;
  }

  var base_host = baseDomainFor(root_host);
  var source_base = baseDomainFor(source.hostname);

  /***
  * There are 4 cases:
  * - internal: same hostname (or with a www prefix) as the source URL.
  * - nearby: same base domain, different (non-www) subdomain as source URL.
  * - affiliated: known to be affiliated in some way. (TBD)
  * - external: different base domain from source URL.
  ***/

  var hostType;

  // Case 1: internal
  if (
    (www_host == source.hostname) ||
    (root_host == source.hostname)
  ) {
    hostType = "internal";

    if (!data.internal_urls.includes(href))
      data.internal_urls.push(href);

    // Log www and root requests separately. They are only treated
    // the same when calculating internal-ness, as they can still have
    // different technical ramifications.
    if (!data.internal_domains.includes(url.hostname))
      data.internal_domains.push(url.hostname);
  }

  // Case 2: nearby
  else if (base_host == source_base) {
    hostType = "nearby";

    if (!data.nearby_urls.includes(href))
      data.nearby_urls.push(href);

    if (!data.nearby_domains.includes(url.hostname))
      data.nearby_domains.push(url.hostname);
  }

  // TODO: Case 3: affiliated
  // Allow additional provided affiliated suffixes.
  // For example, allow ".gov" to be considered affiliated.

  // Case 4: external
  else {
    hostType = "external";

    if (!data.external_urls.includes(href))
      data.external_urls.push(href);

    if (!data.external_domains.includes(url.hostname))
      data.external_domains.push(url.hostname);
  }

  // Check every URL (even internal/nearby/affiliated ones)
  // against the list of known services.
  var known = false;
  for (var name in known_services) {
    var services = known_services[name];
    for (var service of services) {

      // Either an exact match, or can share a suffix with a known
      // service-owned hostname.
      if (
        (www_host == service) ||
        (root_host == service) ||
        (root_host.endsWith(service))
      ) {

        if (!data.known_services.includes(name))
          data.known_services.push(name);

        known = true;
        break;
      }
    }
  }

  // Specifically call out unknown external services for research.
  if (!known && (hostType == "external")) {
    if (!data.unknown_services.includes(url.hostname))
      data.unknown_services.push(url.hostname);
  }
};

// For now, a naive base domain calculation.
// TODO: use the Public Suffix List.
// TODO: may be useful to move to base.js or make a utils.js file.
var baseDomainFor = (input) => {
  return input.split("\.").slice(-2).join("\.");
};
