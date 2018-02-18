#!/usr/bin/env node

const puppeteer = require('puppeteer');

const options = [

  // error when launch(); No usable sandbox! Update your kernel
  '--no-sandbox',

  // error when launch(); Failed to load libosmesa.so
  '--disable-gpu',

  // freeze when newPage()
  '--single-process'
];

exports.execute = ((event, context, callback) => {

  const domain = event['domain']
  const url = event.options['url']

  console.log("[" + domain + "] Opening URL: " + url);

  (async () => {
    const browser = await puppeteer.launch({
      headless: true,
      // executablePath: config.executablePath,
      args: options
    });

    const page = await browser.newPage();
    await page.goto(url);

    //
    const body = await page.content();

    await browser.close();

    callback(null, body);
  })();

});
