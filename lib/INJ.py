# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ base guardian module

This defines the behavior for all transient injections.
"""

from gpstime import gpstime
from guardian import GuardState
from injawg import awg_inject
from injtools import check_exttrig_alert, check_imminent_injection, read_schedule, read_waveform
#from injupload import gracedb_upload

# name of channel to inject transient signals
model_name = "CAL-INJ"
exc_channel_name = model_name + "_TRANSIENT_EXC"

# name of channel to check for external alerts
exttrig_channel_name = model_name + "_EXTTRIG_ALERT_TIME"

# seconds to wait for an external alert
exttrig_wait_time = 3600

# seconds to check for an imminent hardware injection
imminent_wait_time = 600

# seconds in advance to call awgstream
awgstream_wait_time = 30

# path to schedule file
schedule_path = "fake_schedule"

# sample rate of excitation channel and waveform files
sample_rate = 16384

# global variable for imminent HardwareInjection
global imminent_hwinj

# global variable to hold waveform time series
global waveform

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
    """ The IDLE state continuously loops IDLE.run checking for external
    alerts and if there is an imminent hardware injection.

    An imminment hardware injection is defined by imminent_wait_time in seconds.

    An external alert will cause a jump transition to the EXTTRIG_ALERT state if
    it is within exttrig_wait_time seconds.
    """

    def run(self):
        """ Execute method in a loop.
        """

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name, exttrig_wait_time)
        if exttrig_alert_time:
            return "EXTTRIG_ALERT"

        # check schedule for imminent hardware injection
        hwinj_list = read_schedule(schedule_path)
        imminent_hwinj = check_imminent_injection(hwinj_list, imminent_wait_time)

        print exttrig_alert_time, imminent_hwinj

class EXTTRIG_ALERT(GuardState):
    """ The EXTTRIG_ALERT state continuously loops EXTTRIG_ALERT.run checking
    if the most recent external alert is not within exttrig_wait_time seconds.
    Once the external alert is far enough in the past there will be a jump transition
    to the ENABLED state.
    """

    # automatically assign edges from every other state
    goto = True

    def run(self):
        """ Execute method in a loop.
        """

        # check if not external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name, exttrig_wait_time)
        if not exttrig_alert_time:
            return "ENABLED"

class PREP(GuardState):
    """ None.
    """

    def main(self):
        """ 
        """

        # upload hardware injection to gracedb

        # read waveform file
        waveform = read_waveform(imminent_hwinj.waveform_path)

        return

    def run(self):
        """ Execute method in a loop.
        """

        # check if external alert
        exttrig_alert_time = check_exttrig_alert(exttrig_channel_name, exttrig_wait_time)
        if exttrig_alert_time:
            return "EXTTRIG_ALERT"

        # check if hardware injection is imminent enough to call awgstream
        if check_imminent_injection([imminent_hwinj], awgstream_wait_time):

            # check if detector in desired observation mode
            if True:
                return hwinj.schedule_state
            else:
                return "ABORT"

class CBC(GuardState):
    """ None.
    """

    def main(self):
        """ Execute method once.
        """

        #! FIXME: commented out for dev
        # call awgstream
        #awg_inject(exc_channel_name, waveform, imminent_hwinj.schedule_time, sample_rate)

        return

class SUCCESS(GuardState):
    """ None.
    """

    def main(self):
        """ Execute method once.
        """

        return

class ABORT(GuardState):
    """ None.
    """

    def main(self):
        """ Execute method once.
        """

        return

# define directed edges that connect guardian states
edges = (
    ("ENABLED", "IDLE"),
    ("IDLE", "PREP"),
    ("PREP", "CBC"),
    ("PREP", "ABORT"),
    ("CBC", "SUCCESS"),
    ("CBC", "ABORT"),
)




