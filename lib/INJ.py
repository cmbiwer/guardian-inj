# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ base guardian module

This defines the behavior for all transient injections.
"""

from gpstime import gpstime
from guardian import GuardState
from injtools import check_exttrig_alert, check_imminent_injection, read_schedule

# name of channel to inject transient signals
model_name = "CAL-INJ"
exc_channel_name = model_name + "_TRANSIENT_EXC"

# name of channel to check for external alerts
exttrig_channel_name = model_name + "_EXTTRIG_ALERT_TIME"

# seconds to wait for an external alert
exttrig_wait_time = 3600

# seconds to check for an imminent hardware injection
imminent_wait_time = 60

# path to schedule file
schedule_path = "fake_schedule"

# sample rate of excitation channel and waveform files
sample_rate = 16384

# global variable for imminent HardwareInjection
global imminent_hwinj

class INIT(GuardState):
    """ The INIT state is the first state entered when starting the Guardian
    daemon. It will run INIT.main once where then there will be a jump transition
    to the DISABLED state.
    """

    def main(self):
        """ Execute method once.
        """

        return "DISABLED"

class DISABLED(GuardState):
    """ The DISABLED state is for when injections have been disabled manually.
    The DISABLED state will not be left unless the operator requests.
    """

    # automatically assign edges from every other state
    goto = True

    def run(self):
        """ Execute method in a loop.
        """

        #! FIXME: for tests only
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
    """ The IDLE state continuously loops.
    """

    def run(self):
        """ Execute method in a loop.
        """

        # check if electromagnetic alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name, exttrig_wait_time)

        # check schedule for imminent hardware injection
        hwinj_list = read_schedule(schedule_path)
        imminent_hwinj = check_imminent_injection(hwinj_list, imminent_wait_time)

        print exttrig_alert_time, imminent_hwinj

class EXTTRIG_ALERT(GuardState):
    """ None.
    """

    # automatically assign edges from every other state
    goto = True

    def run(self):
        """ None.
        """

        # check if electromagnetic alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name, exttrig_wait_time)
        if not exttrig_alert_time:
            return "ENABLED"

# define directed edges that connect guardian states
edges = (
    ("ENABLED", "IDLE"),
)




