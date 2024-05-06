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

import sys
import os.path
import logging
import logging.handlers
from pprint import pprint, pformat
from typing import Any, Callable, Sequence, Iterable   # use `list` only for return types and prefer Sequence or Iterable for parameters
import re
import datetime
from enum import Enum

from csv_tools import Column, Empty, ArrayGroup

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

# taken from swagger
country_codes = set( [
    "UNDEFINED", "AC", "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AN",
    "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ", "BA",
    "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM",
    "BN", "BO", "BQ", "BR", "BS", "BT", "BU", "BV", "BW", "BY",
    "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL",
    "CM", "CN", "CO", "CP", "CR", "CS", "CU", "CV", "CW", "CX",
    "CY", "CZ", "DE", "DG", "DJ", "DK", "DM", "DO", "DZ", "EA",
    "EC", "EE", "EG", "EH", "ER", "ES", "ET", "EU", "EZ", "FI",
    "FJ", "FK", "FM", "FO", "FR", "FX", "GA", "GB", "GD", "GE",
    "GF", "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR",
    "GS", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT",
    "HU", "IC", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
    "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI",
    "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC",
    "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO",
    "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY",
    "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
    "NR", "NT", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH",
    "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA",
    "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE",
    "SF", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO",
    "SR", "SS", "ST", "SU", "SV", "SX", "SY", "SZ", "TA", "TC",
    "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO",
    "TP", "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UK", "UM",
    "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI", "VN", "VU",
    "WF", "WS", "XI", "XU", "XK", "YE", "YT", "YU", "ZA", "ZM",
    "ZR", "ZW" ] )

class StatesType(Enum):
    """Values for states.type"""
    INACTIVE = 0
    ACTIVE = 1

class ClassificationsType(Enum):
    """Values for classifications.type"""
    NACE = 0
    NAF = 1
    NAICS = 2
    SIC = 3

class Roles(Enum):
    """Values for roles"""
    SUPPLIER = 0
    CUSTOMER = 1
    ONE_TIME_SUPPLIER = 2
    ONE_TIME_CUSTOMER = 3

class AddressType(Enum):
    """Value for postalAddress.addresstype"""
    LegalAndSiteMainAddress = 0         # pylint: disable=invalid-name
    LegalAddress = 1                    # pylint: disable=invalid-name
    SiteMainAddress = 2                 # pylint: disable=invalid-name
    AdditionalAddress = 3               # pylint: disable=invalid-name

class DeliveryServiceType(Enum):
    """Value for address_alternative.deliveryServiceType"""
    PO_BOX = 0
    PRIVATE_BAG = 1
    BOITE_POSTALE = 2

