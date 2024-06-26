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
# Contains the code to convert a CSV file to JSON

import sys
import csv
import os.path
import datetime
import logging
import logging.handlers
from pprint import pprint, pformat
from typing import Any, Union, Callable, Sequence, Iterable   # use list only for return types and prefer Sequence or Iterable for parameters
from enum import Enum
import re
import json

import file_format
from file_format import StatesType, Roles, ClassificationsType, AddressType, DeliveryServiceType
import csv_tools
from csv_tools import ArrayGroup

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

class CSVIdentifiers:
    """Identifiers of a CSV-Record"""
    def __init__(self):
        self.type: str|None = None
        self.value: str|None = None
        self.issuingBody: str|None = None

class CSVStates:
    """States of a CSV-Record"""
    def __init__(self):
        self.validFrom: datetime.datetime = None
        self.validTo: datetime.datetime = None
        self.type: StatesType = None

class CSVRecord:
    """A CSV-Record"""
    def __init__(self):
        self.externalId: str|None = None
        self.name1: str|None = None
        self.name2: str|None = None
        self.name3: str|None = None
        self.name4: str|None = None
        self.name5: str|None = None
        self.name6: str|None = None
        self.name7: str|None = None
        self.name8: str|None = None
        self.name9: str|None = None
        self.identifiers: list[CSVIdentifiers] = []
        self.states: list[CSVStates] = []
        self.roles: list[Roles] = []
        self.isOwnCompanyData: bool = False
        self.legalEntity_legalEntityBpn: str|None = None
        self.legalEntity_legalName: str|None = None
        self.legalEntity_shortName: str|None = None
        self.legalEntity_legalForm: str|None = None
        self.legalEntity_states: list[CSVStates] = []
        self.site_siteBpn: str|None = None
        self.site_name: str|None = None
        self.site_states: list[CSVStates] = []
        self.address_addressBpn: str|None = None
        self.address_name: str|None = None
        self.address_addressType: AddressType|None = None
        self.address_physical_geographicCoordinates_longitude: float|None = None
        self.address_physical_geographicCoordinates_latitude: float|None = None
        self.address_physical_geographicCoordinates_altitude: float|None = None
        self.address_physical_country: str|None = None
        self.address_physical_administrativeAreaLevel1: str|None = None
        self.address_physical_administrativeAreaLevel2: str|None = None
        self.address_physical_administrativeAreaLevel3: str|None = None
        self.address_physical_postalCode: str|None = None
        self.address_physical_city: str|None = None
        self.address_physical_district: str|None = None
        self.address_physical_street_namePrefix: str|None = None
        self.address_physical_street_additionalNamePrefix: str|None = None
        self.address_physical_street_name: str|None = None
        self.address_physical_street_nameSuffix: str|None = None
        self.address_physical_street_additionalNameSuffix: str|None = None
        self.address_physical_street_houseNumber: str|None = None
        self.address_physical_street_houseNumberSupplement: str|None = None
        self.address_physical_street_milestone: str|None = None
        self.address_physical_street_direction: str|None = None
        self.address_physical_companyPostalCode: str|None = None
        self.address_physical_industrialZone: str|None = None
        self.address_physical_building: str|None = None
        self.address_physical_floor: str|None = None
        self.address_physical_door: str|None = None
        self.address_alternative_geographicCoordinates_longitude: float|None = None
        self.address_alternative_geographicCoordinates_latitude: float|None = None
        self.address_alternative_geographicCoordinates_altitude: float|None = None
        self.address_alternative_country: str|None = None
        self.address_alternative_administrativeAreaLevel1: str|None = None
        self.address_alternative_postalCode: str|None = None
        self.address_alternative_city: str|None = None
        self.address_alternative_deliveryServiceType: DeliveryServiceType = None
        self.address_alternative_deliveryServiceQualifier: str|None = None
        self.address_alternative_deliveryServiceNumber: str|None = None
        self.address_states: list[CSVStates] = []

    def to_dict(self) -> dict[str, Any]:
        """Converts the object to a dictionary suitable for submitting to the API"""

        nameParts = []
        for i in range( 1, 10 ):
            namePart = getattr( self, f"name{i}" )
            if namePart:
                nameParts.append( namePart )

        result = {
            "externalId": self.externalId,
            "nameParts": nameParts,
            "identifiers": [ { "type": i.type, "value": i.value, "issuingBody": i.issuingBody } for i in self.identifiers ],
            "states": [ { "validFrom": s.validFrom.isoformat(), "validTo": s.validTo.isoformat(), "type": s.type.name } for s in self.states ],
            "roles": [ r.name for r in self.roles ],
            "legalEntity": {
                "states": [ { "validFrom": s.validFrom.isoformat(), "validTo": s.validTo.isoformat(), "type": s.type.name } for s in self.legalEntity_states ]
            },
            "site": {
                "states": [ { "validFrom": s.validFrom.isoformat(), "validTo": s.validTo.isoformat(), "type": s.type.name } for s in self.site_states ]
            },
            "address": {
                "physicalPostalAddress": {},
                "alternativePostalAddress": {},
                "states": [ { "validFrom": s.validFrom.isoformat(), "validTo": s.validTo.isoformat(), "type": s.type.name } for s in self.address_states ]
            },
            "isOwnCompanyData": self.isOwnCompanyData
        }

        # address
        address = result["address"]
        set_field( address, "addressBpn", self.address_addressBpn )
        set_field( address, "name", self.address_name )
        set_field( address, "addressType", self.address_addressType )

        # site
        site = result["site"]
        set_field( site, "siteBpn", self.site_siteBpn )
        set_field( site, "name", self.site_name )

        # legalEntity
        le = result["legalEntity"]
        set_field( le, "legalEntityBpn", self.legalEntity_legalEntityBpn )
        set_field( le, "legalName", self.legalEntity_legalName )
        set_field( le, "shortName", self.legalEntity_shortName )
        set_field( le, "legalForm", self.legalEntity_legalForm )

        # physicalPostalAddress
        ppa = address["physicalPostalAddress"]
        if self.address_physical_geographicCoordinates_longitude or self.address_physical_geographicCoordinates_latitude or self.address_physical_geographicCoordinates_altitude:
            ppa["geographicCoordinates"] = {
                "longitude": self.address_physical_geographicCoordinates_longitude or 0,
                "latitude": self.address_physical_geographicCoordinates_latitude or 0,
                "altitude": self.address_physical_geographicCoordinates_altitude or 0
            }

        set_field( ppa, "country", self.address_physical_country )
        set_field( ppa, "administrativeAreaLevel1", self.address_physical_administrativeAreaLevel1 )
        set_field( ppa, "administrativeAreaLevel2", self.address_physical_administrativeAreaLevel2 )
        set_field( ppa, "administrativeAreaLevel3", self.address_physical_administrativeAreaLevel3 )
        set_field( ppa, "postalCode", self.address_physical_postalCode )
        set_field( ppa, "city", self.address_physical_city )
        set_field( ppa, "district", self.address_physical_district )
        set_field( ppa, "companyPostalCode", self.address_physical_companyPostalCode )
        set_field( ppa, "industrialZone", self.address_physical_industrialZone )
        set_field( ppa, "building", self.address_physical_building )
        set_field( ppa, "floor", self.address_physical_floor )
        set_field( ppa, "door", self.address_physical_door )

        # physicalPostalAddress/street
        street = {}             # only add later, if at least one entry is being added
        set_field( street, "namePrefix", self.address_physical_street_namePrefix )
        set_field( street, "additionalNamePrefix", self.address_physical_street_additionalNamePrefix )
        set_field( street, "name", self.address_physical_street_name )
        set_field( street, "nameSuffix", self.address_physical_street_nameSuffix )
        set_field( street, "additionalNameSuffix", self.address_physical_street_additionalNameSuffix )
        set_field( street, "houseNumber", self.address_physical_street_houseNumber )
        set_field( street, "houseNumberSupplement", self.address_physical_street_houseNumberSupplement )
        set_field( street, "milestone", self.address_physical_street_milestone )
        set_field( street, "direction", self.address_physical_street_direction )
        if len( street ) > 0:
            ppa["street"] = street

        # alternativePostalAddress
        apa = result["address"]["alternativePostalAddress"]
        if self.address_alternative_geographicCoordinates_longitude or self.address_alternative_geographicCoordinates_latitude or self.address_alternative_geographicCoordinates_altitude:
            apa["geographicCoordinates"] = {
                "longitude": self.address_alternative_geographicCoordinates_longitude or 0,
                "latitude": self.address_alternative_geographicCoordinates_latitude or 0,
                "altitude": self.address_alternative_geographicCoordinates_altitude or 0
            }

        set_field( apa, "country", self.address_alternative_country )
        set_field( apa, "administrativeAreaLevel1", self.address_alternative_administrativeAreaLevel1 )
        set_field( apa, "postalCode", self.address_alternative_postalCode )
        set_field( apa, "city", self.address_alternative_city )
        set_field( apa, "deliveryServiceType", self.address_alternative_deliveryServiceType )
        set_field( apa, "deliveryServiceQualifier", self.address_alternative_deliveryServiceQualifier )
        set_field( apa, "deliveryServiceNumber", self.address_alternative_deliveryServiceNumber )

        return result


