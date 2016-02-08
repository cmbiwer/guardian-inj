# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ base guardian module

This module defines the behavior for all transient injections.
"""

from gpstime import gpstime
from guardian import GuardState
from injawg import awg_inject
from injtools import check_exttrig_alert, check_imminent_injection
from injtools import read_schedule, read_waveform
from injupload import gracedb_upload_injection, gracedb_upload_message

# name of channel to inject transient signals
model_name = "CAL-INJ"
exc_channel_name = model_name + "_TRANSIENT_EXC"

# name of channel to check for external alerts
exttrig_channel_name = model_name + "_EXTTRIG_ALERT_TIME"

# name of channel to check if detector is locked
lock_channel_name = "GRD-ISC_LOCK_OK"

# name of channel to check if intent mode on
obs_channel_name = "ODC-MASTER_CHANNEL_LATCH"

# name of channel to write tinj type
type_channeL_name = model_name + "_TINJ_TYPE"

# seconds to wait for an external alert
exttrig_wait_time = 3600

# seconds to check for an imminent hardware injection
imminent_wait_time = 600

# seconds in advance to call awg
awg_wait_time = 30

# path to schedule file
schedule_path = "fake_schedule"

# sample rate of excitation channel and waveform files
sample_rate = 16384

# declare variable for imminent HardwareInjection
imminent_hwinj = None

# declare variable to hold waveform time series
waveform = None

# declare variable to hold GraceDB ID
gracedb_id = None

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

    def run(self):
        """ Execute method in a loop.
        """

        #! FIXME: commented out for dev
        return "ENABLED"

        return

class ENABLED(GuardState):
    """ The ENABLED sate is the state that is requested when moving out of
    the DISABLED state. The ENABLED state will jump transition to the IDLE
    state.
    """

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

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            return "EXTTRIG_ALERT"

        # check schedule for imminent hardware injection
        hwinj_list = read_schedule(schedule_path)
        imminent_hwinj = check_imminent_injection(hwinj_list,
                                                  imminent_wait_time)
        if imminent_hwinj:
            return "PREP"

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
    """ The PREP state will upload a hardware injection event to GraceDB and
    read the waveform file upon entry. It will also set the legacy TINJ_TYPE
    EPICs record for the desired injection type at this time.

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

        # try to upload to GraceDB and read waveform
        try:

            #! FIXME: commented out for dev
            # upload hardware injection to GraceDB
            #gracedb_id = gracedb_upload_injection(hwinj, ezca["ifo"],
            #                                      group=hwinj.schedule_state)

            # read waveform file
            waveform = read_waveform(imminent_hwinj.waveform_path)

            #! FIXME: commented out for dev
            # legacy of the old setup to set TINJ_TYPE
            tinj_type_dict = {
                "CBC" : 1,
                "Burst" : 2,
                "Stochastic" : 3,
                "DetChar" : 4,
            }
            #ezca[type_channel_name] = tinj_type_dict[hwinj.schedule_state]

        # if there was an error add it to the log and ABORT the injection
        except Exception as e:
            log(e)
            return "ABORT"

    def run(self):
        """ Execute method in a loop.
        """

        # check if external alert
        # in the PREP state if we find an external alert we jump transition
        # to the ABORT state first
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            return "ABORT"

        # check if hardware injection is imminent enough to call awg
        if check_imminent_injection([imminent_hwinj], awg_wait_time):

            # check if detector is locked
            if ezca.read(lock_channel_name) == 1:

                # check if detector in desired observing mode and
                # then make a jump transition to injection type state
                latch = ezca.read(obs_channel_name)
                if latch == 1 and imminent_hwinj.observation_mode == 1 or \
                        latch == 0 and imminent_hwinj.observation_mode == 0:

                    # get the current GPS time
                    current_gps_time = gpstime.tconvert("now").gps()

                    # legacy of the old setup to set TINJ_START_TIME
                    #ezca["TINJ_START_TIME"] = current_gps_time

                    return hwinj.schedule_state

            # if detector not locked or not desired observing mode then abort
            return "ABORT"

class CBC(GuardState):
    """ The CBC state will perform a CBC hardware injection.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awg to inject the signal
        #retcode = awg_inject(exc_channel_name, waveform,
        #                     imminent_hwinj.schedule_time, sample_rate,
        #                     scale_factor=scale_factor)
        retcode = 1

        # jump transition to post-injection state
        if retcode:
            return "ABORT"
        else:
            return "SUCCESS"

class SUCCESS(GuardState):
    """ The SUCCESS state is an intermediary state for an injection that was
    successfully performed. There is a jump transition to the ENABLED state.
    """

    def main(self):
        """ Execute method once.
        """

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # legacy of the old setup to set TINJ_END_TIME
        #ezca["TINJ_END_TIME"] = current_gps_time

        # append success message to GraceDB event
        message = "This hardware injection was successful."
        gracedb_upload_message(gracedb_id, message)

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

        # get the current GPS time
        current_gps_time = gpstime.tconvert("now").gps()

        # legacy of the old setup to set TINJ_END_TIME
        #ezca["TINJ_END_TIME"] = current_gps_time

        # append abort message to GraceDB event
        message = "This hardware injection was aborted."
        gracedb_upload_message(gracedb_id, message)

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_time)
        if exttrig_alert_time:
            return "EXTTRIG_ALERT"

        return "ENABLED"

# define directed edges that connect guardian states
edges = (
    ("ENABLED", "IDLE"),
    ("IDLE", "EXTTRIG_ALERT"),
    ("IDLE", "PREP"),
    ("PREP", "CBC"),
    ("PREP", "ABORT"),
    ("CBC", "SUCCESS"),
    ("CBC", "ABORT"),
    ("ABORT", "EXTTRIG_ALERT"),
)




