'use strict';

// TEST_LOCAL will turn on debug output.
// TODO: Allow --debug to turn on debug output from CLI/Python-land.
// TODO: Move logging functions into base.js where possible.
var debug = false;
if (process.env.TEST_LOCAL) debug = true;

// Default overall timeout, in seconds.
// TODO: make timeout calculation way more sophisticated. :)
// TODO: Move timeout management into base.js where possible.
var default_timeout = 20;


// JS entry point for third party scan.
module.exports = {
  scan: async (domain, environment, options, browser, page) => {
    const url = environment.url;

    var data = {
      url: url
    };

    // Override puppeteer default of 30, especially since that
    // causes Lambda execution itself to timeout and halt.
    page.setDefaultNavigationTimeout(default_timeout * 1000);

    try {
      await page.goto(url);
    } catch (exc) {
      // if it's a timeout, that's okay, send back what we got.
      if (exc.message.includes("Navigation Timeout Exceeded"))
        return data;

      // otherwise, re-throw and handle higher up.
      else throw exc;
    }

    const html = await page.content();

    data.banner_bad_text = hasBadText(html);

    return data;
  }
}

var hasBadText = (html) => {
  return (html.search("Federal government websites always use a .gov or .mil domain.") >= 0)
};
