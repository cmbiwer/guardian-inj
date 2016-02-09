# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ base guardian module

This module defines the behavior for all transient injections.
"""

import os.path
import sys
import traceback
from gpstime import gpstime
from guardian import GuardState
from inj_awg import awg_inject
from inj_io import read_schedule, read_waveform
from inj_det import check_exttrig_alert
from inj_types import check_imminent_injection
from inj_upload import gracedb_upload_injection, gracedb_upload_message

# name of channel to inject transient signals
model_name = "CAL-PINJX"
exc_channel_name = model_name + "_TRANSIENT_EXC"

# name of channel to write legacy tinj EPIC records
type_channeL_name = model_name + "_TINJ_TYPE"
start_channel_name = model_name + "_TINJ_START_TIME"
end_channel_name = model_name + "_TINJ_END_TIME"
outcome_channel_name = model_name + "_TINJ_OUTCOME"

# name of channel to check for external alerts
exttrig_channel_name = "CAL-INJ_EXTTRIG_ALERT_TIME"

# name of channel to check if detector is locked
lock_channel_name = "GRD-ISC_LOCK_OK"

# name of channel to check if intent mode on
obs_channel_name = "ODC-MASTER_CHANNEL_LATCH"

# seconds to wait for an external alert
exttrig_wait_time = 3600

# seconds to check for an imminent hardware injection
imminent_wait_time = 600

# seconds in advance to call awg
awg_wait_time = 30

# path to schedule file
schedule_path = os.path.dirname(__file__) + "/schedule/schedule_1148558052.txt"

# sample rate of excitation channel and waveform files
sample_rate = 16384

# declare variable for imminent HardwareInjection
imminent_hwinj = None

class INIT(GuardState):
    """ The INIT state is the first state entered when starting the Guardian
    daemon. It will run INIT.main once where there will be a jump transition
    to the DISABLED state.
    """

    def main(self):
        """ Execute method once.
        """

        return "DISABLED"

class DISABLED(GuardState):
    """ The DISABLED state is for when hardware injections have been disabled
    manually. The DISABLED state will not be left unless the operator requests.
    """

    # automatically assign edges from every other state
    goto = True

    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for injections disabled or paused
        #ezca[outcome_channel_name] = -3

    def run(self):
        """ Execute method in a loop.
        """

        return

class ENABLED(GuardState):
    """ The ENABLED sate is the state that is requested when moving out of
    the DISABLED state. The ENABLED state will jump transition to the IDLE
    state.
    """

    # automatically assign edges from every other state
    goto = True

    def main(self):
        """ Execute method once.
        """

        return "IDLE"

class IDLE(GuardState):
    """ The IDLE state continuously loops IDLE.run checking for external
    alerts and if there is an imminent hardware injection.

    An imminment hardware injection is defined by imminent_wait_time in
    seconds. If an imminent hardware injection is found then there will be a
    jump transition to the PREP state.

    An external alert will cause a jump transition to the EXTTRIG_ALERT state
    if it is within exttrig_wait_time seconds.
    """

    def run(self):
        """ Execute method in a loop.
        """

        # use the global variables so they can used in multiple states
        global imminent_hwinj

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            #ezca[outcome_channel_name] = -4
            return "EXTTRIG_ALERT"

        # check schedule for imminent hardware injection
        try:
            hwinj_list = read_schedule(schedule_path)
            imminent_hwinj = check_imminent_injection(hwinj_list,
                                                      imminent_wait_time)

            # jump transition to PREP state if imminent hardware injection
            if imminent_hwinj:

                # check if detector is locked
                if ezca[lock_channel_name] == 1:

                    # check if detector in desired observing mode and
                    # then make a jump transition to injection type state
                    latch = ezca[obs_channel_name]
                    if latch == 1 and imminent_hwinj.observation_mode == 1 or \
                            latch == 0 and imminent_hwinj.observation_mode == 0:
                        return "PREP"

                    # set legacy TINJ_OUTCOME value for detector not in desired
                    # observation mode
                    #ezca[outcome_channel_name] = -5

                # set legacy TINJ_OUTCOME value for detector not locked
                #ezca[outcome_channel_name] = -6

        # if there is an error reading the schedule then just retry PREP.run
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            
class EXTTRIG_ALERT(GuardState):
    """ The EXTTRIG_ALERT state continuously loops EXTTRIG_ALERT.run checking
    if the most recent external alert is not within exttrig_wait_time seconds.
    Once the external alert is far enough in the past there will be a jump
    transition to the ENABLED state.
    """

    def run(self):
        """ Execute method in a loop.
        """

        # check if not external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if not exttrig_alert_time:
            return "ENABLED"

class PREP(GuardState):
    """ The PREP state will read the waveform file and upload a hardware
    injection event to GraceDB upon entry.

    It will then continuously run PREP.run until its nearly time to inject.
    Once the current GPS time is within awg_wait_time of the start of the
    injection, then it will check if the detector is locked and in the desired
    observing mode.

    If it is then there will be a jump transition to the injection type's
    state, else there will be a jump transition to the ABORT state.
    """

    def main(self):
        """ Execute method once.
        """

        # use the global variables so they can used in multiple states
        global imminent_hwinj

        # try to upload to GraceDB and read waveform
        try:

            # read waveform file
            imminent_hwinj.waveform = read_waveform(imminent_hwinj.waveform_path)

            #! FIXME: commented out for dev
            # upload hardware injection to GraceDB
            imminent_hwinj.gracedb_id = gracedb_upload_injection(imminent_hwinj,
                                            [ezca.ifo],
                                            group=imminent_hwinj.schedule_state)

            #! FIXME: commented out for dev
            # legacy of the old setup to set TINJ_TYPE
            tinj_type_dict = {
                "CBC" : 1,
                "Burst" : 2,
                "Stochastic" : 3,
                "DetChar" : 4,
                "Test" : 5,
            }
            #ezca[type_channel_name] = tinj_type_dict[hwinj.schedule_state]

        # if there was an error add it to the log and ABORT the injection
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "ABORT"

    def run(self):
        """ Execute method in a loop.
        """

        # check if external alert;  in the PREP state if we find an external
        # alert we jump transition to the ABORT state first
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            log("Found external alert so aborting hardware injection.")
            return "ABORT"

        # check if hardware injection is imminent enough to call awg
        if check_imminent_injection([imminent_hwinj], awg_wait_time):

            # check if detector is locked
            if ezca[lock_channel_name] == 1:

                # check if detector in desired observing mode and
                # then make a jump transition to injection type state
                latch = ezca[obs_channel_name]
                if latch == 1 and imminent_hwinj.observation_mode == 1 or \
                        latch == 0 and imminent_hwinj.observation_mode == 0:

                    # get the current GPS time
                    current_gps_time = gpstime.tconvert("now").gps()

                    #! FIXME: commented out for dev
                    # legacy of the old setup to set TINJ_START_TIME
                    #ezca[start_channel_name] = current_gps_time

                    return hwinj.schedule_state

            # if detector not locked or not desired observing mode then abort
            log("Detector is not locked or in desired observing mode.")
            return "ABORT"

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # check if most imminent injection has passed and jump tp ABORT state
        # if it has already past; this is a safe guard against long execution
        # times when uplaoding to GraceDB or reading large waveform files
        if current_gps_time > imminent_hwinj.schedule_time:
            log("Most imminent hardware injection is in the past.")
            return "ABORT"

class CBC(GuardState):
    """ The CBC state will perform a CBC hardware injection.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awg to inject the signal
        try:
            #awg_inject(exc_channel_name, imminent_hwinj.waveform,
            #           imminent_hwinj.schedule_time, sample_rate,
            #           scale_factor=scale_factor)

            # jump transition to post-injection state
            return "SUCCESS"

        # if there was a failure then jump transition to ABORT state
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "ABORT"

