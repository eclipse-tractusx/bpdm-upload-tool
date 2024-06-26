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

import csv_tools
from csv_tools import Column, Empty

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

def get_external_ids( reader: csv.reader ) -> list[str]:
    """Get the external IDs from a CSV file"""
    header = [
        Column( "externalId",                                           str,                Empty.NotOK ),
    ]

    data = csv_tools.read_header_csv_with_reader( reader, header=header, make_objects=False, ignore_unknown_columns=True, identifier_column="externalId" )[0]

    return [ row[0] for row in data ]
