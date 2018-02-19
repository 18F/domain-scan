
/**
* Node-based Lambda handler for headless browser scan functions.
*/

exports.handler = (event, context, callback) => {
  // Tell Lambda to shut it down after the callback executes,
  // even if the container still has stuff (e.g. Chrome) running.
  context.callbackWaitsForEmptyEventLoop = false;

  // start_time = new Date();

  var domain = event.domain;
  var options = event.options || {};
  var name = event.scanner;
  var environment = event.environment || {};

  // Log all events for debugging purposes.
  console.log("Starting:")
  console.log(event);

  // TODO: error handling around these.
  // base = require("./scanners/headless/base")
  // scanner = require("./scanners/" + name);

  var data = scan(
    domain, environment, options, // scanner,
    function(err, data) {
      // We capture start and end times locally as well, but it's
      // useful to know the start/end from Lambda's vantage point.
      // end_time = new Date()
      // duration = end_time - start_time

      // response = {
      //   lambda: {
      //     log_group_name: context.log_group_name,
      //     log_stream_name: context.log_stream_name,
      //     request_id: context.aws_request_id,
      //     memory_limit: context.memory_limit_in_mb,
      //     // start_time: start_time,
      //     // end_time: end_time,
      //     // measured_duration: duration
      //   },
      //   data: data
      // }

      // TODO: JSON datetime sanitization, like the Python handler does.
      callback(null, data);
    }
  );
};


const puppeteer = require('puppeteer');
var path = require('path');
var fs = require('fs');
var tar = require('tar');

var scan = async function (domain, environment, options, callback) {

  const browser = await getBrowser();

  console.log("getting new page")
  const page = await browser.newPage();
  console.log("got new page");
  var data;

  // Do the scanner-specific heavy lifting.
  try {
    // data = await scanner.scan(domain, environment, options, browser, page);
    var url = environment.url;
    console.log("going to: " + url)
    await page.goto(url);
    console.log("getting content")
    data = await page.content();
  } catch (err) {
    await browser.close();
    return callback(err)
  }

  await browser.close();

  // TODO: error handling
  return callback(null, data);
};


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

const debugLog = (log) => {
  let message = log;
  if (typeof log === 'function') message = log();
  Promise.resolve(message).then(
    (message) => console.log(message)
  );
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

        // puppeteer 1.1.0 broke dumpio. Should be fixed soon.
        // dumpio: true
      });

      var version = await browser.version()
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
  var event = {
    domain: "konklone.com",
    options: {},
    environment: {url: "https://konklone.com/"}
  }
  var context = {}
  var callback = function(err, data) {
    console.log("Done:");
    console.log(err);
    console.log(data);
  }

  exports.handler(event, context, callback);
}
