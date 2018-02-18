#!/usr/bin/env node

const headless = require("./base")

default_timeout = 60

// TODO:
// timeout = int(options.get("timeout", default_timeout))

// JS entry point for third party scan.
async function scan(domain, environment, options) {

  headless.execute(
    domain, environment, options,

    async (browser, page) => {
      return await page.content()
    },

    (err, data) => {
      if (err) process.exit(1);
      console.log(data)
    }
  )
}

// the first command line argument is JSON-serialized data
const params = JSON.parse(process.argv[2]);

// When executed, run the scan function
scan(params.domain, params.environment, params.options);
