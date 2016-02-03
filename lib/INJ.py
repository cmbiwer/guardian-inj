# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ base guardian module

This defines the behavior for all transient injections.
'''

###############################################################################
# IMPORTS
###############################################################################

import injtools
#import injupload
from guardian import GuardState
from gpstime import gpstime
from time import sleep

###############################################################################
# VARIABLES
###############################################################################

# name of channel to inject transient signals
exc_channel = 'CAL-INJ_TRANSIENT_EXC'

# seconds to sleep after an iteration of STATE.run
sleep_time = 20

# path to schedule file
schedule_path = 'fake_schedule'

# sample rate of excitation channel and waveform files
sample_rate = 16384

#FIXME: use echo for development but for production should be awgstream
# executable to perform hardware injections
inj_exe = 'echo'

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

        # FIXME: off until production
        # set injection bit to disabled
        # ezca.write('TINJ_OUTCOME', -4)

        # if injections are enabled then move to IDLE state
        inj_enabled = injtools.check_injections_enabled()
        if inj_enabled:
            return 'IDLE'

        # wait some set amount of time
        log('Will now sleep %d seconds\n'%sleep_time)
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

        # read schedule
        inj_list = injtools.read_schedule(schedule_path)
        log('There are %d injections in the future'%len(inj_list))

        # check if injection is imminent
        global imminent_inj
        imminent_inj = injtools.check_injections_imminent(inj_list)

        # if injections are disabled then move to DISABLED state
        inj_enabled = injtools.check_injections_enabled()
        if not inj_enabled:
            log('Injections have been disabled')
            return 'DISABLED'

        # if there is an imminent injection then check if detector is observing
        if imminent_inj:
            log('There is an imminent injection at %f'%imminent_inj.scheduled_time)
            detector_enabled = injtools.check_detector_enabled()

            # if detector is in observation mode then change to
            # injection-type state, eg. CBC, BURST, or STOCHASTIC
            if detector_enabled:
                return imminent_inj.inj_type

            # else continue in IDLE.run and do not perform injection
            else:
                log('Will not perform injection because detector is' + \
                         'not in observation mode')

                # FIXME: off until production
                # set injection bit to not in observation mode
                # ezca.write('TINJ_OUTCOME', -6)

        # else there is no imminent injection continue
        else:
            log('There is no imminent injection')

        # wait some set amount of time
        log('Will now sleep %d seconds\n'%sleep_time)
        sleep(sleep_time)

class CBC(GuardState):
    ''' The CBC state is for performing CBC hardware injections. In the CBC
    state a hardware injection event is uploaded to GraceDB. Then an external
    call to awgstream is used to inject the waveform into the detector.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # FIXME: grid utils not on control room workspaces
        # upload GraceDB hardware injection event
        #injupload.upload_gracedb_event(imminent_inj)

        # FIXME: off until production
        # set EPICs records for injection type and time
        # ezca.write('TINJ_TYPE', 1)
        # ezca.write('TINJ_START', imminent_inj.scheduled_time)
        # ezca.write('TINJ_END', 0)

        # FIXME: off until production
        # set injection bit to streaming
        # ezca.write('TINJ_OUTCOME', 2)

        # call awgstream
        log('Calling external command to perform injection')
        cmd = map(str, [inj_exe, exc_channel, sample_rate, 
               imminent_inj.waveform_path, imminent_inj.scale_factor])
        retcode = injtools.make_external_call(cmd)

        # FIXME: off until production
        # set injection bit to failure or successful
        # if retcode:
            # ezca.write('TINJ_OUTCOME', -4)
        # else:
            # ezca.write('TINJ_OUTCOME', 1)

        # FIXME: off until production
        # set end time of injection
        current_gps_time = gpstime.tconvert('now').gps()
        # ezca.write('TINJ_END', current_gps_time)

        # FIXME: set to 300 seconds because using echo as inj_exe
        # wait some set amount of time
        postinj_time = 300
        log('Will now sleep %d seconds\n'%postinj_time)
        sleep(postinj_time)

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

