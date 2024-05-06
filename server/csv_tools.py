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
import re
import csv
import types
import datetime
import inspect
import logging
import logging.handlers
from pprint import pprint, pformat
from typing import Any, Union, Callable, Sequence, Iterable   # use `list` only for return types and prefer Sequence or Iterable for parameters
from enum import Enum

import string_tools

logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

re_invalid_object_attribute_chars = re.compile( r"[^a-zA-Z0-9_]+" )

class CSVException(Exception):
    """Default Exception for CSV errors"""

class Empty:
    """What to do with empty columns?"""
    NotOK = 0
    ToNone = 1
    OK = 2                  # only allowed for strings

class SpaceHandling:
    """What to do with spaces in strings?"""
    Keep = 0            # don't change anything
    Strip = 1           # strip spaces from the beginning and end of the string
    Collapse = 2        # strip spaces from the beginning and end of the string and collapse multiple spaces in the middle to one space


class Column:
    """Represents a column in the csv file

    Parameters
    ----------
    column_name : str
        Name of the column in the csv file
    column_type : type
        Type of the column. Can be str, int, float, datetime.datetime, an enum or a set of strings.
        If it is a set of strings, then the column must be a string and the value must be one of the strings in the set.
    empty : Union[Empty,str]
        What to do with empty columns?
        - NotOk: An empty column is an error
        - ToNone: An empty column is converted to None
        - OK: An empty column is OK. This is only allowed for string columns.
        - A string: An empty column is converted to this string (i.e. this is the default value)
    optional : bool
        The column may be missing in the csv file
    destination_name : str
        Name of the attribute in the destination object. If this is None, the column_name is used.
    """
    def __init__(self, column_name: str, column_type: type, empty: Union[Empty,str], *, optional: bool = False, destination_name: str|None = None ) -> None:
        self.column_name: str           = column_name
        self.column_type: type          = column_type
        self.empty: Union[Empty,str]    = empty
        self.optional: bool             = optional
        self.destination_name: str      = destination_name if destination_name is not None else make_attribute_name( column_name )
        self.destination_name_provided: bool = destination_name is not None

    def __repr__(self) -> str:
        return f"Column( {self.column_name} )"

    def column_name_for_array_object( self, prefixlen: int ) -> str:
        """Convert a column name to a suitable attribute name for an array object"""
        if self.destination_name_provided:
            return self.destination_name
        else:
            return make_attribute_name( self.column_name[prefixlen:] )


def make_attribute_name( name: str ) -> str:
    """Convert a name to a suitable attribute name"""
    result = re_invalid_object_attribute_chars.sub( "_", name )
    if result[0].isdigit():
        result = "_" + result
    return result


class ArrayGroup:
    """Represents a group of columns in the csv file that belong together

    Parameters
    ----------
    name : str
        Name of the group. An attribute with this name will be created in the destination object.
        It will be a list.
    prefix : str
        If this is None, the csv must also contain a column called `name`.
        The result will be a list of objects with the attributes as specified in the header.
        If this is not None, there must be one or more columns with this prefix.
        An object will be created depending on the value of make_type.
        The attributes of the object will be the columns with the prefix stripped.
    make_type : type
        if this is not None, for each record one object of this type will be created.
        Otherwise, a SimpleNamespace object will be created.
        This is only useful if prefix is not empty.
    """
    def __init__(self, name: str, prefix: Union[str,None] = None, make_type: Union[type,None] = None ) -> None:
        self.name: str = name
        self.prefix: Union[str,None] = prefix
        self.make_type: Union[type,None] = make_type

    def __repr__(self) -> str:
        return f"ArrayGroup( {self.name} )"


