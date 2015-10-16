# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ base guardian module

This defines the behavior for all transient injections.
'''

##################################################
# IMPORTS
##################################################

# cannot use glue module yet

import injtools
import logging
import ligo.gracedb.rest as gracedb_rest
from ezca import Ezca
from gpstime import gpstime
from guardian import GuardState
from injupload import upload_gracedb_event
from os.path import basename
from time import sleep

##################################################
# VARIABLES
##################################################

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_time = 2

# full path to schedule file
path_schedule = '/ligo/home/christopher.biwer/src/fake_schedule'

# sample rate of excitation channel and waveform files
sample_rate = 16384

# list of IFOs
ifo_list = ['H1', 'L1']

##################################################
# STATES
##################################################

class INIT(GuardState):
    ''' State that is first entered when starting Guardian daemon.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # initialize log
        #logging_level = logging.WARN
        #logging.basicConfig(file='INJ.log', format='%(asctime)s : %(message)s', level=logging_level)

        # setup EPICS reading and writing
        ezca = Ezca(prefix)

        return 'DISABLED'

class DISABLED(GuardState):
    ''' State for when injections are disabled either manually
    or from an electromagnetic alert.
    '''

    # automatically assign edges from every other state
    goto = True

    def run(self):
        ''' Execute method in a loop.
        '''

        # if injections are enabled then move to IDLE state
        injections_enabled = injtools.check_injections_enabled()
        if injections_enabled:
            return 'IDLE'
        else:
            sleep(sleep_time)

class IDLE(GuardState):
    ''' State when the schedule is continously checked for injections.
    If an injection is imminent then the state will change to that
    injection type.
    '''

    def run(self):
        ''' Execute method in a loop.
        '''

        # wait some set amount of time
        sleep(sleep_time)

        # read schedule
        injection_list = injtools.read_schedule(path_schedule)
        print 'There are ', len(injection_list), 'injections in the future'

        # check if injection is imminent
        imminent_injection = injtools.check_injections_imminent(injection_list)
        if imminent_injection:
            print 'Injection imminent', imminent_injection.scheduled_time
        else:
            print 'No injection imminent' 
            return 'IDLE'

        # if injections are disabled then move to DISABLED state
        injections_enabled = injtools.check_injections_enabled()
        if not injections_enabled: 
            return 'DISABLED'

        # if detector is in observation mode then change to injection-type state
        detector_enabled = injtools.check_detector_enabled()
        if not detector_enabled:
            print 'Detector is not in observation mode'
            return 'IDLE'
        else:
            return imminent_injection.injection_type

class CBC(GuardState):
    ''' State for performing a CBC injection.
    '''

    def main(self):
        ''' Executate method once.
        '''
        # read schedule

        # print information about injections (total num, future inj)

        # check if injection is imminent

        # print if injection is imminent

        # get full path to injection file

        # get injection type

        # if injections enabled and no electromangetic alert go to DISABLED state

        # if detector is locked and intent bit is on then continue

        # upload GraceDB hardware injection event

        # call awgstream

        # check that awgstream completed

        pass

##################################################
# EDGES
##################################################

# define directed edges that connect guardian states
edges = (
    ('INIT', 'DISABLED'),
    ('DISABLED', 'IDLE'),
    ('IDLE', 'CBC'),
)

