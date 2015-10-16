# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ tools module

This defines how to read the schedule and determine if
injections are to be performed.
'''

from glue.ligolw import ligolw, lsctables
from gpstime import gpstime

# seconds before injection to call awgstream
awgstream_time = 300

# setup content handler for LIGOLW XML
@lsctables.use_in
class ContentHandler(ligolw.LIGOLWContentHandler):
    pass

class InjectionList(list):

    def __init__(self):
        self.imminient_injection = None

class Injection(object):
    ''' A class representing a single injection.
    '''

    def __init__(self, scheduled_time, injection_type,
                     scale_factor, path):

        self.scheduled_time = float(scheduled_time)
        self.injection_type = injection_type
        self.scale_factor = float(scale_factor)
        self.path = path

def validate_schedule():
    ''' Validate formatting of schedule file.
    '''
    pass

def read_schedule(path_schedule):
    ''' Parses schedule and returns rows.
    '''

    # initialize empty list to store injections
    injection_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # open schedule file and add the injections to the list
    with open(path_schedule, 'rb') as fp:
        lines = fp.readlines()
        for line in lines:
            scheduled_time, injection_type, scale_factor, path = line.split()
            injection = Injection(scheduled_time, injection_type, scale_factor, path)

            # add injection to list if its in the future
            if injection.scheduled_time-current_gps_time > 0:
                injection_list.append(injection)

    return injection_list

def check_injections_enabled():
    ''' Check that injections are enabled.
    '''

    # check if injections enabled
    tinj_enable = ezca.read('TINJ_ENABLE')
    print 'The value of %s is %f'%(ezca.prefix+'TINJ_ENABLE', tinj_enable)

    # check if electromagnetic alert
    exttrig_alert_time = ezca.read('EXTTRIG_ALERT_TIME')
    print 'The value of %s is %f'%(ezca.prefix+'EXTTRIG_ALERT_TIME', exttrig_alert_time)

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # if injections enabled and no electromangetic alert return True
    if tinj_enable and (current_gps_time - exttrig_alert_time > awgstream_time):
        return True

    # else return False
    else:
        return False

def check_injections_imminent(injection_list):
    ''' Check for an imminent injection.
    '''

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # find most imminent injection
    if len(injection_list):
        imminent_injection = min(injection_list, key=lambda x: x.scheduled_time-current_gps_time)
    else:
        return None

    # if most imminent injection is within time to call awgstream then return that injection
    if imminent_injection.scheduled_time-current_gps_time > awgstream_time:
        return imminent_injection
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

def external_call():
    ''' Make an external call on the command line.
    '''
    pass

