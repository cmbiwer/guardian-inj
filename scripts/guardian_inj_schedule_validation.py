#! /usr/bin/env python

import argparse
import logging
import injtools
import sys

"""
Validates the guardian INJ schedule.

2016 - Christopher M. Biwer
"""

def waveform_end_time(hwinj, sample_rate):
    return hwinj.schedule_time + float(hwinj.waveform_length) / sample_rate

parser = argparse.ArgumentParser()
parser.add_argument("--ifos", nargs="+",
                    help="IFOs to check, eg. H1 and L1.")
parser.add_argument("--schedule", type=str, 
                    help="Path to the schedule file.")
parser.add_argument("--min-cadence", type=int,
                    help="Minimum amount of time between the start \
                         and end of two adjacent injections.")
parser.add_argument("--sample-rate", type=int, default=16384,
                    help="Sample rate of waveform file and injection channel.")
opts = parser.parse_args()

# setup log
logging.basicConfig(format="%(asctime)s : %(levelname)s : %(message)s", level=logging.DEBUG)

# read schedule
logging.info("Reading schedule file: %s", opts.schedule)
hwinj_list = injtools.read_schedule(opts.schedule)

# loop over HardwareInjection
logging.info("Reading waveform and meta-data files")
for hwinj in hwinj_list:

    # loop over IFO
    for ifo in opts.ifos:

        # create a dict for formatting; we allow users to use the {ifo}
        # substring substition in the waveform_path column
        format_dict = {
            "ifo" : ifo,
        }

        # check all waveform files are readable
        waveform_path = hwinj.waveform_path.format(**format_dict)
        waveform = injtools.read_waveform(hwinj.waveform_path)

        # add a length of waveform attribute
        if hasattr(hwinj, "waveform_length"):
            if hwinj.waveform_length != len(waveform):
                logging.info("Waveform file for different IFOs have different lengths: %s", hwinj)
        else:
            hwinj.waveform_length = len(waveform)

        # read meta-data file
        if hwinj.metadata_path != "None":
            file_contents = inj_io.read_metadata(hwinj.metadata_path,
                                                 hwinj.waveform_start_time,
                                                 hwinj.schedule_time)

# check that no two injections are within X seconds of each other
logging.info("Checking cadence of scheduled injections")
hwinj_list = sorted(hwinj_list, key=lambda hwinj: hwinj.schedule_time)
for hwinj_1, hwinj_2 in zip(hwinj_list, hwinj_list[1:]):

    # check schedule start times
    dt = hwinj_2.schedule_time - hwinj_1.schedule_time
    if dt > 0 and dt < opts.min_cadence:
        logging.error("Two injections start times are scheduled %f seconds apart: %s and %s", dt, str(hwinj_2), str(hwinj_1))
        sys.exit()

    # check length of time from the end to the start of the next injection
    dt = hwinj_2.schedule_time - waveform_end_time(hwinj_1, opts.sample_rate)
    if dt > 0 and abs(dt) < opts.min_cadence:
        logging.warn("Two injections are scheduled close together with only %f seconds from the end of the first injection to the start of the next injection: %s and %s", dt, str(hwinj_2), str(hwinj_1))

# exit
logging.info("Finished and schedule is valid")
