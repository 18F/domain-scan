#!/usr/bin/env node

const headless = require("./base")

// TODO:
// take in URL (and other options) over STDIN

async function main() {
  headless.execute({
      domain: "example.com",
      options: {
        url: "https://example.com/"
      }
    }, {},
    (err, data) => console.log(data)
  )
}

main();