class BURST(GuardState):
    """ The BURST state will perform a burst hardware injection.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awg to inject the signal
        try:
            #awg_inject(exc_channel_name, imminent_hwinj.waveform,
            #           imminent_hwinj.schedule_time, sample_rate,
            #           scale_factor=scale_factor)

            # jump transition to post-injection state
            return "SUCCESS"

        # if there was a failure then jump transition to ABORT state
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "ABORT"

class STOCHASTIC(GuardState):
    """ The STOCHASTIC state will perform a stochastic hardware injection.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awg to inject the signal
        try:
            #awg_inject(exc_channel_name, imminent_hwinj.waveform,
            #           imminent_hwinj.schedule_time, sample_rate,
            #           scale_factor=scale_factor)

            # jump transition to post-injection state
            return "SUCCESS"

        # if there was a failure then jump transition to ABORT state
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "ABORT"

class DETCHAR(GuardState):
    """ The DETCHAR state will perform a detector characterization
     hardware injection.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awg to inject the signal
        try:
            #awg_inject(exc_channel_name, imminent_hwinj.waveform,
            #           imminent_hwinj.schedule_time, sample_rate,
            #           scale_factor=scale_factor)

            # jump transition to post-injection state
            return "SUCCESS"

        # if there was a failure then jump transition to ABORT state
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "ABORT"

class SUCCESS(GuardState):
    """ The SUCCESS state is an intermediary state for an injection that was
    successfully performed. There is a jump transition to the ENABLED state.
    """

    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for successful injection
        #ezca[outcome_channel_name] = 1

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        #! FIXME: commented out for dev
        # legacy of the old setup to set TINJ_END_TIME
        #ezca[end_channel_name] = current_gps_time

        # append success message to GraceDB event
        # we block this in a try-except statment because if
        # it cannot connect to GraceDB it could cause guardian to fail
        try:
            message = "This hardware injection was successful."
            gracedb_upload_message(imminent_hwinj.gracedb_id, message)
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)

        return "ENABLED"

class ABORT(GuardState):
    """ The ABORT state is an intermediary state for an injection that was not
    successfully performed. There is a jump transition to the ENABLED state.

    A hardware injection could have been aborted for several reasons including
    but not limited to incorrect types in schedule file, could not read
    waveform file, an external alert was recieved in the PREP state, or the
    detector is not locked.
    """

    def main(self):
        """ Execute method once.
        """

        # use the global variables so they can used in multiple states

        # set legacy TINJ_OUTCOME value for failed injection
        #ezca[outcome_channel_name] = -4

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        #! FIXME: commented out for dev
        # legacy of the old setup to set TINJ_END_TIME
        #ezca[end_channel_name] = current_gps_time

        # append success message to GraceDB event
        # we block this in a try-except statment because if
        # it cannot connect to GraceDB it could cause guardian to fail
        try:
            message = "This hardware injection was successful."
            gracedb_upload_message(imminient_hwinj.gracedb_id, message)
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            #ezca[outcome_channel_name] = -2
            return "EXTTRIG_ALERT"

        return "ENABLED"

# define directed edges that connect guardian states
edges = (
    ("DISABLED", "ENABLED"),
    ("ENABLED", "IDLE"),
    ("IDLE", "EXTTRIG_ALERT"),
    ("IDLE", "PREP"),
    ("PREP", "CBC"),
    ("PREP", "BURST"),
    ("PREP", "STOCHASTIC"),
    ("PREP", "DETCHAR"),
    ("PREP", "ABORT"),
    ("CBC", "SUCCESS"),
    ("CBC", "ABORT"),
    ("BURST", "SUCCESS"),
    ("BURST", "ABORT"),
    ("STOCHASTIC", "SUCCESS"),
    ("STOCHASTIC", "ABORT"),
    ("DETCHAR", "SUCCESS"),
    ("DETCHAR", "ABORT"),
    ("ABORT", "EXTTRIG_ALERT"),
)




