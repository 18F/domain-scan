#!/usr/bin/env node

const puppeteer = require('puppeteer');

const chromeOptions = [
  // Resolves error:
  //    error when launch(); No usable sandbox! Update your kernel
  '--no-sandbox',

  // Resolves error:
  //    error when launch(); Failed to load libosmesa.so
  '--disable-gpu',

  // Resolves error: freeze when newPage()
  '--single-process'
];

var scan = async function (domain, environment, options, scanner, callback) {

  const url = environment['url']

  // console.log("[" + domain + "] Opening URL: " + url);

  const browser = await puppeteer.launch({
    headless: true,
    // executablePath: config.executablePath,
    args: chromeOptions
  });

  const page = await browser.newPage();
  await page.goto(url);

  // Do the scanner-specific heavy lifting.
  const data = await scanner.scan(browser, page);

  await browser.close();

  // put standard values into the return data
  data.url = url;
  data.domain = domain;

  // TODO: error handling
  callback(null, data);
};

/********************************************************
** TODO: move this to its own CLI-specific interface file
*********************************************************/

// the first argument passed in is the name of the scanner
const scanner = require("./" + process.argv[2]);

// the second argument passed is JSON-serialized data
const params = JSON.parse(process.argv[3]);

// When executed, run the scan function
scan(
  params.domain, params.environment, params.options,
  scanner,
  function(err, data) {
    if (err) process.exit(1);
    console.log(JSON.stringify(data))
  }
);