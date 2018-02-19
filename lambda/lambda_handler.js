
/**
* Node-based Lambda handler for headless browser scan functions.
*/

exports.handler = (event, context, callback) => {
  start_time = new Date();

  domain = event.domain;
  options = event.options || {};
  name = event.scanner;
  environment = event.environment || {};

  // Log all events for debugging purposes.
  console.log(event);

  // TODO: error handling around these.
  base = require("./scanners/headless/base")
  scanner = require("./scanners/" + name);

  data = base.scan(
    domain, environment, options, scanner,
    function(err, data) {
      // We capture start and end times locally as well, but it's
      // useful to know the start/end from Lambda's vantage point.
      // end_time = new Date()
      // duration = end_time - start_time

      response = {
        lambda: {
          log_group_name: context.log_group_name,
          log_stream_name: context.log_stream_name,
          request_id: context.aws_request_id,
          memory_limit: context.memory_limit_in_mb,
          // start_time: start_time,
          // end_time: end_time,
          // measured_duration: duration
        },
        data: data
      }

      // TODO: JSON datetime sanitization, like the Python handler does.
      callback(null, response);
    }
  );
};