def get_csv_header() -> list[Column]:
    """Gets the format of the CSV file"""

    header = [
        Column( "externalId",                                           str,                Empty.NotOK ),
        Column( "name1",                                                str,                Empty.NotOK ),
        Column( "name2",                                                str,                Empty.ToNone, optional=True ),
        Column( "name3",                                                str,                Empty.ToNone, optional=True ),
        Column( "name4",                                                str,                Empty.ToNone, optional=True ),
        Column( "name5",                                                str,                Empty.ToNone, optional=True ),
        Column( "name6",                                                str,                Empty.ToNone, optional=True ),
        Column( "name7",                                                str,                Empty.ToNone, optional=True ),
        Column( "name8",                                                str,                Empty.ToNone, optional=True ),
        Column( "name9",                                                str,                Empty.ToNone, optional=True ),
        Column( "identifiers.type",                                     str,                Empty.ToNone, optional=True ),
        Column( "identifiers.value",                                    str,                Empty.ToNone, optional=True ),
        Column( "identifiers.issuingBody",                              str,                Empty.ToNone, optional=True ),
        Column( "states.validFrom",                                     datetime.datetime,  Empty.ToNone, optional=True ),
        Column( "states.validTo",                                       datetime.datetime,  Empty.ToNone, optional=True ),
        Column( "states.type",                                          StatesType,         Empty.ToNone, optional=True ),
        Column( "roles",                                                Roles,              Empty.ToNone, optional=True ),
        Column( "legalEntity.legalEntityBpn",                           str,                Empty.ToNone, optional=True ),
        Column( "legalEntity.legalName",                                str,                Empty.ToNone, optional=True ),
        Column( "legalEntity.shortName",                                str,                Empty.ToNone, optional=True ),
        Column( "legalEntity.legalForm",                                str,                Empty.ToNone, optional=True ),
        Column( "legalEntity.classifications.type",                     ClassificationsType,Empty.ToNone, optional=True ),
        Column( "legalEntity.classifications.code",                     str,                Empty.ToNone, optional=True ),
        Column( "legalEntity.classifications.value",                    str,                Empty.ToNone, optional=True ),
        Column( "site.siteBpn",                                         str,                Empty.ToNone, optional=True ),
        Column( "site.name",                                            str,                Empty.ToNone, optional=True ),
        Column( "address.addressBpn",                                   str,                Empty.ToNone, optional=True ),
        Column( "address.name",                                         str,                Empty.ToNone, optional=True ),
        Column( "address.addressType",                                  AddressType,        Empty.ToNone, optional=True ),
        Column( "address.physical.geographicCoordinates.longitude",     float,              Empty.ToNone, optional=True ),
        Column( "address.physical.geographicCoordinates.latitude",      float,              Empty.ToNone, optional=True ),
        Column( "address.physical.geographicCoordinates.altitude",      float,              Empty.ToNone, optional=True ),
        Column( "address.physical.country",                             country_codes,      Empty.ToNone, optional=True ),
        Column( "address.physical.administrativeAreaLevel1",            str,                Empty.ToNone, optional=True ),
        Column( "address.physical.administrativeAreaLevel2",            str,                Empty.ToNone, optional=True ),
        Column( "address.physical.administrativeAreaLevel3",            str,                Empty.ToNone, optional=True ),
        Column( "address.physical.postalCode",                          str,                Empty.ToNone, optional=True ),
        Column( "address.physical.city",                                str,                Empty.ToNone, optional=True ),
        Column( "address.physical.district",                            str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.namePrefix",                   str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.additionalNamePrefix",         str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.name",                         str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.nameSuffix",                   str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.additionalNameSuffix",         str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.houseNumber",                  str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.houseNumberSupplement",        str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.milestone",                    str,                Empty.ToNone, optional=True ),
        Column( "address.physical.street.direction",                    str,                Empty.ToNone, optional=True ),
        Column( "address.physical.companyPostalCode",                   str,                Empty.ToNone, optional=True ),
        Column( "address.physical.industrialZone",                      str,                Empty.ToNone, optional=True ),
        Column( "address.physical.building",                            str,                Empty.ToNone, optional=True ),
        Column( "address.physical.floor",                               str,                Empty.ToNone, optional=True ),
        Column( "address.physical.door",                                str,                Empty.ToNone, optional=True ),
        Column( "address.alternative.geographicCoordinates.longitude",  float,              Empty.ToNone, optional=True ),
        Column( "address.alternative.geographicCoordinates.latitude",   float,              Empty.ToNone, optional=True ),
        Column( "address.alternative.geographicCoordinates.altitude",   float,              Empty.ToNone, optional=True ),
        Column( "address.alternative.country",                          country_codes,      Empty.ToNone, optional=True ),
        Column( "address.alternative.administrativeAreaLevel1",         str,                Empty.ToNone, optional=True ),
        Column( "address.alternative.postalCode",                       str,                Empty.ToNone, optional=True ),
        Column( "address.alternative.city",                             str,                Empty.ToNone, optional=True ),
        Column( "address.alternative.deliveryServiceType",              DeliveryServiceType,Empty.ToNone, optional=True ),
        Column( "address.alternative.deliveryServiceQualifier",         str,                Empty.ToNone, optional=True ),
        Column( "address.alternative.deliveryServiceNumber",            str,                Empty.ToNone, optional=True ),
        Column( "createdAt",                                            datetime.datetime,  Empty.ToNone, optional=True ),
        Column( "updatedAt",                                            datetime.datetime,  Empty.ToNone, optional=True ),
        Column( "isOwnCompanyData",                                     bool,               Empty.NotOK ),
    ]

    return header
