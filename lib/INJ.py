# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ base guardian module

This defines the behavior for all transient injections.
'''

##################################################
# IMPORTS
##################################################

import injtools
import injupload
import logging
import ligo.gracedb.rest as gracedb_rest
from ezca import Ezca
from guardian import GuardState
from time import sleep

##################################################
# VARIABLES
##################################################

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_time = 2

# path to schedule file
path_schedule = 'fake_schedule'

# sample rate of excitation channel and waveform files
sample_rate = 16384

# list of IFOs
ifo_list = ['H1', 'L1']

# setup log
log = logging.getLogger('INJ')

# global variable for imminent injection
imminent_inj = None

##################################################
# STATES
##################################################

class INIT(GuardState):
    ''' State that is first entered when starting Guardian daemon.
    '''

    def main(self):
        ''' Executate method once.
        '''

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
        inj_enabled = injtools.check_injections_enabled()
        if inj_enabled:
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
        log.info('Entering idle loop and waiting %d seconds', sleep_time)
        sleep(sleep_time)

        # read schedule
        inj_list = injtools.read_schedule(path_schedule)
        log.info('There are %d injections in the future', len(inj_list))

        # check if injection is imminent
        global imminent_inj
        imminent_inj = injtools.check_injections_imminent(inj_list)
        if imminent_inj:
            log.info('There is an imminent injection at %f', imminent_inj.scheduled_time)
        else:
            log.info('There is no imminent injection')

        # if injections are disabled then move to DISABLED state
        inj_enabled = injtools.check_injections_enabled()
        if not inj_enabled: 
            log.info('Injections have been disabled')
            return 'DISABLED'

        # if detector is in observation mode then change to injection-type state
        detector_enabled = injtools.check_detector_enabled()
        if not detector_enabled:
            log.info('Detector is not in observation mode')
        else:
            return imminent_inj.injection_type

class CBC(GuardState):
    ''' State for performing a CBC injection.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # upload GraceDB hardware injection event
        injupload.upload_gracedb_event(imminent_inj)

        # call awgstream
        injtools.make_external_call()

        # check that awgstream completed

        return 'IDLE'

##################################################
# EDGES
##################################################

# define directed edges that connect guardian states
edges = (
    ('INIT', 'DISABLED'),
    ('DISABLED', 'IDLE'),
    ('IDLE', 'CBC'),
)

