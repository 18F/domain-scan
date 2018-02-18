var fs = require('fs');
var path = require('path');
const { URL } = require('url');

// Load in known third party service names.
const knownPath = path.join(__dirname, '..', 'utils', 'known_services.json');
const third_parties = JSON.parse(fs.readFileSync(knownPath, 'utf8'));



// JS entry point for third party scan.
module.exports = {
  scan: async (domain, environment, options, browser, page) => {
    const url = environment.url;

    var data = {
      external_domains: [],
      external_urls: []
    };

    // Trap each outgoing HTTP request to examine the URL.
    page.on('request', (request) => {
      processUrl(request.url(), data);
    });

    await page.goto(url);

    // TODO: make smarter use of timeouts and events to decide 'done'

    return data;
  }
}

var processUrl = (href, data) => {
  var url = new URL(href);

  if (!data.external_urls.includes(href))
    data.external_urls.push(href);

  if (!data.external_domains.includes(url.hostname))
    data.external_domains.push(url.hostname);
}
