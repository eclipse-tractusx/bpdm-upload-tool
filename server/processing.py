################################################################################
# Copyright (c) 2024 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
################################################################################

import io
import os.path
import html
import csv
import json
import base64
import logging
from pprint import pprint, pformat

import requests

import common
from job import Job
import csv_tools
import convert_csv
import convert_json
import sharing_state_csv

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

CHUNK_SIZE = 100

# Swagger: https://business-partners.int.demo.catena-x.net/companies/test-company/ui/swagger-ui/index.html#/business-partner-controller/upsertBusinessPartnersInput
AUTH_URL = "https://centralidp.dev.demo.catena-x.net/auth/realms/CX-Central/protocol/openid-connect/token"
BASE_URL = "https://business-partners.dev.demo.catena-x.net/companies/test-company/v6/"

CREDENTIALS = None      # will be set in init()

def init():
    """Initialize processing. This is called once when the server starts

    We currently keep the data in global variables. This might be changed later."""

    global CREDENTIALS                      # pylint: disable=global-statement

    with open( common.CREDENTIALS_FILE, "r", encoding="utf-8" ) as fh:
        CREDENTIALS = json.load( fh )


def run_job( job: Job, data: bytes|str, func ) -> None:
    """Process a CSV file

    This is the main entry point for a job. It will call the actual processing function."""
    logger.info( "Processing job %s", job.name )

    try:
        func( job, data )
    except UnicodeDecodeError as ex:
        logger.error( "File is not valid UTF-8: %s", ex )
        job.status.append( f'<li class="progress_error">Encoding Error: {html.escape(str(ex))}</li>' )
    except csv_tools.CSVException as ex:
        logger.error( "Error in CSV: %s", ex )
        job.status.append( f'<li class="progress_error">CSV Error: {html.escape(str(ex))}</li>' )
    except Exception as ex:
        logger.error( "Error: %s", ex )
        job.status.append( f'<li class="progress_error">Error: {html.escape(str(ex))}</li>' )

    job.status.append( "<li>Done</li>" )
    job.done = True


def upload_file( job: Job, data: bytes ) -> None:
    """Do the actual processing of the CSV file.

    Should not be called directly, but via run_job()"""

    job.status.append( "<li>Converting CSV...</li>" )

    reader = _get_reader( data )

    record_objects = convert_csv.convert( reader )
    record_dicts = [ d.to_dict() for d in record_objects ]
    json_data_readable = json.dumps( record_dicts, indent=4, ensure_ascii=False ).encode("utf-8")

    job.status.append( "<li>Conversion successful</li>" )

    # save the converted data for debugging purposes
    with open( os.path.join( common.UPLOAD_FOLDER, job.name + ".json" ), "wb" ) as fh:
        fh.write( json_data_readable )

    # Now upload the data
    access_token = _get_access_token()

    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    total = 0
    while len( record_dicts ) > 0:
        chunk = record_dicts[:CHUNK_SIZE]
        record_dicts = record_dicts[CHUNK_SIZE:]

        json_data = json.dumps( chunk ).encode("utf-8")
        response = requests.put( BASE_URL + "input/business-partners", headers=headers, verify=common.VERIFY_SSL, data=json_data, timeout=30 )
        logger.info( "chunk [%d, %d]: Status %d", total, total + len(chunk) - 1, response.status_code )
        response.raise_for_status()
        total += len(chunk)
        job.status.append( f"<li>Uploaded {total} records</li>" )


