#!/usr/bin/env node

/******
* Part of a Python<->Node bridge for local scans.
*
* Executed by local_bridge.py, to send scan parameters and
* receive scan responses over the CLI and STDOUT.
*******/

const puppeteer = require('puppeteer');
var base = require("./base")

// the first argument passed in is the name of the scanner
const scanner = require("../" + process.argv[2]);

// the second argument passed is (ordinarily) JSON-serialized data
var params;

// Hook to allow slightly easier debugging.
// TEST_LOCAL=1 ./scanners/headless/local_bridge.js third_parties example.com
if (process.env.TEST_LOCAL) {
  domain = process.argv[3];
  params = {
    domain: domain,
    options: {},
    environment: {url: "https://" + domain + "/"}
  }
}

// Ordinarily, parse in the full params from a JSON-serialized blob.
else
  params = JSON.parse(process.argv[3]);

// Async function to load Chrome from the local system.
var getBrowser = async () => {
  return await puppeteer.launch({
    // TODO: Let executable path be overrideable.
    // executablePath: config.executablePath,
    headless: true,
    ignoreHTTPSErrors: true,
    args: [
      '--no-sandbox',
      '--disable-gpu',
      '--single-process'
    ]
  });
};

var go = async () => {

  // Execute the scan using the passed-in data, and the
  // locally launched headless Chrome browser.
  base.scan(
    params.domain, params.environment, params.options,
    getBrowser, scanner,
    function(err, data) {
      if (err) {
        console.error(err);
        process.exit(1);
      }
      console.log(JSON.stringify(data))
    }
  );

};

go();
