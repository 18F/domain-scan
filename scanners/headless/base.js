'use strict';


var scan = async function (domain, environment, options, getBrowser, scanner, callback) {
  const browser = await getBrowser();

  const page = await browser.newPage();
  var data;

  // Do the scanner-specific heavy lifting.
  try {
    data = await scanner.scan(domain, environment, options, browser, page);
  } catch (exc) {
    await browser.close();
    return callback(exc);
  }

  await browser.close();

  // TODO: error handling
  return callback(null, data);
};

module.exports = {scan: scan};
