# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ IO guardian module

This module provides functions for reading input files.
"""

import numpy
import os.path
import tempfile
from glue.ligolw import ilwd, ligolw, lsctables, table, utils
from inj_types import HardwareInjection

@lsctables.use_in
class ContentHandler(ligolw.LIGOLWContentHandler):
    """ Setup content handler for LIGOLW XML files.
    """
    pass

    @property
    def waveform_start_time(self):
        """ Returns the GPS start time of the waveform. This assumes that
        the waveform file has the following format:

            IFO-TAG-GPS_START_TIME-DURATION.EXT

        Where IFO is the observatory, TAG is an arbitrary string that does not
        contain "-", GPS_START_TIME is the start time of the waveform file,
        DURATION is the length in seconds of the waveform file, and EXT is
        an arbitrary file extension.

        Returns
        ----------
        waveform_start_time: float
            Start time of the waveform file.
        """

        # get waveform file name
        filename = os.path.basename(self.waveform_path)

        # parse filename and get start time of waveform file
        waveform_start_time = filename.split("-")[-2]

        return float(waveform_start_time)

def read_schedule(schedule_path):
    """ Parses schedule file. Schedule file should be a space-delimited file
    with the following ordered columns: GPS start time, INJ state, observing
    mode, scale factor, path to the waveform file, and path to a meta-data
    file.

    The INJ state should be one of the INJ guardian module's states.

    The observing mode column should be 1 or 0. If there is a 1 the injection
    will be performed in observation mode and if there is a 0 the injection
    will be performed in commissioning mode.

    The scale factor should be a float. This is the overall factor a time
    series will be multiplied by before it is injected.

    If there is no meta-data file, then use None for this column.

    Since each detector will have different time series to inject, we allow the
    user to use the {ifo} substring in the waveform_path column. So that the
    substring {ifo} is replace with the value of ezca["ifo"].

    Parameters
    ----------
    schedule_path: str
        Path to the schedule file.

    Returns
    ----------
    inj_list: list
        A list where each element is an HardwareInjection instance.
    """

    # initialize empty list to store HardwareInjection
    hwinj_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert("now").gps()

    # read lines of schedule file
    fp = open(schedule_path, "rb")
    lines = fp.readlines()
    fp.close()

    # create a dict for formatting; we allow users to use the {ifo}
    # substring substition in the waveform_path column
    format_dict = {
        "ifo" : ezca["ifo"]
    }

    # loop over lines in schedule file
    for line in lines:

        # get line in schedule as a list of strings
        # assumes its a space-delimited line
        data = line.split()

        # parse line elements into variables
        i = 0
        schedule_time = float(data[i]); i += 1
        schedule_state = data[i]; i += 1
        observation_mode = int(data[i]); i+= 1
        scale_factor = float(data[i]); i += 1
        waveform_path = data[i].format(**format_dict); i += 1
        metadata_path = data[i]; i += 1

        # add a new HardwareInjection to list if its in the future
        if schedule_time - current_gps_time > 0:
            hwinj = HardwareInjection(schedule_time, schedule_state,
                                      observation_mode, scale_factor,
                                      waveform_path, metadata_path)
            hwinj_list.append(hwinj)

    return hwinj_list

def read_waveform(waveform_path, ftype="ascii"):
    """ Reads a waveform file. Only single-column ASCII files are
    supported for reading.

    Parameters
    ----------
    waveform_path: str
        Path to the waveform file.
    ftype: str
        Selects what method to use. Currently must be a string set to "ascii".

    Retuns
    ----------
    waveform: numpy.array
        Returns the time series as a numpy array.
    """

    # single-coulmn ASCII file reading
    if ftype == "ascii":

        # read single-column ASCII file with time series
        waveform = numpy.loadtxt(waveform_path)

    return waveform

def read_metadata(metadata_path, waveform_start_time, schedule_time=0.0,
                  ftype="sim_inspiral"):
    """ Reads a file that contains meta-data about the waveform file.

    Only XML files with a single row of a sim_inspiral table are
    supported. GraceDB only supports uploading SimInspiral files.

    Parameters
    ----------
    metadata_path: str
        Path to the metadata file.
    waveform_start_time: float
        GPS start time of the waveform file for when it was generated.
    schedule_time: float
        GPS time injection is scheduled to start.
    ftype: str
        Selects what method to use. Currently must be a string set
        to "sim_inspiral".

    Retuns
    ----------
    file_contents: str
        Returns a string that contains a XML file with a sim_inspiral table.
    """

    # sim_inspiral XML file case
    if ftype == "sim_inspiral":

        # read XML file
        try:
            xmldoc = utils.load_filename(metadata_path,
                                         contenthandler=ContentHandler)

        # if cannot read the XML file then log error and return
        # an empty sim_inspiral XML file as a string
        except IOError as e:
            #log("Error: "+e)
            file_contents = create_empty_sim_inspiral_xml(schedule_time)
            return file_contents

        # get first sim_inspiral row
        sim_table = table.get_table(xmldoc,
                                    lsctables.SimInspiralTable.tableName)
        if len(sim_table) == 1:
            sim = sim_table[0]

        # if more than one sim_inspiral row then log message, do not
        # make any assumptions about what the user is trying to do, and
        # return an empty sim_inspiral XML file as a string
        else:
            log("sim_inspiral table has more than one row, no meta-data read")
            file_contents = create_empty_sim_inspiral_xml(schedule_time)
            return file_contents

        # keep original geocentric end time to use for RA correction
        orig_end_time = sim.geocent_end_time

        # get corrected geocentric end time
        if type(sim.geocent_end_time) == int:
            dt = sim.geocent_end_time - waveform_start_time
            sim.geocent_end_time = schedule_time + dt

            # get corrected RA
            if type(sim.longitude) == float:
                sidereal_seconds = 86164.09054
                sim.longitude = ( sim.longitude + (2*numpy.pi/sidereal_seconds) * ( (sim.geocent_end_time-orig_end_time) % sidereal_seconds ) ) % (2*numpy.pi)

        # get corrected H1 end time
        if type(sim.h_end_time) == int:
            dt = sim.h_end_time - waveform_start_time
            sim.h_end_time = schedule_time + dt

        # get corrected L1 end time
        if type(sim.l_end_time) == int:
            dt = sim.l_end_time - waveform_start_time
            sim.l_end_time = schedule_time + dt

        # get XML content as a str
        fp = tempfile.NamedTemporaryFile()
        xmldoc.write(fp)
        fp.seek(0)
        file_contents = fp.read()
        fp.close()

    return file_contents

def create_empty_sim_inspiral_xml(geocent_end_time=0.0):
    """ Creates a string of a LIGOLW XML file with an empty sim_inspiral table.

    Parameters
    ----------
    geocent_end_time: float
        The geocentric end time to add to row in sim_inspiral table.

    Retuns
    ----------
    file_contents: str
        A string that contains a LIGOLW XML file with an empty
        sim_inspiral table.
    """

    # create a new sim_inspiral table
    cols = lsctables.SimInspiralTable.validcolumns.keys()
    sim_table = lsctables.New(lsctables.SimInspiralTable, cols)

    # create new LIGOLW XML document and add the new sim_inspiral table
    xmldoc = ligolw.Document()
    xmldoc.appendChild(ligolw.LIGO_LW())
    xmldoc.childNodes[0].appendChild(sim_table)

    # add a row with the geocentric end time column filled
    sim = create_empty_sim_inspiral_row()
    sim.geocent_end_time = int(geocent_end_time)
    sim.geocent_end_time_ns = int(geocent_end_time % 1 * 1e9)
    sim_table.append(sim)

    # get XML content as a str
    fp = tempfile.NamedTemporaryFile()
    xmldoc.write(fp)
    fp.seek(0)
    file_contents = fp.read()
    fp.close()

    return file_contents

def create_empty_sim_inspiral_row():
    """ Create an empty sim_inspiral or sngl_inspiral row where the columns
    have default values of None for a float.

    Retuns
    ----------
    row: SimInspiral
        An empty sim_inspiral row.
    """

    # create sim_inspiral row
    row = lsctables.SimInspiral()
    cols = lsctables.SimInspiralTable.validcolumns

    # populate columns with default values
    for entry in cols.keys():
        if cols[entry] in ['real_4','real_8']:
            setattr(row, entry, None)
        elif cols[entry] == 'int_4s':
            setattr(row, entry, None)
        elif cols[entry] == 'lstring':
            setattr(row, entry, "")
        elif entry == 'process_id':
            row.process_id = "process:process_id:0"
        elif entry == 'simulation_id':
            row.simulation_id = "sim_inspiral:simulation_id:0"

    return row


