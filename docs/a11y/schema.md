# a11y schema

Every scan of a11y domains will need to be converted to JSON suitable for updating pulse.cio.gov. The following code JSON samples illustrate the files and schema that such conversion needs to target.

## tl;dr (just show me the code!)

Once you've completed an `a11y` scan run the following (requires Docker setup):

```sh
$ docker-compose run process_a11y
```

This will produce the following files inside of `scripts/pulse/results`:

- `domains.json`
- `a11y.json` TODO
- `agencies.json` TODO

## a11y.json

Schema:

A JSON object with a top-level key called `data`.

`data` contains a JSON object with the a domain as the top-level key containing another JSON object with keys for each error type.

```json
{
  "domain": {
    "Alt Tag Errors": [],
    "Color Contrast Errors": [],
    "Form Errors": [],
    "HTML\/Attribute Errors": [],
    "Other Errors": []
  }
}
```

Each error type has an array of error objects. Each error object is a JSON object with the following keys:

- `code`
- `typecode`
- `message`
- `context`
- `selector`
- `type`

These keys are taken directly from the results of a `pa11y` scan. Refer to the [`pa11y` docs](https://github.com/pa11y/pa11y) for a description of each field.

Example:

```json
{
  "data": {
    "18f.gov": {
      "Alt Tag Errors": [
        {
          "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
          "typeCode": "1",
          "message": "This text input element does not have a name available to an accessibility API. Valid names are: label element, title attribute.",
          "context": "<input type=\"text\" size=\"20\" name=\"q\" value=\"\">",
          "selector": "html > body > table:nth-child(3) > tbody > tr > td > table > tbody > tr > td:nth-child(2) > input:nth-child(1)",
          "type": "error"
        }
      ],
      "Color Contrast Errors": [
        {
          "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
          "typeCode": "1",
          "message": "This text input element does not have a name available to an accessibility API. Valid names are: label element, title attribute.",
          "context": "<input type=\"text\" size=\"20\" name=\"q\" value=\"\">",
          "selector": "html > body > table:nth-child(3) > tbody > tr > td > table > tbody > tr > td:nth-child(2) > input:nth-child(1)",
          "type": "error"
        }
      ],
      "Form Errors": [
        {
          "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
          "typeCode": "1",
          "message": "This text input element does not have a name available to an accessibility API. Valid names are: label element, title attribute.",
          "context": "<input type=\"text\" size=\"20\" name=\"q\" value=\"\">",
          "selector": "html > body > table:nth-child(3) > tbody > tr > td > table > tbody > tr > td:nth-child(2) > input:nth-child(1)",
          "type": "error"
        }
      ],
      "HTML\/Attribute Errors": [
        {
          "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
          "typeCode": "1",
          "message": "This text input element does not have a name available to an accessibility API. Valid names are: label element, title attribute.",
          "context": "<input type=\"text\" size=\"20\" name=\"q\" value=\"\">",
          "selector": "html > body > table:nth-child(3) > tbody > tr > td > table > tbody > tr > td:nth-child(2) > input:nth-child(1)",
          "type": "error"
        }
      ],
      "Other Errors": [
        {
          "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
          "typeCode": "1",
          "message": "This text input element does not have a name available to an accessibility API. Valid names are: label element, title attribute.",
          "context": "<input type=\"text\" size=\"20\" name=\"q\" value=\"\">",
          "selector": "html > body > table:nth-child(3) > tbody > tr > td > table > tbody > tr > td:nth-child(2) > input:nth-child(1)",
          "type": "error"
        }
      ]
    }
  }
}      
```

## agencies.json

Schema:

A JSON object with a top-level key called `data`.

`data` contains an array of JSON objects. Each JSON object describes error type totals for a given agency and has the following keys:

- `Agency` - the name of the agency
- `Average Errors per Page` - total errors for pages scanned belonging to that agency divided by number of pages scanned belonging to that agency
- `Alt Tag Errors`
- `HTML\/Attribute Errors`
- `Form Errors`
- `Color Contrast Errors`
- `Other Errors`
- `pages_count` - number of pages scanned belonging to that agency

Example:

```json
{
  "data": [
    {
      "Agency": "General Services Administration",
      "Average Errors per Page": 11,
      "Alt Tag Errors": 195,
      "HTML\/Attribute Errors": 180,
      "Form Errors": 77,
      "Color Contrast Errors": 508,
      "Other Errors": 17,
      "pages_count": 86
    }
  ]
}
```

## domains.json

Schema:

A JSON object with a top-level key called `data`.

`data` contains an array of JSON objects describing a domain's total a11y error counts with the following keys:

- `agency` - the name of the agency
- `branch` - the branch of the agency
- `canonical` -  the canonical URL of the agency
- `domain` - the domain of the agency
- `errors` - an integer count of the number of errors
- `errorlist` - a JSON object with the following keys (the values are the integer counts of the corresponding error types):
  - `Alt Tag Errors`
  - `Color Contrast Errors`
  - `HTML\/Attribute Errors`

Example:

```json
{
  "data": [
    {
      "agency": "General Services Administration",
      "branch": "Executive",
      "canonical": "http:\/\/18f.gov",
      "domain": "18f.gov",
      "errors": 0,
      "errorlist": {
        "Alt Tag Errors": 0,
        "Color Contrast Errors": 0,
        "HTML\/Attribute Errors": 0
      }
    }
  ]
}
```
