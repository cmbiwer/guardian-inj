#! /usr/bin/env python

from inj_types import HardwareInjection
from inj_upload import gracedb_upload_injection, gracedb_upload_message

def log(message):
    """ A replacement function for the guardian log.
    """
    print message

# set some values for attributes
schedule_time = 32.0
schedule_state = "CBC"
observation_mode = 0
scale_factor = 1.0
waveform_path = "H1-TEST-0-0.txt"
metadata_path = "H1-TEST-0-0.xml"

# create a new HardwareInjection
hwinj = HardwareInjection(schedule_time, schedule_state, observation_mode,
                          scale_factor, waveform_path, metadata_path)

##### test 1
print "performing test 1"

# upload new test entry to GraceDB
gracedb_id = gracedb_upload_injection(hwinj, ["H1"], group="Test")

# append message to test entry
message = "This is a test. There should be no injection in the data."
gracedb_upload_message(gracedb_id, message)

##### test 2
print "performing test 2"

# test case where no metadata_path
hwinj.schedule_state = "Burst"
hwinj.metadata_path = "None"

# upload new test entry to GraceDB
gracedb_id = gracedb_upload_injection(hwinj, ["H1"], group="Test")

# append message to test entry
message = "This is a test. There should be no injection in the data."
gracedb_upload_message(gracedb_id, message)




