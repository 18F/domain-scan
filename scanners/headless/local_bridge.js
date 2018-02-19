#!/usr/bin/env node

/******
* Part of a Python<->Node bridge for local scans.
*
* Executed by local_bridge.py, to send scan parameters and
* receive scan responses over the CLI and STDOUT.
*******/

var base = require("./base")

// the first argument passed in is the name of the scanner
const scanner = require("../" + process.argv[2]);

// the second argument passed is JSON-serialized data
const params = JSON.parse(process.argv[3]);

var go = async () => {

  // Load the Chrome browser from the local system.
  const puppeteer = require('puppeteer');
  const browser = await puppeteer.launch({
      // TODO: Let executable path be overrideable.
      // executablePath: config.executablePath,
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-gpu',
        '--single-process'
      ]
    });

  // Execute the scan using the passed-in data, and the
  // locally launched headless Chrome browser.
  base.scan(
    params.domain, params.environment, params.options,
    browser, scanner,
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
