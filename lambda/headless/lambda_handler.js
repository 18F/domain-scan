'use strict';

/**
* Node-based Lambda handler for headless browser scan functions.
*/

exports.handler = (event, context, callback) => {
  var start_time = new Date().getTime() / 1000;

  // Tell Lambda to shut it down after the callback executes,
  // even if the container still has stuff (e.g. Chrome) running.
  context.callbackWaitsForEmptyEventLoop = false;

  var domain = event.domain;
  var options = event.options || {};
  var name = event.scanner;
  var environment = event.environment || {};

  // Log all events for debugging purposes.
  console.log(event);

  // TODO: error handling around these.
  var base = require("./scanners/headless/base");
  var scanner = require("./scanners/" + name);

  base.scan(
    domain, environment, options,
    getBrowser, scanner,
    function(err, data) {
      // We capture start and end times locally as well, but it's
      // useful to know the start/end from Lambda's vantage point.
      var end_time = new Date().getTime() / 1000;
      var duration = end_time - start_time;

      var response = {
        lambda: {
          log_group_name: context.logGroupName,
          log_stream_name: context.logStreamName,
          request_id: context.awsRequestId,
          memory_limit: context.memoryLimitInMB,
          start_time: start_time,
          end_time: end_time,
          measured_duration: duration
        }
      }

      if (err) {
        if (err instanceof Error)
          response.error = err.stack;
        else
          response.error = err;
      }

      if (data === undefined) {
        response.data = null;
        if (!err)
          response.error = "Data came back undefined for some reason.";
      }
      else
        response.data = data;

      // TODO: JSON datetime sanitization, like the Python handler does.
      callback(null, response);
    }
  );
};


const puppeteer = require('puppeteer');
var path = require('path');
var fs = require('fs');
var tar = require('tar');

const setupLocalChrome = () => {
  return new Promise((resolve, reject) => {
    fs.createReadStream(localChromePath)
    .on('error', (err) => reject(err))
    .pipe(tar.x({
      C: setupChromePath,
    }))
    .on('error', (err) => reject(err))
    .on('end', () => resolve());
  });
};

const localChromePath = path.join('headless_shell.tar.gz');
const setupChromePath = path.join(path.sep, 'tmp');
const executablePath = path.join(
    setupChromePath,
    'headless_shell'
);


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


// Async function to load Chrome from the Lambda container.
var getBrowser = (() => {
  let browser;
  return async () => {
    // idempotence
    if (typeof browser === 'undefined' || !await isBrowserAvailable(browser)) {

      // extract .tar.gz to tmp/
      await setupLocalChrome();

      // load the browser from its extracted path
      browser = await puppeteer.launch({
        headless: true,
        executablePath: executablePath,
        args: chromeOptions,
        ignoreHTTPSErrors: true,

        // puppeteer 1.1.0 broke dumpio. Should be fixed soon.
        // dumpio: true
      });

      var version = await browser.version();
      console.log("Launched: " + version);
    }
    return browser;
  };
})();

const isBrowserAvailable = async (browser) => {
  try {
    await browser.version();
  } catch (e) {
    console.log(e); // not opened etc.
    return false;
  }
  return true;
};


/** local test run **/

if (process.env.TEST_LOCAL) {
  var domain = process.argv[2];

  var event = {
    domain: domain,
    scanner: "third_parties",
    options: {},
    environment: {url: "https://" + domain + "/"}
  }
  var context = {}
  var callback = function(err, data) {
    console.log("Done:\n");

    if (err) {
      console.log("Error:")
      if (err instanceof Error)
        console.log(err.stack);
      else
        console.log(error);
    }

    if (data) {
      console.log("Data:")
      console.log(data);
    }
  }

  exports.handler(event, context, callback);
}