def get_sharing_state( job: Job, data: bytes ) -> None:
    """Get the sharing state for a list of external IDs.

    Should not be called directly, but via run_job()"""

    job.status.append( "<li>Getting External IDs from CSV...</li>" )

    reader = _get_reader( data )
    external_ids = sharing_state_csv.get_external_ids( reader )
    job.status.append( f"<li>{len(external_ids)} external IDs found</li>" )
    if len(external_ids) == 0:
        job.status.append( "<li>Done</li>" )
        job.done = True
        return

    access_token = _get_access_token()

    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    result = [[ "externalId", "businessPartnerType", "sharingStateType", "sharingErrorCode", "sharingErrorMessage", "bpn", "sharingProcessStarted", "taskId" ]]

    total = 0
    while len( external_ids ) > 0:
        chunk = external_ids[:CHUNK_SIZE]
        external_ids = external_ids[CHUNK_SIZE:]

        params = {
            "page": 0,
            "size": CHUNK_SIZE,
            "businessPartnerType": "GENERIC",
            "externalIds": chunk
        }

        response = requests.get( BASE_URL + "sharing-state", headers=headers, verify=common.VERIFY_SSL,
                            params=params, timeout=30 )
        logger.info( "chunk [%d, %d]: Status %d", total, total + len(chunk) - 1, response.status_code )
        response.raise_for_status()
        data = response.json()
        for record in data["content"]:
            result.append( [ record["externalId"],
                             record["businessPartnerType"],
                             record["sharingStateType"],
                             record["sharingErrorCode"],
                             record["sharingErrorMessage"],
                             record["bpn"],
                             record["sharingProcessStarted"],
                             record["taskId"] ] )

        total += len(data["content"])
        job.status.append( f"<li>Downloaded {total} records</li>" )

    # save the result for debugging purposes
    serialized = io.StringIO()
    writer = csv.writer( serialized, delimiter=";" )
    writer.writerows( result )

    with open( os.path.join( common.UPLOAD_FOLDER, job.name + "_result.csv" ), "w", encoding="utf-8-sig", newline="" ) as fh:
        fh.write( serialized.getvalue() )

    job.result = serialized.getvalue().encode("utf-8-sig")

    job.status.append( f'<li><a href="/result/{job.uuid}">Download CSV here</a></li>' )


def download_all( job: Job, what: str ) -> None:
    """Download all data from the input or the output stage.

    `what` must be "input" or "output", depending on the stage that shall be downloaded.

    Should not be called directly, but via run_job()"""

    job.status.append( f"<li>Downloading all data from the {what} stage...</li>" )

    access_token = _get_access_token()

    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    result = []

    total = 0
    page = -1
    while True:
        page += 1

        params = {
            "page": page,
            "size": CHUNK_SIZE
        }
        body = []

        response = requests.post( BASE_URL + f"{what}/business-partners/search", headers=headers, params=params, verify=common.VERIFY_SSL, data=body, timeout=30 )
        response.raise_for_status()
        data = response.json()
        count = len( data["content"] )
        logger.info( "chunk [%d, %d]: Status %d", total, total + count - 1, response.status_code )
        if count == 0:
            break

        for record in data["content"]:
            result.append( record )

        total += count
        job.status.append( f"<li>Downloaded {total} records</li>" )

        if total > 1000000:
            break       # something is wrong

    # save the result for debugging purposes
    with open( os.path.join( common.UPLOAD_FOLDER, job.name + ".json" ), "w", encoding="utf-8" ) as fh:
        json.dump( result, fh, indent=4, ensure_ascii=False )

    # convert to csv
    csv_lines, csv_header = convert_json.convert( result )
    csv_data = io.StringIO()
    dw = csv.DictWriter( csv_data, csv_header, delimiter=";", lineterminator="\n" )
    dw.writeheader()
    dw.writerows( csv_lines )

    # save this too for debugging purposes
    with open( os.path.join( common.UPLOAD_FOLDER, job.name + ".csv" ), "w", encoding="utf-8-sig", newline="" ) as fh:
        fh.write( csv_data.getvalue() )

    job.result = csv_data.getvalue().encode("utf-8-sig")

    job.status.append( f'<li><a href="/result/{job.uuid}">Download CSV here</a></li>' )


def _get_access_token():
    """Get an access token for the API"""

    # Encode the client ID and client secret
    try:
        authorization = base64.b64encode(bytes(CREDENTIALS["client_id"] + ":" + CREDENTIALS["client_secret"], "ISO-8859-1")).decode("ascii")

        headers = {
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = {
            "grant_type": "client_credentials"
        }

        response = requests.post(AUTH_URL, data=body, headers=headers, verify=common.VERIFY_SSL, timeout=30 )
        response.raise_for_status()
        response = json.loads(response.text)

        return response["access_token"]
    except Exception as ex:
        logger.error( "Error getting access token: %s", ex )
        raise Exception( "Error getting access token" ) from ex


def _get_reader( data: bytes ) -> tuple[bytes, str]:
    """Prepare the CSV data for processing and return a CSV reader object"""

    # remove utf-8 BOM if present
    if data.startswith( b"\xef\xbb\xbf" ):
        data = data[3:]

    # check field separator character
    firstline = data.split( b"\n", 1 )[0]
    if b";" in firstline:
        delimiter = ";"
    elif b"," in firstline:
        delimiter = ","
    elif b"\t" in firstline:
        delimiter = "\t"
    else:
        raise csv_tools.CSVException( "Field separator not found" )

    return csv.reader( io.StringIO( data.decode("utf-8")), delimiter=delimiter, strict=True )