def read_header_csv( filename: str, *,
                     header: Sequence[Column],
                     make_objects: Union[bool,type] = True,
                     space_handling: SpaceHandling = SpaceHandling.Collapse,
                     ignore_unknown_columns: bool = False,
                     related_columns: list[set[Column]] = None,
                     identifier_column: str = None,
                     array_groups: list[ArrayGroup] = None,
                   ):
    """Reads an Excel-CSV-File with a header line and returns a list of records.

    Parameters
    ----------
    filename : str
        Eingabedatei
    header : list
        Liste mit gesuchten Spalten. Die Ausgabe enthält genau diese Spalten in der angegebenen Reihenfolge. Siehe unten.
    make_objects: bool or type
        If False, a list of lists is returned. The outer list are the records, the inner list contains the fields.
        If True, a list of objects is returned. Each object has the members as specified in the third element of `header`.
        If it is a type, then this type will be instantiated for each record and the members will be set.
    identifier_column: str
        Name of the identifier column. This is necessary if array groups are used.
    space_handling: SpaceHandling
        What to do with spaces in strings?
        TODO: might be useful to add this to the Column class for per-column settings.
    """

    with open( filename, "r", encoding="utf-8-sig", newline="" ) as fh:
        reader = csv.reader( fh, delimiter=";", strict=True )
        return read_header_csv_with_reader( reader,
                                            header=header,
                                            make_objects=make_objects,
                                            space_handling=space_handling,
                                            ignore_unknown_columns=ignore_unknown_columns,
                                            related_columns=related_columns,
                                            identifier_column=identifier_column,
                                            array_groups=array_groups,
                                          )


