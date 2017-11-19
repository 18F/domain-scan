# Using domain-scan with Amazon Lambda

The domain-scan tool can execute compatible scanners in Amazon Lambda, instead of locally.

This can allow much higher numbers of parallel workers, as CPU- and memory-expensive operations can take place inside of separate Lambda functions, rather than on a single machine.

The domain-scan tool will still spin up a local thread for each Lambda function, but each thread will be doing much less, and will spend most of its life waiting for a Lambda function to return, so it's much more reasonable to use hundreds of workers.

Lambda's default limit for simultaneous function executions is 1000 per AWS account. On even a modest laptop or server, domain-scan can reasonably use 1000 workers to manage a rotating pool of Lambda functions executing and returning scans.

(In practice, you will likely want to give yourself some flex room to avoid flirting with hitting the limit. This tool's developer generally uses 900 workers.)

##### Preparing scanners for use in Lambda

To prepare for using domain-scan with Lambda, you will need to:

* Create an Amazon Web Services account, if you don't have one.
* Install the `awscli` Python package, which installs the `aws` command.
* Configure `aws` to have permission to write to Lambda and to read from CloudWatch. This usually means AWS API credentials, but if you're running this inside of an AWS service like EC2, you can use IAM roles to automatically grant permissions.

Then you'll need to create the functions in Lambda. This repository has tools to make that easy.

Lambda functions need to be uploaded as a zip file containing all necessary dependencies. Native dependencies (including Python modules that use C) need to have been compiled on an architecture compatible with Amazon Linux. Occasionally, there are Lambda-specific issues that require tweaks to how dependencies are installed. It can be annoying!

However, **this dependency compilation work is already done for you** by default. This repository contains a Lambda-ready set of dependencies at `lambda/envs/domain-scan.zip` that are sufficient to power [all tested Lambda-compatible scanners](#lambda-compatible-scanners). When creating a function, the contents of this zip file are mixed into a new zip file specific to each scanner.

Once you have an AWS account, and permissions to use Lambda, you'll be able to run the commands below and execute scans in Lambda right away.

##### Creating and updating Lambda functions

Once the preparation steps above are done, you will need to run a command to create each scan function individually in Lambda.

From the project root, using `pshtt` as an example:

```bash
./lambda/deploy pshtt --create
```

If you're making changes to a scanner, you'll need to update Lambda with the new function code after making the changes locally. You can update a function in place by running the deploy command _without_ the `--create` flag.

From the project root, using `pshtt` as an example:

```bash
./lambda/deploy pshtt
```

##### Using scanners in Lambda

Once Lambda functions are created in your AWS account, and your machine has permissions to invoke Lambda functions, all you need to do is add the `--lambda` flag:

```bash
./scan 18f.gsa.gov --scan=pshtt,sslyze --lambda
```

This will execute the core of each scan inside a Lambda function. Some scanners still may do some light per-domain prep work locally, or do heavy one-time initialization work locally (for example, downloading data from a third-party server once, so as to avoid hitting it from each Lambda worker), but the scanner's actual scanning will occur in Lambda.

You may wish to take advantage of the increased ability to use many simultaneous workers, especially with large batches:

```bash
./scan path/to/many-domains.csv --scan=pshtt,sslyze --lambda --workers=900
```


##### Lambda-compatible scanners

Currently, the only scanners tested for use in Lambda are:

* `pshtt` - Third party data sources, such as the Chrome preload list, will be downloaded at the top of the scan and then trimmed per-domain to avoid excessive network transfer to Lambda and to third party servers.
* `sslyze` - SSLyze will run in single-process mode inside Lambda, which lacks the `multiprocessing` features used by SSLyze's internal parallelization.

(**Note:** to use `--lambda`, all scanners you use should be Lambda-compatible and have functions created in your AWS account. You can't yet mix locally- and Lambda-executed scanners.)


## TODOs

Some notes on helpful additions to this system (contributions welcome!):

* Scripts in `lambda/` that can perform other common functions, such as adjusting timeouts.
* Automatically set/adjust Lambda function timeouts based on metadata managed inside Lambda-compatible scanners, such as a module-level `lambda_timeout` variable.
* A way to create test data that can be passed into the Lambda handler from the AWS console's `Test` button. An example for the `noop` scanner (a `task_noop` function) would be:

```json
{
  "scanner": "noop",
  "domain": "example.com",
  "environment": {
    "scan_uuid": "test-uuid",
    "scan_method": "lambda",
    "constant": 12345,
    "variable": "example.com"
  },
  "options": {
    "debug": true
  }
}
```
