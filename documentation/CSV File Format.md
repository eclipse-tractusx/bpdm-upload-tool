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
- The field names are derived from the JSON API (see link above)
- The field names for nested objects are created by separating the individual names by a dot
  - For example: The `addressBpn` field in the `address` top level entry will be named `address.addressBpn`
- There are a few special rules:
  - The top-level `nameParts` element is created using the field names `name1`, `name2`, ... `name9`
  - The name `physicalPostalAddress` is abbreviated to `physical`
  - The name `alternativePostalAddress` is abbreviated to `alternate`
- The minimum neccessary fields are
  - `externalId`
  - `isOwnCompanyData`

## Arrays
The following elements of a record are arrays in the REST API:
- `identifiers.*`
- `states.*`
- `roles`
- `legalEntity.states.*`
- `site.states.*`
- `address.states.*`

Each time, a new `externalId` is encountered, this line will become the main data source from which
all data fields for the REST API are populated. If values are provided for fields that can be arrays
in the CSV file, the first array element will be populated with the data from the main line.
In order to add more elements to an array, it is possible to add lines containing further array elements
immediately the main line. These follow-up-lines must contain the same `externalId` again and data
for exactly one array.

For example, if you want to add a second `identifiers` element, create a second line where only
the following fields are set:
- `extenalId` (same as in the main line)
- `identifiers.type`
- `identifiers.value`
- `identifiers.issuingBody`
If you also want to provide a second element for `site.states`, do *not* set those fields
in the same line. Instead, create a third line with the respective values.

## NOTICE

This work is licensed under the [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).

- SPDX-License-Identifier: Apache-2.0
- SPDX-FileCopyrightText: 2024 ZF Friedrichshafen AG
- SPDX-FileCopyrightText: 2024 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
- Source URL: https://github.com/eclipse-tractusx/bpdm-upload-tool
