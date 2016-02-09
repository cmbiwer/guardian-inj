# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ GraceDB module

This module provides functions for uploading hardware injections to GraceDB.

2016 - Christopher M. Biwer
"""

import tempfile
import ligo.gracedb.rest as gracedb_rest
from inj_io import read_metadata

def gracedb_upload_injection(hwinj, ifo_list,
                             pipeline="HardwareInjection", group="Test"):
    """ Uploads an event to GraceDB.

    Parameters
    ----------
    hwinj: HardwareInjection
        The HardwareInjection event to upload to GraceDB.
    ifo_list: list
        A list of the IFOs that should be appended to this event.
    pipeline: str
        The pipeline to tag for the GraceDB event.
    group: str
        The group to tag for the GraceDB event.

    Retuns
    ----------
    gracedb_id: str
        The GraceDB ID string for the HardwareInjection event that was
        uploaded.
    """

    # begin GraceDB API
    client = gracedb_rest.GraceDb()

    # read metadata file
    file_contents = read_metadata(hwinj.metadata_path,
                                  hwinj.waveform_start_time,
                                  hwinj.schedule_time)

    # make a comma-delimited string the IFOs
    ifo_str = ",".join(ifo_list)

    # upload event to GraceDB
    out = client.createEvent(group, pipeline, hwinj.metadata_path,
                             filecontents=file_contents, instrument=ifo_str,
                             source_channel="", destination_channel="")

    # get GraceDB ID
    gracedb_id = out.json()["graceid"]

    return gracedb_id

def gracedb_upload_message(gracedb_id, message, tagname="analyst comments"):
    """ Adds a message to the GraceDB entry.

    Parameters
    ----------
    gracedb_id: str
        The GraceDB ID of the entry to be appended.
    message: str
        The message to be appended to the GraceDB ID entry.
    tagname: str
        The name of the tag to use for GraceDB event.
    """

    # begin GraceDB API
    client = gracedb_rest.GraceDb()

    # append comment to GraceDB entry
    out = client.writeLog(gracedb_id, message, tagname=tagname)

