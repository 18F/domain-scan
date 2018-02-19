'use strict';

const fs = require('fs');
const path = require('path');
const URL = require('url');

// Load in known third party service names.
const knownPath = path.join(__dirname, '..', 'utils', 'known_services.json');
const known_services = JSON.parse(fs.readFileSync(knownPath, 'utf8'));



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
      unknown_services: []
    };

    // Trap each outgoing HTTP request to examine the URL.
    page.on('request', (request) => {
      var requested = request.url();

      // Ignore the original request to the page itself.
      if (requested != url)
        processUrl(requested, url, data);
    });

    await page.goto(url);

    // TODO: make smarter use of timeouts and events to decide 'done'

    return data;
  }
}

var processUrl = (href, sourceHref, data) => {
  var url = URL.parse(href);
  var source = URL.parse(sourceHref);

  let www_host, root_host;

  // Isolate the hostname with or without a www prefix,
  // and treat them effectively as the same hostname.
  if (url.hostname.startsWith("www.")) {
    www_host = url.hostname
    root_host = www_host.replace(/^www\./, "")
  } else {
    www_host = "www." + url.hostname
    root_host = url.hostname
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
          data.known_services.push(name)

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
var baseDomainFor = (input) => {
  return input.split("\.").slice(-2).join("\.");
};
