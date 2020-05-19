#!/usr/bin/env node

/**
 * Lighthouse scanner
 * This module orchestrates parallel Lighthouse scans over one headless Chrome
 * instance.
 */

const chromeLauncher = require('chrome-launcher');
const lighthouse = require('lighthouse');
const puppeteer = require('puppeteer');


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

function launchChromeAndRunLighthouse(url, opts, config = null) {
  return chromeLauncher.launch({chromeFlags: opts.chromeFlags}).then(chrome => {
    opts.port = chrome.port;
    return lighthouse(url, opts, config).then(results => {
      return chrome.kill().then(() => results.lhr)
    });
  });
}

const opts = {
  chromeFlags: ['--headless', '--no-sandbox']
};

/*
function configure() {
  let port;
  chromeLauncher.launch({
    chromeFlags: ['--headless', '--no-sandbox']
  }).then(chrome => {
    port = chrome.port
  });
}

launchChromeAndRunLighthouse('https://www.whitehouse.gov', opts).then(results => {
  console.log(results);
});
*/

getBrowser().then(async browser => {
  const url = 'https://www.whitehouse.gov';
  const {lhr} = await lighthouse(url, {
    port: (new URL(browser.wsEndpoint())).port,
    output: 'json',
    logLevel: 'info',
  });
  console.log(lhr);
  await browser.close();
});
