#!/usr/bin/env node

const puppeteer = require('puppeteer');

const chromeOptions = [

  // TODO: in Lambda, turn on --no-sandbox
  // error when launch(); No usable sandbox! Update your kernel
  '--no-sandbox',

  // TODO: in Lambda, turn on --disable-gpu
  // error when launch(); Failed to load libosmesa.so
  '--disable-gpu',

  // freeze when newPage()
  '--single-process'
];

// Future Lambda handler.
exports.handler = ((event, context, callback) => {
});

exports.execute = ((domain, environment, options, scanner, callback) => {

  const url = environment['url']

  console.log("[" + domain + "] Opening URL: " + url);

  (async () => {
    const browser = await puppeteer.launch({
      headless: true,
      // executablePath: config.executablePath,
      args: chromeOptions
    });

    const page = await browser.newPage();
    await page.goto(url);

    // Do the scanner-specific heavy lifting.
    const data = await scanner(browser, page);

    await browser.close();

    callback(null, data);
  })();

});
