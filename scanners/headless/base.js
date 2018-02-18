const puppeteer = require('puppeteer');

const options = [
  // error when launch(); No usable sandbox! Update your kernel
  '--no-sandbox',
  // error when launch(); Failed to load libosmesa.so
  // '--disable-gpu',
  // freeze when newPage()
  // '--single-process'
];

exports.handler = ((event, context, callback) => {

  (async () => {
    const browser = await puppeteer.launch({
      headless: true,
      // executablePath: config.executablePath,
      args: options
    });

    const page = await browser.newPage();
    await page.goto('https://example.com');

    // Get the "viewport" of the page, as reported by the page.
    const dimensions = await page.evaluate(() => {
      return {
        width: document.documentElement.clientWidth,
        height: document.documentElement.clientHeight,
        deviceScaleFactor: window.devicePixelRatio
      };
    });

    await browser.close();

    callback(null, dimensions);
  })();

});
