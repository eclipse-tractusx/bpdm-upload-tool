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

import os.path
import logging
import uuid
import threading

from flask import Flask, redirect, request, flash, render_template, url_for, Response
from werkzeug.utils import secure_filename

import common
import string_tools
import logging_tools
import processing
from job import Job

class AppException(Exception):
    """Default Exception for CSV errors"""

logging_tools.configure()
logger = logging.getLogger(__name__)       # pylint: disable=invalid-name

for directory in [ common.UPLOAD_FOLDER, common.STATIC_FOLDER, common.TEMPLATES_FOLDER ]:
    if not os.path.isdir( directory ):
        raise AppException( f"Directory {directory} does not exist" )

app = Flask(__name__, static_url_path='/static', static_folder=common.STATIC_FOLDER)

# Allow uploads up to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = uuid.uuid4().hex       # used for signing session cookies

# TODO: implement cleanup of old jobs
jobs: dict[str,Job] = {}
processing.init()

@app.route("/")
def start():
    """Currently only redirect to file selection page"""
    return render_template("start.jinja")


@app.route("/select-upload")
def select_upload():
    """Show file selection"""
    return render_template("select.jinja", destination="/upload", prompt="Select a file to upload", description="The file must be a CSV file in the specified format")


@app.route("/select-sharing-state")
def select_sharing_state():
    """Show file selection"""
    return render_template("select.jinja", destination="/sharing-state", prompt="Select a file for checking the sharing state",
                           description="Determine the sharing state for external IDs.\n"
                           "The provided CSV file must contain at least one column with the name `externalId`.\n"
                           "Other columns are ignored" )


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload a CSV file"""
    # check if the post request has the file part
    try:
        data, insecure_filename = get_file_data()
    except AppException as ex:
        flash( str(ex) )
        return redirect(url_for(select_upload.__name__))

    job = make_job( insecure_filename, data, "upload" )

    # Start a thread to process the file
    thread = threading.Thread( target=processing.run_job, args=(job, data, processing.upload_file) )
    thread.start()

    return redirect(url_for( process.__name__, job_uuid=job.uuid ))


@app.route('/sharing-state', methods=['POST'])
def sharing_state():
    """Determine the sharing state for external IDs.
    The provided CSV file must contain at least one column with the name `externalId`.
    Other columns are ignored
    """
    # check if the post request has the file part
    try:
        data, insecure_filename = get_file_data()
    except AppException as ex:
        flash( str(ex) )
        return redirect(url_for(select_sharing_state.__name__))

    job = make_job( insecure_filename, data, "sharing-state" )

    # Start a thread to process the file
    thread = threading.Thread( target=processing.run_job, args=(job, data, processing.get_sharing_state) )
    thread.start()

    return redirect(url_for( process.__name__, job_uuid=job.uuid ))


@app.route("/download-all-input")
def download_all_input():
    """Download all business partners in input"""
    job = make_job( None, None, "download-all-input" )

    thread = threading.Thread( target=processing.run_job, args=(job, "input", processing.download_all) )
    thread.start()

    return redirect(url_for( process.__name__, job_uuid=job.uuid ))


@app.route("/download-all-output")
def download_all_output():
    """Download all business partners in output"""
    job = make_job( None, None, "download-all-output" )

    thread = threading.Thread( target=processing.run_job, args=(job, "output", processing.download_all) )
    thread.start()

    return redirect(url_for( process.__name__, job_uuid=job.uuid ))


@app.route("/processing/<job_uuid>")
def process( job_uuid ):
    """Show results of the analysis"""
    return render_template("processing.jinja", job_uuid=job_uuid)


@app.route("/progress/<job_uuid>")
def progress( job_uuid ):
    """Return progress of the analysis. This is polled by Javascript on the client side."""
    if job_uuid not in jobs:
        return { "progress": "<li>Job not found</li>", "done": True }
    return { "progress": "".join( jobs[job_uuid].status ),
             "done": jobs[job_uuid].done,
             "result": None if jobs[job_uuid].result is None or not jobs[job_uuid].done else "/result/" + jobs[job_uuid].name
           }


@app.route("/result/<job_uuid>")
def result( job_uuid ):
    """Return the result of a job"""
    if job_uuid not in jobs:
        flash( "Job not found" )
        return redirect(url_for( start.__name__ ))
    job = jobs[job_uuid]

    if job.result is None:
        flash( "No result available" )
        return redirect(url_for( start.__name__ ))

    return Response( job.result, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={job.name}.csv"} )


def get_file_data():
    """Gets the uploaded file"""
    if 'file' not in request.files:
        raise AppException( "No file part" )
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        raise AppException( "No selected file" )
    return file.stream.read(), file.filename


def make_job( insecure_filename: str|None, data: bytes|None, kind: str ):
    """Create a job from the uploaded file"""

    # create a unique job id which the client will use to poll for results
    job_uuid = str( uuid.uuid4())
    timestamp = string_tools.date_time_for_filename()

    if insecure_filename is not None:
        filename = f"{timestamp}_{kind}_{secure_filename(insecure_filename)}_{job_uuid}"
    else:
        filename = f"{timestamp}_{kind}_{job_uuid}"

    # Save the file (for debugging)
    if data is not None and len( data ) > 0:
        with open( os.path.join( common.UPLOAD_FOLDER, filename ), "wb" ) as f:
            f.write( data )

    # determine a job name, which sould be the filename without the extension (if the extension is `csv`)
    job_name, ext = os.path.splitext( filename )
    if ext.lower() != ".csv":
        job_name = filename

    job = Job( job_uuid, job_name, timestamp )
    jobs[job_uuid] = job

    return job