def read_header_csv_with_reader( reader: csv.reader, *,
                                 header: Sequence[Column],
                                 make_objects: Union[bool,type] = True,
                                 space_handling: SpaceHandling = SpaceHandling.Collapse,
                                 ignore_unknown_columns: bool = False,
                                 related_columns: list[set[Column]] = None,
                                 identifier_column: str = None,
                                 array_groups: list[ArrayGroup] = None,
                               ):
    """Reads an CSV-File with a header line and returns a list of records.
    """

    # make a dict with the column names as keys
    header_dict: dict[str,Column] = {}
    for c in header:
        header_dict[c.column_name] = c

    if related_columns is None:
        related_columns = []
    if array_groups is None:
        array_groups = []

    # First check the parameters if they are valid

    # 1. Check if all columns are unique
    tmp = set()
    for c in header:
        if c.column_name in tmp:
            raise CSVException( f"Duplicate column name '{c.column_name}' in header" )
        tmp.add( c.column_name )

    # 2. Make sure that Empty.OK is only used for string columns
    for c in header:
        if c.empty == Empty.OK and c.column_type != str:
            raise CSVException( f"Empty.OK is only allowed for string columns, but column '{c.column_name}' is of type {c.column_type}" )

    # 3. related_columns and identifier_column must be columns of the given header
    for rcs in related_columns:
        for c in rcs:
            if c not in header_dict:
                raise CSVException( f"Unknown related column '{c.column_name}' in csv file" )
    if identifier_column is not None and identifier_column not in header_dict:
        raise CSVException( f"Unknown identifier column '{identifier_column}' in csv file" )

    # create a mapping from array column name to array group object
    array_column_name_to_array_index: dict[str,int] = {}
    for ag_index, ag in enumerate( array_groups ):
        if ag.prefix is None:
            if ag.name not in header_dict:
                raise CSVException( f"Unknown array column '{ag.name}' in csv file" )
            array_column_name_to_array_index[ag.name] = ag_index
        else:
            matched = False
            for h in header:
                if h.column_name.startswith( ag.prefix ):
                    matched = True
                    array_column_name_to_array_index[h.column_name] = ag_index
            if not matched:
                raise CSVException( f"Unknown array column prefix '{ag.prefix}' in csv file" )

    # Read the header line and check the columns
    # Also create a few column mappings for later use
    headerline = next( reader )
    column_to_column_index: dict[Column,int] = {}
    column_index_to_column: dict[int,Column] = {}
    column_name_to_index: dict[str,int] = {}
    header_field_count = len( headerline )
    for col_nr, colname in enumerate( headerline ):
        colname_stripped = colname.strip()
        if colname_stripped in header_dict:
            column_to_column_index[header_dict[colname_stripped]] = col_nr
            column_index_to_column[col_nr] = header_dict[colname_stripped]
            column_name_to_index[colname_stripped] = col_nr
        else:
            if not ignore_unknown_columns:
                raise CSVException( f"Unknown column '{colname}' in csv file" )

    # check if all required columns are present
    for c in header:
        if not c.optional and c not in column_to_column_index:
            raise CSVException( f"Required column '{c.column_name}' is missing in csv file" )

    # get the index of the identifier column
    identifier_column_index = column_name_to_index[identifier_column] if identifier_column is not None else None

    line = 1
    # Now read the data and convert the columns
    result = []
    previous_identifier = None
    done_identifiers = set()            # all identifiers we already have seen
    for row in reader:
        line += 1
        if len( row ) != header_field_count:
            raise CSVException( f"Line {line}: Expected {header_field_count} columns, but found {len(row)}" )

        # first: space handling
        for col_nr, col in column_index_to_column.items():
            if space_handling == SpaceHandling.Strip:
                row[col_nr] = row[col_nr].strip()
            elif space_handling == SpaceHandling.Collapse:
                row[col_nr] = string_tools.collapse( row[col_nr] )

        # now check related columns. If one of them is not empty, all of them must not be empty
        for related in related_columns:
            empty_state = []
            for c in related:
                if c in column_to_column_index:
                    empty_state.append( row[column_to_column_index[c]] == "" )
                else:
                    empty_state.append( False )

            if any( empty_state ) and not all( empty_state ):
                raise CSVException( f"Line {line}: Either all or none of the related columns {', '.join(c for c in related)} must be set" )

        # Now we have to determine if we have a new record or if we have to add to the previous record.
        # The newdest variable will be True if we have a new record and false if we have a continuation line.
        newdest = True
        if identifier_column is not None:
            identifier = row[identifier_column_index]
            if identifier != previous_identifier:
                # new record
                if identifier in done_identifiers:
                    # all lines regarding an identifier must be consecutive
                    raise CSVException( f"Line {line}: Duplicate identifier '{identifier}' (all lines regarding an identifier must be consecutive.)" )
                previous_identifier = identifier
                done_identifiers.add( identifier )
            else:
                # add to previous record
                newdest = False

        if newdest:
            # create a new record
            if make_objects is False:           # "is" does not test for falsiness
                dest = []
                if len( array_groups ) > 0:
                    raise CSVException( f"Line {line}: array_columns is not supported if make_objects is False" )
            else:
                if make_objects is True:
                    dest = types.SimpleNamespace()
                else:
                    dest = make_objects()
                # create the array columns as empty lists
                for ag in array_groups:
                    setattr( dest, ag.name.replace( ".", "_" ), [] )

            result.append( dest )

            # for all array groups, create the objects already.
            # They will be added to the corrsponding lists, later if there has been data
            # The indexes here correspond to the indexes in array_groups
            array_group_data = []
            array_group_used = []
            for ag in array_groups:
                array_group_data.append( _create_array_object( ag ) )
                array_group_used.append( False )

            # just for safety, reset the current_array_...-variables. They are only used if we are on a continuation line.
            current_array_group = None
            current_array_object = None
            current_array_columns = None
        else:
            # we re-use the dest object from the previous iteration
            #
            # However, we have to check that only array columns are set and that exactly one of the arrays is set.
            have_data_for_array: set[ArrayGroup] = set()
            current_array_columns = set()
            for col_nr, col in column_index_to_column.items():
                value = row[col_nr]
                if value == "":
                    continue
                if col.column_name in array_column_name_to_array_index:
                    # it is an array column
                    have_data_for_array.add( array_groups[ array_column_name_to_array_index[col.column_name]] )
                    current_array_columns.add( col.column_name )
                else:
                    # normal column
                    if col_nr != identifier_column_index:
                        raise CSVException( f"Line {line}: Setting column '{col.column_name}' is not allowed in a continuation line" )

            if len( have_data_for_array ) > 1:
                raise CSVException( f"Line {line}: Only one of the array groups {', '.join(ag.name for ag in array_groups)} must be set" )
            if len( have_data_for_array ) == 0:
                raise CSVException( f"Line {line}: One of the array columns {', '.join(ag.name for ag in array_groups)} must be set" )

            # determine which array group it is
            current_array_group = have_data_for_array.pop()
            # We can already add the array object to the list, because we are processing exactly one array in a continuation line.
            current_array_object = _create_array_object( current_array_group )    # will be None if it is a single column
            if current_array_object is not None:
                getattr( dest, current_array_group.name ).append( current_array_object )

            # just for safety, reset the array_group_data and _used variables. They are only used if we are on a new record.
            array_group_data = None
            array_group_used = None

        # convert the columns
        for col_nr, col in column_index_to_column.items():
            value = row[col_nr]

            # If we are on a continuation line, we ignore all columns except the array columns.
            # We already checked that the others are all empty.
            if not newdest:
                if col.column_name not in current_array_columns:
                    continue

            # empty handling
            if value == "":
                if col.empty == Empty.NotOK:
                    raise CSVException( f"Line {line}: Column '{col.column_name}' is empty" )
                elif col.empty == Empty.ToNone:
                    value = None
                elif col.empty == Empty.OK:
                    pass
                else:
                    value = col.empty           # Default value
                is_empty = True
            else:
                is_empty = False

            # type conversion
            if value is not None:
                if col.column_type == str:
                    converted_value = value
                elif col.column_type == int:
                    try:
                        converted_value = int( value )
                    except ValueError as exc:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be an integer, but '{value}' is not" ) from exc
                elif col.column_type == float:
                    try:
                        converted_value = float( value.replace( ",", "." ))
                    except ValueError as exc:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be a float, but '{value}' is not" ) from exc
                elif col.column_type == datetime.datetime:
                    try:
                        converted_value = datetime.datetime.fromisoformat( value )
                    except Exception as exc:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be a datetime, but '{value}' is not" ) from exc
                elif inspect.isclass( col.column_type ) and issubclass( col.column_type, Enum ):
                    try:
                        converted_value = col.column_type[ value ]
                    except Exception as exc:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be one of '{', '.join([e.name for e in col.column_type])}', but it is '{value}'" ) from exc
                elif isinstance( col.column_type, set ):
                    if value not in col.column_type:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be one of {string_tools.ellipsize(', '.join( sorted( col.column_type )))}, but '{value}' is not" )
                    converted_value = value
                elif col.column_type == bool:
                    vl = value.lower()
                    if vl in [ "1", "true" ]:
                        converted_value = True
                    elif vl in [ "0", "false" ]:
                        converted_value = False
                    else:
                        raise CSVException( f"Line {line}: Column '{col.column_name}' should be '1/true' or '0/false', but it is '{value}'" )
                else:
                    raise CSVException( f"Line {line}: Internal error: Unknown column type '{col.column_type}'" )
            else:
                converted_value = None

            # store the value

            if newdest:
                # we are on a new record (not a continuation line)

                if col.column_name not in array_column_name_to_array_index:
                    # normal column
                    if make_objects:
                        setattr( dest, col.destination_name, converted_value )
                    else:
                        dest.append( converted_value )
                else:
                    # it is an array column

                    ag_index = array_column_name_to_array_index[col.column_name]
                    ag = array_groups[ag_index]
                    if not is_empty:
                        array_group_used[ag_index] = True

                    # is it a single value?
                    if ag.prefix is None:
                        # yes, it is a single value
                        array_group_data[ag_index] = converted_value
                    else:
                        setattr( array_group_data[ag_index], col.column_name_for_array_object( len(ag.prefix)), converted_value )
            else:
                # We are on a continuation line.
                # That means, we are processing exactly one array group.

                # is it a single value?
                if current_array_group.prefix is None:
                    # get the list containing the array values
                    l = getattr( dest, current_array_group.name )
                    l.append( converted_value )
                else:
                    # no, this array group is made of several columns.
                    # We already created an object and added it to the list.
                    # So we just have to set the value.
                    setattr( current_array_object, col.column_name_for_array_object(len(current_array_group.prefix)), converted_value )

        if newdest:
            # We are done with the new record
            # We now have to add all array objects to the corresponding lists.
            for ag_index, ag in enumerate( array_groups ):
                if not array_group_used[ag_index]:
                    continue
                l = getattr( dest, ag.name )
                l.append( array_group_data[ag_index] )

    return result, column_to_column_index


def _create_array_object( array_group: ArrayGroup ):
    """Creates an object for an array column"""

    if array_group.prefix is None:
        # don't create an object because it is a single column
        return None

    if array_group.make_type is None:
        result = types.SimpleNamespace()
    else:
        result = array_group.make_type()

    return result
