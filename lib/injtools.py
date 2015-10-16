# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ tools module

This defines how to read the schedule and determine if
injections are to be performed.
'''

##################################################
# IMPORTS
##################################################

import logging
from glue.ligolw import ligolw, lsctables
from gpstime import gpstime

##################################################
# VARIABLES
##################################################

# seconds before injection to call awgstream
awgstream_time = 300

# setup log
log = logging.getLogger('INJ')

##################################################
# CLASSES
##################################################

# setup content handler for LIGOLW XML
@lsctables.use_in
class ContentHandler(ligolw.LIGOLWContentHandler):
    pass

class InjectionList(list):

    def __init__(self):
        self.imminient_inj = None

class Injection(object):
    ''' A class representing a single injection.
    '''

    def __init__(self, scheduled_time, inj_type,
                     scale_factor, path):

        self.scheduled_time = float(scheduled_time)
        self.inj_type = inj_type
        self.scale_factor = float(scale_factor)
        self.path = path

##################################################
# FUNCTIONS
##################################################

def validate_schedule():
    ''' Validate formatting of schedule file.
    '''
    pass

def read_schedule(path_schedule):
    ''' Parses schedule and returns rows.
    '''

    # initialize empty list to store injections
    inj_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # open schedule file and add the injections to the list
    with open(path_schedule, 'rb') as fp:
        lines = fp.readlines()
        for line in lines:
            scheduled_time, inj_type, scale_factor, path = line.split()
            inj = Injection(scheduled_time, inj_type, scale_factor, path)

            # add injection to list if its in the future
            if inj.scheduled_time-current_gps_time > 0:
                inj_list.append(inj)

    return inj_list

def check_injections_enabled():
    ''' Check that injections are enabled.
    '''

    # check if injections enabled
    tinj_enable = ezca.read('TINJ_ENABLE')
    log.info('The value of %s is %f', ezca.prefix+'TINJ_ENABLE', tinj_enable)

    # check if electromagnetic alert
    exttrig_alert_time = ezca.read('EXTTRIG_ALERT_TIME')
    log.info('The value of %s is %f', ezca.prefix+'EXTTRIG_ALERT_TIME', exttrig_alert_time)

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # if injections enabled and no electromangetic alert return True
    if tinj_enable and (current_gps_time - exttrig_alert_time > awgstream_time):
        return True

    # else return False
    else:
        return False

def check_injections_imminent(inj_list):
    ''' Check for an imminent injection.
    '''

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # find most imminent injection
    if len(inj_list):
        imminent_inj = min(inj_list, key=lambda x: x.scheduled_time-current_gps_time)
    else:
        return None

    # if most imminent injection is within time to call awgstream then return that injection
    if imminent_inj.scheduled_time-current_gps_time > awgstream_time:
        return imminent_inj
    else:
        return None

def check_detector_enabled():
    ''' Check that the detector is in observation mode.
    '''
    pass

def check_filterbank_status():
    ''' Check that filterbank is ON.
    '''
    pass

def make_external_call():
    ''' Make an external call on the command line.
    '''
    pass

