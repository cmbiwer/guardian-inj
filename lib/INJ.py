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
from ezca import Ezca
from guardian import GuardState
from gpstime import gpstime
from time import sleep

##################################################
# VARIABLES
##################################################

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_time = 20

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

        # get the current GPS time
        current_gps_time = gpstime.tconvert('now').gps()
        log.info('The time is %d', current_gps_time)

        # if injections are enabled then move to IDLE state
        inj_enabled = injtools.check_injections_enabled()
        if inj_enabled:
            return 'IDLE'

        # wait some set amount of time
        log.info('Will now sleep %d seconds\n', sleep_time)
        sleep(sleep_time)

class IDLE(GuardState):
    ''' State when the schedule is continously checked for injections.
    If an injection is imminent then the state will change to that
    injection type.
    '''

    def run(self):
        ''' Execute method in a loop.
        '''

        # get the current GPS time
        current_gps_time = gpstime.tconvert('now').gps()
        log.info('The time is %d', current_gps_time)

        # read schedule
        inj_list = injtools.read_schedule(path_schedule)
        log.info('There are %d injections in the future', len(inj_list))

        # check if injection is imminent
        global imminent_inj
        imminent_inj = injtools.check_injections_imminent(inj_list)

        # if injections are disabled then move to DISABLED state
        inj_enabled = injtools.check_injections_enabled()
        if not inj_enabled:
            log.info('Injections have been disabled')
            return 'DISABLED'

        # if there is an imminent injection then check if observing
        if imminent_inj:
            log.info('There is an imminent injection at %f', imminent_inj.scheduled_time)
            detector_enabled = injtools.check_detector_enabled()

            # if detector is in observation mode then change to injection-type state
            if detector_enabled:
                return imminent_inj.inj_type
            else:
                log.info('Detector is not in observation mode')

        # else there is no imminent injection continue
        else:
            log.info('There is no imminent injection')

        # wait some set amount of time
        log.info('Will now sleep %d seconds\n', sleep_time)
        sleep(sleep_time)

class CBC(GuardState):
    ''' State for performing a CBC injection.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # upload GraceDB hardware injection event
        injupload.upload_gracedb_event(imminent_inj)

        # call awgstream
        cmd = map(str, ['awgstream', exc_channel, sample_rate, 
               imminent_inj.path, imminent_inj.scale_factor])
        injtools.make_external_call(cmd)

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

