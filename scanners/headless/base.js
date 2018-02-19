
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

  const browser = await puppeteer.launch({
    headless: true,
    // executablePath: config.executablePath,
    args: chromeOptions
  });

  const page = await browser.newPage();
  var data;

  // Do the scanner-specific heavy lifting.
  try {
    data = await scanner.scan(domain, environment, options, browser, page);
  } catch (exc) {
    await browser.close();
    return callback(exc)
  }

  await browser.close();

  // TODO: error handling
  return callback(null, data);
};

module.exports = {scan: scan}
