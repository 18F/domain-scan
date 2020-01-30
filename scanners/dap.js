'use strict';

// Used to parse for URL parameters.
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


// JS entry point for DAP scan.
module.exports = {
  scan: async (domain, environment, options, browser, page) => {
    const url = environment.url;

    var data = {
      domain: domain,
      status_code: -1,
      dap_detected: false,
      dap_parameters: ""
    };

    // Trap each outgoing HTTP request to see if we are submitting DAP data.
    page.on('request', (request) => {
      // When the browser is doing the request to the DAP analytics service,
      // the POST data and/or URL will contain the UA identifier, so this canonically
      // determines whether it is doing DAP or not!
      const requesturl = request.url();
      if (requesturl.includes('UA-33523145-1')) {
        data.dap_detected = true;
      }
      try {
        const postdata = request.postData();
        if (postdata.includes('UA-33523145-1')) {
          data.dap_detected = true;
        }
      } catch (err) {
        // there is no postdata, which is fine.
      }

      // get the dap_parameters from the query to dap.digitalgov.gov
      // TODO:  maybe parse the parameters into json or something more readable?
      if (request.url().includes('dap.digitalgov.gov/Universal-Federated-Analytics-Min.js')) {
        const requesturl = URL.parse(request.url());
        data.dap_parameters = requesturl.query;
      }
    });

    // get the status code once it becomes available
    page.on('response', (response) => {
      data.status_code = response.status();
    })


    // Override puppeteer default of 30, especially since that
    // causes Lambda execution itself to timeout and halt.
    page.setDefaultNavigationTimeout(default_timeout * 1000);

    try {
      await page.goto(url);
    } catch (exc) {
      // if there's a problem, that's fine, just return what we have.
      // console.log('problem scanning ' + domain + ' ' + exc.message);
      return data;
    }

    // TODO: make smarter use of timeouts and events to decide 'done'

    return data;
  }
};
