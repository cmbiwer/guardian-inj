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
from gpstime import gpstime
from subprocess import Popen, PIPE

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

class Injection(object):
    ''' A class representing a single injection.
    '''

    def __init__(self, scheduled_time, inj_type,
                 scale_factor, waveform_path, metadata_path):
        self.scheduled_time = float(scheduled_time)
        self.inj_type = inj_type
        self.scale_factor = float(scale_factor)
        self.waveform_path = waveform_path
        self.metadata_path = metadata_path

##################################################
# FUNCTIONS
##################################################

def validate_schedule():
    ''' Validate formatting of schedule file.

    This function is not operational.
    '''
    pass

def read_schedule(schedule_path):
    ''' Parses schedule and returns rows.

    Parameters
    ----------
    schedule_path: str
        Path to the schedule file.

    Returns
    ----------
    inj_list: list
        A list where each element is an Injection instance.
    '''

    # initialize empty list to store injections
    inj_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # open schedule file and add the injections to the list
    with open(schedule_path, 'rb') as fp:
        lines = fp.readlines()
        for line in lines:
            scheduled_time, inj_type, scale_factor, waveform_path, metadata_path = line.split()
            inj = Injection(scheduled_time, inj_type, scale_factor, waveform_path, metadata_path)

            # add injection to list if its in the future
            if inj.scheduled_time-current_gps_time > 0:
                inj_list.append(inj)

    return inj_list

def check_injections_enabled():
    ''' Check that injections are enabled. This includes a few checks.

    First check the EPICs record if injections are enabledo.

    Then check if injections have been paused.

    Last check if there is a recent electromagnetic alert.

    Returns
    ----------
    bool
        Returns True if injections are enabled. Returns False if injections are
        not enabled.
    '''

    # check if injections enabled
    tinj_enable = ezca.read('TINJ_ENABLE')
    log.info('The value of %s is %f',
        ezca.prefix+'TINJ_ENABLE', tinj_enable)

    # check if injections paused
    tinj_enable = ezca.read('TINJ_ENABLE')
    log.info('The value of %s is %f',
        ezca.prefix+'TINJ_ENABLE', tinj_enable)

    # check if electromagnetic alert
    exttrig_alert_time = ezca.read('EXTTRIG_ALERT_TIME')
    log.info('The value of %s is %f',
        ezca.prefix+'EXTTRIG_ALERT_TIME', exttrig_alert_time)

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # if injections enabled and no electromangetic alert return True
    if tinj_enable and (current_gps_time-exttrig_alert_time > awgstream_time):
        return True

    # else return False
    else:
        return False

def check_injections_imminent(inj_list):
    ''' Check for an imminent injection.

    Parameters
    ----------
    inj_list: list
        A list of Injection instances.

    Retuns
    ----------
    imminent_inj: Injection
        An Injection instance is return if there is an imminent injection
        found.
    '''

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # find most imminent injection
    if len(inj_list):
        imminent_inj = min(inj_list, key=lambda x: x.scheduled_time-current_gps_time)
    else:
        return None

    # if most imminent injection is within time to call awgstream
    # then return that injection
    dt = imminent_inj.scheduled_time-current_gps_time
    if dt <= awgstream_time and dt > 0:
        return imminent_inj
    else:
        return None

def check_detector_enabled():
    ''' Check that the detector is in observation mode.

    Function is not operational.
    '''

    return True

def make_external_call(cmd_list, stdout=PIPE, stderr=PIPE, shell=False):
    ''' Make an external call on the command line.

    Parameters
    ----------
    cmd_list: list
        A list where the elements are the command line arguments.
    stdout: object
        Where to write stdout.
    stderr: object
        Where to write stderr.
    shell: boolean
        If True then execute external call through the shell.

    Retuns
    ----------
    process.returncode: int
        The exit code of the external call.
    '''

    # run command
    cmd_list = map(str, cmd_list)
    cmd_str = ' '.join(cmd_list)
    log.info('Making external call: %s', cmd_str)
    process = Popen(cmd_list, shell=shell,
                  stdout=stdout, stderr=stderr)

    # get standard output and standard error
    stdout, stderr = process.communicate()

    # if external call failed show stderr and stdout
    if process.returncode:
        log.debug('External call failed\n%s\n%s', stdout, stderr)
    else:
        log.info('External call successful')

    return process.returncode
