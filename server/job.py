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

import logging
import time

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

CLEANUP_TIMEOUT = 60 * 60 * 24              # remove jobs after 24 hours

class Job:
    """Contains the status of a conversion/upload job"""
    def __init__( self, uuid: str, name: str, timestamp: str ):
        self.uuid = uuid
        self.name = name
        self.timestamp = timestamp

        # This contains the HTML that is sent to the client
        self.status: list[str] = []

        self.done = False
        self.cleanup = time.time() + CLEANUP_TIMEOUT

        # If set, the user can download this as a file
        self.result: bytes|None = None