def set_field( obj: dict[str, Any], field: str, value: Any ) -> None:
    """Sets a field in a dictionary if the value is not None or the empty String"""
    if value is not None and value != "":
        if isinstance( value, Enum ):
            obj[field] = value.name
        else:
            obj[field] = value


def convert( reader: csv.reader ) -> list[CSVRecord]:
    """Parst das CSV in eine Struktur, die an die API übergeben werden kann"""

    header = file_format.get_csv_header()

    # If one of the columns exists, all columns have to exist in the input file
    related_columns = [
        _get_all_columns( header, re.compile( r"^address.physical.geographicCoordinates.l" )),          # only longitude/latitude, not altitude
        _get_all_columns( header, re.compile( r"^address.alternative.geographicCoordinates.l" )),       # only longitude/latitude, not altitude
    ]

    # These columns can be repeated again on new lines for adding additional elements to the array
    array_groups = [
        ArrayGroup( "identifiers",          "identifiers.",         CSVIdentifiers ),
        ArrayGroup( "roles" ),
        ArrayGroup( "states",               "states.",              CSVStates ),
        ArrayGroup( "legalEntity_states",   "legalEntity.states.",  CSVStates ),
        ArrayGroup( "site_states",          "site.states.",         CSVStates ),
        ArrayGroup( "address_states",       "address.states.",      CSVStates ),
    ]

    data, _ = csv_tools.read_header_csv_with_reader( reader,
                                         header=header,
                                         make_objects=CSVRecord,
                                         related_columns=related_columns,
                                         identifier_column="externalId",
                                         array_groups=array_groups )

    return data


def _get_all_columns( header, regex ) -> set[str]:
    """Determine all column names that match the condition.

    Raises an exception if no columns are found"""

    result = set()
    for column in header:
        if regex.search( column.column_name ):
            result.add( column.column_name )

    if len( result ) == 0:
        raise Exception( f"No columns found for regex '{regex.pattern}'" )

    return result
