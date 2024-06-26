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
# pylint: disable=consider-using-f-string

import sys
import os.path
import datetime
import logging
import logging.handlers
from pprint import pprint, pformat
from typing import Any, Callable, Sequence, Iterable   # use `list` only for return types and prefer Sequence or Iterable for parameters

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

def collapse( s: str ) -> str:
    """collapse a string - remove spaces from the beginning and end of the string and collapse multiple spaces in the middle to one space"""
    return " ".join( s.split())


def ellipsize( s: str, max_length: int = 30 ) -> str:
    """ellipsize a string - if the string is longer than max_length, replace the middle with "..." to make it fit"""
    if len(s) > max_length:
        return s[:max_length//2] + "..." + s[-max_length//2:]
    else:
        return s


def date_time_for_filename( *, separator = "_" ):
    """Return a string with the current date and time in the format YYYY-MM-DD_HH:MM:SS"""
    now = datetime.datetime.now()
    return "{:04d}-{:02d}-{:02d}{}{:02d}.{:02d}.{:02d}".format( now.year, now.month, now.day, separator, now.hour, now.minute, now.second )
