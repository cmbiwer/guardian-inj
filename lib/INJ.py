# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ base guardian module

This module defines the behavior for all transient injections.

2016 - Christopher M. Biwer
"""

import inj_awg
import inj_io
import inj_upload
import os.path
import sys
import traceback
from gpstime import gpstime
from guardian import GuardState
from inj_det import check_exttrig_alert
from inj_types import check_imminent_injection

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

# minimum seconds required to awg in advance
awg_wait_time = 30

# sample rate of excitation channel and waveform files
sample_rate = 16384

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
        ezca[outcome_channel_name] = -3

    def run(self):
        """ Execute method in a loop.
        """

        return True

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

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            ezca[outcome_channel_name] = -4
            return "EXTTRIG_ALERT"

        # check schedule for imminent hardware injection
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

                    # get the current GPS time
                    current_gps_time = gpstime.tconvert("now").gps()

                    # legacy of the old setup to set TINJ_START_TIME
                    ezca[start_channel_name] = current_gps_time

                    return imminent_hwinj.schedule_state

                # set legacy TINJ_OUTCOME value for detector not in desired
                # observation mode
                log("Ignoring hardware injection since detector is not in \
                     the desired observation mode..")
                ezca[outcome_channel_name] = -5

            # set legacy TINJ_OUTCOME value for detector not locked
            log("Ignoring hardware injection since detector is not locked.")
            ezca[outcome_channel_name] = -6

class EXTTRIG_ALERT(GuardState):
    """ The EXTTRIG_ALERT state continuously loops EXTTRIG_ALERT.run checking
    if the most recent external alert is not within exttrig_wait_time seconds.
    Once the external alert is far enough in the past there will be a jump
    transition to the IDLE state.
    """

    def run(self):
        """ Execute method in a loop.
        """

        # check if not external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if not exttrig_alert_time:
            return "IDLE"

class _INJECT_STATE(GuardState):
    """ The _INJECT_STATE state is a subclass that injects the signal into
    the detector.

    The _INJECT_STATE state will read the waveform file and upload a hardware
    injection event to GraceDB upon entry.
    """

    # declare variable to hold the state of the injection
    stream = None

    # declare a str to store the GraceDB ID of the hardware injection
    gracedb_id = ""

    def main(self):
        """ Execute method once.
        """

        # check schedule for imminent hardware injection
        imminent_hwinj = check_imminent_injection(inj_io.hwinj_list,
                                                  imminent_wait_time)
        if not imminent_hwinj or imminent_hwinj.schedule_state != __name__:
            message = "Aborted: Injection no longer most imminent."
            log(message)
            return "INJECT_ABORT"

        # try to read waveform, upload an event to GraceDB, and call awg
        try:

            # create a dict for formatting; we allow users to use the {ifo}
            # substring substition in the waveform_path column
            format_dict = {
                "ifo" : ezca.ifo
            }

            # read waveform file
            waveform_path = imminent_hwinj.waveform_path.format(**format_dict)
            waveform = inj_io.read_waveform(waveform_path)

            # upload hardware injection to GraceDB
            self.gracedb_id = inj_upload.gracedb_upload_injection(imminent_hwinj,
                                            [ezca.ifo],
                                            group=imminent_hwinj.schedule_state)

            # legacy of the old setup to set TINJ_TYPE
            tinj_type_dict = {
                "CBC" : 1,
                "Burst" : 2,
                "Stochastic" : 3,
                "DetChar" : 4,
                "Test" : 5,
            }
            ezca[type_channel_name] = tinj_type_dict[hwinj.schedule_state]

            # get the current GPS time
            current_gps_time = gpstime.tconvert("now").gps()

            # check if most imminent injection has passed and jump tp INJECT_ABORT state
            # if it has already past; this is a safe guard against long execution
            # times when uploading to GraceDB or reading large waveform files
            if current_gps_time > imminent_hwinj.schedule_time - awg_wait_time:
                message = "Aborted: Most imminent hardware injection is in the past."
                log(message)
                inj_upload.gracedb_upload_message(self.gracedb_id, message)
                return "INJECT_ABORT"

            # call awg to inject the signal
            self.stream = inj_awg.awg_inject(exc_channel_name, imminent_hwinj.waveform,
                                            imminent_hwinj.schedule_time, sample_rate,
                                            scale_factor=scale_factor, wait=True)

        # if there was an error add it to the log and jump to INJECT_ABORT
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            inj_upload.gracedb_upload_message(self.gracedb_id, message)
            return "INJECT_ABORT"

    def run(self):
        """ Execute method in a loop.
        """

        # check if stream has ended and jump to INJECT_SUCCESS
        if not self.stream.opened:
            message = "This hardware injection was successful."
            inj_upload.gracedb_upload_message(self.gracedb_id, message)
            return "INJECT_SUCCESS"

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # if stream still open after calculated end of injection data plus some
        # padding then jump to INJECT_ABORT
        end_time_limit = self.stream.starttime \
                         + self.stream.rate * len(self.stream.data) \
                         + awg_wait_time
        if end_time_limit < current_gps_time:
            message = "This hardware injection was aborted for running too long."
            return "INJECT_ABORT"

class CBC(_INJECT_STATE):
    """ The CBC state will perform a CBC hardware injection.
    """

class BURST(_INJECT_STATE):
    """ The BURST state will perform a burst hardware injection.
    """

class STOCHASTIC(_INJECT_STATE):
    """ The STOCHASTIC state will perform a stochastic hardware injection.
    """

class DETCHAR(_INJECT_STATE):
    """ The DETCHAR state will perform a detector characterization
     hardware injection.
    """

class INJECT_SUCCESS(GuardState):
    """ The INJECT_SUCCESS state is an intermediary state for an injection that was
    successfully performed. There is a jump transition to the IDLE state.
    """

    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for successful injection
        ezca[outcome_channel_name] = 1

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # legacy of the old setup to set TINJ_END_TIME
        ezca[end_channel_name] = current_gps_time

        return "IDLE"

class INJECT_ABORT(GuardState):
    """ The INJECT_ABORT state is an intermediary state for an injection that was not
    successfully performed. There is a jump transition to the IDLE state.

    A hardware injection could have been aborted for several reasons including
    but not limited to incorrect types in schedule file, could not read
    waveform file, an external alert was recieved in the PREP state, or the
    detector is not locked.
    """

    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for failed injection
        ezca[outcome_channel_name] = -4

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # legacy of the old setup to set TINJ_END_TIME
        ezca[end_channel_name] = current_gps_time

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            ezca[outcome_channel_name] = -2
            return "EXTTRIG_ALERT"

        return "IDLE"

class RELOAD(GuardState):
    """ The RELOAD state will reload the schdedule file. There will be
    a jump transition to either the RELOAD_SUCCESS or RELOAD_FAILURE
    state after reading the schedule file.
    """

    def main(self):
        """ Execute method once.
        """

        # read schedule and jump transition to success state
        try:
            reload(inj_io)
            return "RELOAD_SUCCESS"

        # if there was an error then jump transition to failure state
        except:
            message = traceback.print_exc(file=sys.stdout)
            log(message)
            return "RELOAD_FAILURE"

class RELOAD_SUCCESS(GuardState):
    """ The RELOAD_SUCCESS state is entered upon successfully reloading
    the schedule file. The guardian node will remain in the
    RELOAD_SUCCESS state until there is a request to change states.

    The operator should request the RELOAD_SUCCESS to reload the
    schedule file.
    """

    def run(self):
        """ Execute method in a loop.
        """

        return True

class RELOAD_FAILURE(GuardState):
    """ The RELOAD_FAILURE state is entered upon successfully reloading
    the schedule file. The guardian node will remain in the
    RELOAD_FAILURE state until there is a request to change states.
    """

    def run(self):
        """ Execute method in a loop.
        """

        return True

# define directed edges that connect guardian states
edges = (
    # DISABLED jumps
    ("INIT", "DISABLED"),
    ("DISABLED", "IDLE"),
    # EXTTRIG_ALERT jumps
    ("IDLE", "EXTTRIG_ALERT"),
    ("INJECT_ABORT", "EXTTRIG_ALERT"),
    ("EXTTRIG_ALERT", "IDLE"),
    # CBC jumps
    ("IDLE", "CBC"),
    ("CBC", "INJECT_SUCCESS"),
    ("CBC", "INJECT_ABORT"),
    # BURST jumps
    ("IDLE", "BURST"),
    ("BURST", "INJECT_SUCCESS"),
    ("BURST", "INJECT_ABORT"),
    # STOCHASTIC jumps
    ("IDLE", "STOCHASTIC"),
    ("STOCHASTIC", "INJECT_SUCCESS"),
    ("STOCHASTIC", "INJECT_ABORT"),
    # DETCHAR jumps
    ("IDLE", "DETCHAR"),
    ("DETCHAR", "INJECT_SUCCESS"),
    ("DETCHAR", "INJECT_ABORT"),
    # generic post-injection jumps
    ("INJECT_SUCCESS", "IDLE"),
    ("INJECT_ABORT", "IDLE"),
    # RELOAD jumps
    ("DISABLED", "RELOAD"),
    ("RELOAD", "RELOAD_SUCCESS"),
    ("RELOAD", "RELOAD_FAILURE"),
    ("RELOAD_SUCCESS","IDLE"),
    ("RELOAD_FAILURE","IDLE"),
)

