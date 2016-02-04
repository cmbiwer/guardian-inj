# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ GraceDB module

This module provides functions for uploading hardware injections to GraceDB.
"""

import tempfile
import ligo.gracedb.rest as gracedb_rest
from glue.ligolw import ligolw, lsctables, table, utils
from injtools import read_metadata

# URL to injection SVN that contains waveform files
injection_svn_url = "https://daqsvn.ligo-la.caltech.edu/svn/injection/hwinj/Details/"

def upload_gracedb_injection(hwinj, ifo,
                             pipeline="HardwareInjection", group="Test"):
    """ Uploads an event to GraceDB.

    Parameters
    ----------
    hwinj: HardwareInjection
        The HardwareInjection event to upload to GraceDB.

    Retuns
    ----------
    gracedb_id: str
        The GraceDB ID string for the HardwareInjection event that was
        uploaded.
    """

    # begin GraceDB API
    client = gracedb_rest.GraceDB()

    # read metadata file
    file_contents = read_metadata(hwinj.metadata_path)

    # make a comma-delimited string the IFOs
    ifo_str = ",".join(ifo_list)

    # upload event to GraceDB
    out = client.createEvent(group, pipeline, hwinj.metadata_path,
        filecontents=filecontents, insturment=ifo_str,
        source_channel="", destination_channel="")

    # get GraceDB ID
    gracedb_id = out.json()["graceid"]

    return gracedb_id

def upload_gracedb_message(gracedb_id, message):
    """ Uploads an event to GraceDB.

    Parameters
    ----------
    inj: Injection
        The Injection instance to upload to GraceDB.
    """

    # FIXME: hardcoded CBC waveforms for development
    # add URL to waveform and parameter files
    waveform_url = injection_svn_url + "/Inspiral/" + ifo + "/" + basename(inj.waveform_path)
    metadata_url = injection_svn_url + "/Inspiral/" + basename(inj.metadata_path)
    message  = ""
    message += "<a href="+waveform_url+">waveform file</a>"
    message += "<br>"
    message += "<a href="+metadata_url+">original XML parameter file</a>"
    out2 = client.writeLog(graceid, message, tagname="analyst comments")

