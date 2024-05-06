# CSV File format

## General
The CSV file format tries to stay close to the REST API in order to make it easy to
apply the REST API documentation to the CSV format.

See the REST API documentation here:
https://business-partners.int.demo.catena-x.net/companies/test-company/ui/swagger-ui/index.html#/business-partner-controller/upsertBusinessPartnersInput

## General structure
- The CSV file is a "character separated value" file, with one line per record and a header line
- The field separator can be comma (`,`), semicolon (`;`) or the tab character
- Lines can be separated by LF or CRLF
- The first line ("header line") contains the names of the fields (see below for details)
- There is a special mechanism for arrays of objects like they are in the JSON API

## Header line and fields
- The field names are derived from the JSON API at
  https://business-partners.int.demo.catena-x.net/companies/test-company/ui/swagger-ui/index.html#/business-partner-controller/upsertBusinessPartnersInput
- The field names for nested objects are created by separating the individual names by a dot
  - For example: The `addressBpn` field in the `address` top level entry will be named `address.addressBpn`
- There are a few special rules:
  - The top-level `nameParts` element is created using the field names `name1`, `name2`, ... `name9`
  - The name `physicalPostalAddress` is abbreviated to `physical`
  - The name `alternativePostalAddress` is abbreviated to `alternate`
  - There is a special notation for arrays of objects (see below)
- The minimum neccessary fields are
  - `externalId`
  - `name1`
  - `isOwnCompanyData`
