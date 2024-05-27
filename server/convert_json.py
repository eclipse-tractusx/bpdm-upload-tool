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
#
# pylint: disable=invalid-name
#
# Contains the code to convert JSON data from the API to CSV

import logging
import logging.handlers
from pprint import pprint, pformat
from typing import Any, Union, Callable, Sequence, Iterable   # use list only for return types and prefer Sequence or Iterable for parameters
from enum import Enum

import file_format
from csv_tools import Column

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

map_abbreviations = {
    "physicalPostalAddress": "physical",
    "alternativePostalAddress": "alternative",
}


def convert( data ) -> tuple[list[dict[str,str]], list[str]]:
    """Convert JSON data to CSV

    Returns
    -------
    tuple[list[dict[str,str]], list[str]]
    - The first element is a list of dictionaries. Each dictionary represents a line in the CSV.
    - The second element contains the names of the header fields.
    """

    # The csv headers represent the structure of the JSON data.
    # (More or less, for example nameParts is special)
    # So we can use that for parsing
    columns = file_format.get_csv_header()
    csv_header = [ column.column_name for column in columns ]

    column_name_to_column: dict[str,Column] = {}
    for column in columns:
        name = column.column_name
        column_name_to_column[name] = column

    # now for each record, recurse the structure and create a dictonary suitable for csv writing
    records = []
    unknown_keys = set()
    for input_record in data:
        dest: dict[str,str] = {}
        additional_lines = []
        external_id = input_record["externalId"]
        convert_record( input_record, external_id, column_name_to_column, "", dest, additional_lines, unknown_keys )
        records.append( dest )
        for line in additional_lines:
            records.append( line )

    for key in sorted( unknown_keys ):
        logger.warning( "Unknown key: %s", key )

    return records, csv_header


def convert_record( input_record: dict[str,Any], external_id: str, column_name_to_column: dict[str,Column], path: str, dest: dict[str,str], additional_lines: list[dict], unknown_keys: set[str] ):
    """Convert a single record to a dictionary suitable for csv writing

    Parameters
    ----------
    input_record : dict[str,Any]
        The JSON data to convert
    external_id : str
        The external ID of the record
    column_name_to_column : dict[str,Column]
        A dictionary that maps column names to column objects
    path : str
        The path to the current record. This is used for recursion.
    dest : dict[str,str]
        The dictionary to add the data to
    additional_lines : list[dict]
        A list where continuation lines can be added
    unknown_keys : set[str]
        A set to add unknown keys to
    """

    for key, value in input_record.items():
        full_key = path + map_abbreviations.get( key, key )

        # Do special handling
        if full_key == "nameParts":
            num = 0
            for part in value:
                num += 1
                dest[f"name{num}"] = convert_value( part )
            continue

        if full_key == "identifiers":
            if len( value ) > 0:
                convert_identifier( value[0], dest, external_id )
            for identifier in value[1:]:
                convert_identifier( identifier, additional_lines, external_id )
            continue

        if full_key == "states" or full_key.endswith( ".states" ):
            if len( value ) > 0:
                convert_states( value[0], dest, external_id, full_key )
            for state in value[1:]:
                convert_states( state, additional_lines, external_id, full_key )
            continue

        if full_key == "roles":
            if len( value ) > 0:
                convert_roles( value[0], dest, external_id )
            for role in value[1:]:
                convert_roles( role, additional_lines, external_id )
            continue

        if isinstance( value, dict ):
            convert_record( value, external_id, column_name_to_column, full_key + ".", dest, additional_lines, unknown_keys )
        elif isinstance( value, list ):
            # this should not happen
            dest[full_key] = "internal error 1"
        else:
            if full_key in column_name_to_column:
                dest[full_key] = convert_value( value )
            else:
                if value is not None:
                    unknown_keys.add( full_key )


def convert_identifier( identifier: dict[str,Any], dest: dict[str,str]|list, external_id: str ):
    """Convert an identifier to a dictionary suitable for csv writing

    dest can be a dictionary. In that case, the data is added to that dictionary.
    Or it can be a list. In that case, the data is added to the list as a dictionary.
    """

    if isinstance( dest, dict ):
        d = dest
    else:
        d = {}
        dest.append( d )

    d["identifiers.type"] = convert_value( identifier["type"] )
    d["identifiers.value"] = convert_value( identifier["value"] )
    d["identifiers.issuingBody"] = convert_value( identifier["issuingBody"] )
    d["externalId"] = external_id


def convert_states( state: dict[str,Any], dest: dict[str,str]|list, external_id: str, full_key: str ):
    """Convert a state to a dictionary suitable for csv writing

    dest can be a dictionary. In that case, the data is added to that dictionary.
    Or it can be a list. In that case, the data is added to the list as a dictionary.
    """

    if isinstance( dest, dict ):
        d = dest
    else:
        d = {}
        dest.append( d )

    d[full_key + ".validFrom"] = convert_value( state["validFrom"] )
    d[full_key + ".validTo"] = convert_value( state["validTo"] )
    d[full_key + ".type"] = convert_value( state["type"] )
    d["externalId"] = external_id


def convert_roles( role: dict[str,Any], dest: dict[str,str]|list, external_id: str ):
    """Convert a role to a dictionary suitable for csv writing

    dest can be a dictionary. In that case, the data is added to that dictionary.
    Or it can be a list. In that case, the data is added to the list as a dictionary.
    """

    if isinstance( dest, dict ):
        d = dest
    else:
        d = {}
        dest.append( d )

    d["roles"] = convert_value( role )
    d["externalId"] = external_id


def convert_value( value: Any ) -> str:
    """Convert a value to a string"""
    if value is None:
        return ""
    elif isinstance( value, dict ) or isinstance( value, list ):
        # This should not happen
        return "internal error 2"
    elif isinstance( value, float ):
        return str( value ).replace( ".", "," )
    elif isinstance( value, bool ):
        return "true" if value else "false"
    else:
        return str( value )
