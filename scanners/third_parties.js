var fs = require('fs');
var path = require('path');

// TODO: use this, allow override
const maximum_timeout = 60

// TODO: use this, based on ???
const minimum_timeout = 10

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
      data.external_urls.push(request.url());
    });

    // TODO: make use of minimum and maximum timeouts
    await page.goto(url);

    return data;
  }
}
