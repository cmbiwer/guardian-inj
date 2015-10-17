# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ base guardian module

This defines the behavior for all transient injections.
'''

###############################################################################
# IMPORTS
###############################################################################

import injtools
import injupload
import logging
from ezca import Ezca
from guardian import GuardState
from gpstime import gpstime
from time import sleep

###############################################################################
# VARIABLES
###############################################################################

# name of module
prefix = 'CAL-INJ'

# name of channel to inject transient signals
exc_channel = prefix + '_TRANSIENT_EXC'

# seconds to sleep after an operation
sleep_time = 20

# path to schedule file
schedule_path = 'fake_schedule'

# sample rate of excitation channel and waveform files
sample_rate = 16384

# executable to perform hardware injections
inj_exe = 'echo'

# setup log
log = logging.getLogger('INJ')

# global variable for imminent injection
imminent_inj = None

###############################################################################
# STATES
###############################################################################

class INIT(GuardState):
    ''' The INIT state is the first state entered when starting the Guardian
    daemon. It will run INIT.main once and then there will be a jump transition
    to the DISABLED state.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # setup EPICS reading and writing
        ezca = Ezca(prefix)

        return 'DISABLED'

class DISABLED(GuardState):
    ''' The DISABLED state is for when injections have been disabled manually
    or if there is an electromagnetic alert. The DISABLED state will loop
    continuously checking if injections have been enabled and enough time has
    passed since the last electromagnetic alert. If this is true, then there
    will be a jump transition to the IDLE state.
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
    ''' The IDLE state will loop continuously. In each loop it will start off
    by reading the schedule and checking if there is an imminent injection.

    There is a check to see if injections have been disabled. If injections
    have been disabled then there will be a jump transition to the DISABLED
    state.

    Now there are two cases.

    The first case injections are enabled and there is an imminent injection,
    then there is a check to see if the detector is in observation mode. If
    the detector is in observation mode then there is a jump transition to the
    injection-type state, eg. CBC, BURST, or STOCHASTIC states. Else the
    IDLE.run loop is repeated.

    The second case there is no imminent injection and the IDLE.run loop is
    repeated.
    '''

    def run(self):
        ''' Execute method in a loop.
        '''

        # get the current GPS time
        current_gps_time = gpstime.tconvert('now').gps()
        log.info('The time is %d', current_gps_time)

        # read schedule
        inj_list = injtools.read_schedule(schedule_path)
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
    ''' The CBC state is for performing CBC hardware injections. In the CBC
    state a hardware injection event is uploaded to GraceDB. Then an external
    call to awgstream is used to inject the waveform into the detector.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # upload GraceDB hardware injection event
        #injupload.upload_gracedb_event(imminent_inj)

        # call awgstream
        cmd = map(str, [inj_exe, exc_channel, sample_rate, 
               imminent_inj.waveform_path, imminent_inj.scale_factor])
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

