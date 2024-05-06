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
import html
import datetime
import os
import sys
import copy

def configure( file_handler: logging.StreamHandler = None, *, file_log_level = logging.DEBUG, console_log_level = logging.DEBUG, console_datefmt: str = None ):
    """
    Configure logging for the application

    A console handler will always be created.
    If a file handler is passed, it will be configured and added to the root logger.

    console_datefmt can be set to a string to add a date to the console output. e.g. "%Y-%m-%d %H:%M:%S" or "%H:%M:%S"
    """

    root_logger = logging.getLogger()
    root_logger.setLevel( logging.DEBUG )

    console_handler = logging.StreamHandler()
    if console_datefmt is not None:
        console_formatter = MyFormatter( fmt="%(asctime)s %(name)-16s %(message)s", datefmt=console_datefmt, add_level_char=True )
    else:
        console_formatter = MyFormatter( fmt="%(name)-16s %(message)s", add_level_char=True )
    console_handler.setFormatter( console_formatter )
    console_handler.setLevel( console_log_level )
    root_logger.addHandler( console_handler )

    if file_handler is not None:
        file_formatter = MyFormatter( "%(asctime)s %(name)-16s %(message)s", indent_following_lines = 43, add_level_char=True )
        file_handler.setFormatter( file_formatter )
        file_handler.setLevel( file_log_level )
        root_logger.addHandler( file_handler )


def map_level_to_short( levelno: int ):
    """Map a log level to a single character"""
    if levelno < logging.DEBUG:
        return "?"
    if levelno < logging.INFO:
        return " "
    if levelno < logging.WARNING:
        return "."
    if levelno < logging.ERROR:
        return ":"
    if levelno < logging.FATAL:
        return "!"
    return "X"


class MyFormatter( logging.Formatter ):
    """Indents all lines but the first one"""

    def __init__(self, fmt: str = None, datefmt: str = None, style = "%", validate: bool = True, *, indent_following_lines: int = None, add_level_char: bool = False ) -> None:
        super().__init__(fmt, datefmt, style, validate)
        if indent_following_lines is not None and indent_following_lines > 0:
            self.indent = "\n" + ( " " * indent_following_lines )
        else:
            self.indent = None
        self.add_level_char = add_level_char

    def format(self, record):
        text = super().format( record )
        if self.indent is not None:
            text = text.replace( "\n", self.indent )
        if self.add_level_char:
            return map_level_to_short( record.levelno ) + " " + text
        else:
            return text
