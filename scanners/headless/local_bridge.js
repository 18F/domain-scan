#!/usr/bin/env node

/******
* Part of a Python<->Node bridge for local scans.
*
* Executed by local_bridge.py, to send scan parameters and
* receive scan responses over the CLI and STDOUT.
*******/

var base = require("./base")

// the first argument passed in is the name of the scanner
const scanner = require("../" + process.argv[2]);

// the second argument passed is JSON-serialized data
const params = JSON.parse(process.argv[3]);

// When executed, run the scan function
base.scan(
  params.domain, params.environment, params.options,
  scanner,
  function(err, data) {
    if (err) {
      console.error(err);
      process.exit(1);
    }
    console.log(JSON.stringify(data))
  }
);