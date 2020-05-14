'use strict';

const lighthouse = require('lighthouse');


const LIGHTHOUSE_AUDITS = [
    'color-contrast',
    'font-size',
    'image-alt',
    'input-image-alt',
    'performance-budget',
    'speed-index',
    'tap-targets',
    'timing-budget',
    'total-byte-weight',
    'unminified-css',
    'unminified-javascript',
    'uses-text-compression',
    'viewport',
]


// JS entry point for Lighthouse scan.
module.exports = {
  scan: async (domain, environment, options, browser, page) => {
    const url = 'https://' + domain;
    try {
      const output = await lighthouse(url, {
        port: (new URL(browser.wsEndpoint())).port,
        onlyAudits: LIGHTHOUSE_AUDITS,

        disableStorageReset: false,
        saveAssets: false,
        listAllAudits: false,
        listTraceCategories: false,
        printConfig: false,
        output: [ 'json' ],
        chromeFlags: '',
        enableErrorReporting: false,
        logLevel: 'silent',
        outputPath: 'stdout',
      });
      return output.lhr.audits;

    } catch (exc) {
      return {
        error: exc.message
      }
    }
  }
}
