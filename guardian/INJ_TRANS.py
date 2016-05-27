# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
base guardian module for hardware injections

This module defines the states and their relations for all transient injections
guardian states. Configuration parameters for the guardian node are at the top
of the module.

General Structure of the Node
-----------------------------

The pathway for a successful injection is:
  (1) Update the schedule file and validate it.
  (2) Request the INJECT_SUCCESS state. The node should be in the
      WAIT_FOR_NEXT_INJECT state.
  (3) Once its time to perform the injection the node will transition to the
      CHECK_SCHEDULE_TIMES state. Here the node will double-check that no two
      injections are scheduled too closely together.
  (4) Then it will transition to the CREATE_GRACEDB_EVENT state, where it will
      upload a hardware injection event to GraceDB.
  (5) Then it will transition to the READ_WAVEFORM state were it will read the
      data from the waveform file.
  (6) Then it will transition to the AWG_STREAM_OPEN_PREINJECT where it will
      wait to perform the injection. Right before its the scheduled time, the
      node will transition to the _INJECT_STATE_ACTIVE state, eg. INJECT_CBC_ACTIVE.
  (7) In the _INJECT_STATE_ACTIVE state the waveform data is sent to the front end,
      ie. the injection is performed.
  (8) After the injection has finished the node will transition to the
      INJECT_SUCCESS to kill all streams if it was successful. Then it will
      jump back to the WAIT_FOR_NEXT_INJECT state to wait to perform the next
      injection.

Other states are for failures or waiting for external alerts.

Operating the Node
------------------

Operating procedures:
  * Update the schedule file.
  * Validate the schedule file after updating the schedule each time,
    the script is committed to: ../scripts/guardian_inj_validate_schedule.py
  * Reload the guardian node.
  * Request the INJECT_SUCESS state.
  * To cancel an active injection request KILL_INJECT.

To create the guardian node use the guardctrl command line tool, eg.
`guardctrl create INJ_TRANS; guardctrl start INJ_TRANS`.

To bring up the MEDM screen do `guardmedm INJ_TRANS`. To reload the schedule,
click the LOAD button. Then to put the node in operation request
the state INJECT_SUCCESS while in the WAIT_FOR_NEXT_INJECT state.

GraceDB Authentication
----------------------

Running this guardian node will require a robot certificate because the node
will upload events to GraceDB automatically. To get a robot certificate follow
the instructions at
https://wiki.ligo.org/viewauth/AuthProject/LIGOCARobotCertificate
and ask the GraceDB admins to add the subject line from the cert to the
grid-map file. Once you have that then set X509_USER_CERT and X509_USER_KEY in
the user env that the node runs under.

Note that robot certificates can expire and the node will no longer be
authenticated and at the time the robot certificate should be renewed.

2016 - Christopher M. Biwer
"""

import injtools
import os.path
import sys
import traceback
from gpstime import gpstime
from guardian import GuardStateDecorator

# name of channel to inject transient signals
model_name = "CAL-PINJX"
exc_channel_name = model_name + "_TRANSIENT_EXC"

# name of channel to write legacy tinj EPIC records
type_channel_name = model_name + "_TINJ_TYPE"
start_channel_name = model_name + "_TINJ_START"
end_channel_name = model_name + "_TINJ_ENDED"
outcome_channel_name = model_name + "_TINJ_OUTCOME"

# name of channel to check for external alerts
exttrig_channel_name = "CAL-INJ_EXTTRIG_ALERT_TIME"

# name of channel to check if detector is locked
lock_channel_name = "GRD-ISC_LOCK_OK"

# name of channel to check if intent mode on
obs_channel_name = "ODC-MASTER_CHANNEL_LATCH"

# bitmask to use to check if intent mode on this is AND'ed
# with obs_channel_name
obs_bitmask = 1

# seconds to wait after an external alert before performing injections again
exttrig_wait_seconds = 3600

# seconds to check for an imminent hardware injection
# eg. if set to 300 seconds then begin uploading to GraceDB and read
# waveform file 300 seconds in advance of hardware injection start time
imminent_seconds = 300

# maximum seconds in advance before jump to injection state
# eg. if set to 2 seconds then jump from AWG_STREAM_OPEN_PREINJECT to
# _INJECT_STATE_ACTIVE 2 seconds in advance of hardware injection start time
jump_to_inj_seconds = 20

# sample rate of excitation channel and waveform files
sample_rate = 16384

# path to schedule file
schedule_path = os.path.dirname(__file__) + "/schedule/schedule_1148558052.txt"

# read schedule
hwinj_list = injtools.read_schedule(schedule_path)

# a boolean that turns off code blocks to run guardian daemon for development
# at the dev_mode does the following:
#   * Does not check if the detector is locked in WAIT_FOR_NEXT_INJECT.
#   * Does not check if there is an external alert
dev_mode = False

# map injection states to GraceDB groups
gracedb_group_dict = {
    "INJECT_CBC_ACTIVE" : "CBC",
    "INJECT_BURST_ACTIVE" : "Burst",
    "INJECT_STOCHASTIC_ACTIVE" : "Stochastic",
    "INJECT_DETCHAR_ACTIVE" : "Burst",
}

def check_exttrig_alert(hwinj_list, failure_state):
    """ Create a GuardStateDecorator to check if there is an external alert.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.
    failure_state: str
        Name of the GuardState to jump transition to if there is an external
        alert found.

    Returns
    ----------
    check_exttrig_alert_decorator: GuardStateDecorator
        A GuardStateDecorator that checks for external alerts.
    """

    # in dev_mode do not check for external alerts
    if dev_mode:
        class check_exttrig_alert_decorator(GuardStateDecorator):
            pass
        return check_exttrig_alert_decorator

    class check_exttrig_alert_decorator(GuardStateDecorator):
        """ Decorator for GuardState that will check for an external alert.
        """

        def pre_exec(self):
            """ Do this before entering the GuardState.
            """

            # check if external alert within exttrig_wait_seconds seconds
            # in the past
            exttrig_alert_time = injtools.check_exttrig_alert(exttrig_channel_name,
                                                     exttrig_wait_seconds)
            if exttrig_alert_time:

                # if there is an external alert then close all streams
                try:
                    injtools.close_all_streams(hwinj_list)
                except:
                    etype, val, tb = sys.exc_info()
                    ftb = traceback.format_tb(tb)
                    for line in ftb: log(line)
                    log(str(etype) + " " + str(val))
                    return "FAILURE_TO_KILL_STREAM"

                return failure_state

    return check_exttrig_alert_decorator

def gracedb_post_inject_update(hwinj_list, text, label=None,
                               include_schedule_line=True):
    """ Create a GuardStateDecorator that will upload a message to the most
    recent GraceDB HardwareInjeciton event.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.
    text: str
        Text to upload to GraceDB event log.
    label: str
        Add a label to GraveDB event.

    Returns
    ----------
    gracedb_post_inject_update_decorator: GuardStateDecorator
        A GuardStateDecorator that will post a message to a GraceDB event log.
    """

    class gracedb_post_inject_update_decorator(GuardStateDecorator):
        """ Decorator for GuardState that will upload a message to GraceDB.
        """

        def pre_exec(self):
            """ Do this before entering the GuardState.
            """

            # get last hardware injection from schedule
            hwinj = injtools.get_last_injection(hwinj_list)

            # if no GraceDB ID found then go to failuire state
            if not hwinj:
                log("Could not find last injection.")
                return "FAILURE_TO_FIND_GRACEDB_ID"
            elif hwinj and not hwinj.gracedb_id:
                log("Could not find GraceDB ID.")
                return "FAILURE_TO_FIND_GRACEDB_ID"

            # upload message and label for GraceDB event
            try:
                injtools.gracedb_upload_message(hwinj.gracedb_id, text)
                if label:
                    injtools.gracedb_add_label(hwinj.gracedb_id, label)

                # if verbose
                if include_schedule_line:
                    line = " ".join(map(str, [hwinj.schedule_time,
                                              hwinj.schedule_state,
                                              hwinj.observation_mode,
                                              hwinj.scale_factor,
                                              hwinj.waveform_path,
                                              hwinj.metadata_path]))
                    injtools.gracedb_upload_message(hwinj.gracedb_id, line)

            # if an unexpected error was encountered then
            # jump to failure state
            except:
                etype, val, tb = sys.exc_info()
                ftb = traceback.format_tb(tb)
                for line in ftb: log(line)
                log(str(etype) + " " + str(val))
                return "FAILURE_ADDING_GRACEDB_MESSAGE"

    return gracedb_post_inject_update_decorator

def kill_all_streams(hwinj_list):
    """ Create a GuardStateDecorator that aborts all streams and resets the
    HardwareInjection.stream class attribute to None.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.

    Returns
    ----------
    kill_all_streams_decorator: GuardStateDecorator
        A GuardStateDecorator that aborts all streams.
    """

    class kill_all_streams_decorator(GuardStateDecorator):
        """ Decorator for GuardState that will aborts all streams and then
        resets them to None.
        """

        def pre_exec(self):
            """ Do this before entering the GuardState.
            """

            # close all streams
            try:
                injtools.close_all_streams(hwinj_list)
            except:
                etype, val, tb = sys.exc_info()
                ftb = traceback.format_tb(tb)
                for line in ftb: log(line)
                log(str(etype) + " " + str(val))
                return "FAILURE_TO_KILL_STREAM"

    return kill_all_streams_decorator

class INIT(injtools.HwinjGuardState):
    """ The INIT state is the first state entered when starting the Guardian
    daemon. It will run INIT.main once where there will be an edge transition.
    """

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    def main(self):
        """ Execute method once.
        """
        return True

class WAIT_FOR_NEXT_INJECT(injtools.HwinjGuardState):
    """ The WAIT_FOR_NEXT_INJECT state continuously loops checking for external
    alerts and if there is an imminent hardware injection.

    An imminment hardware injection is defined by imminent_seconds in
    seconds. If an imminent hardware injection is found then there will be a
    edge transition.

    An external alert will cause a jump transition to the EXTTRIG_ALERT_ACTIVE
    state if it is within exttrig_wait_seconds seconds.
    """

    # assign index for state
    index = 20

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @kill_all_streams(hwinj_list)
    def main(self):
        """ Execute method once.
        """
        return False

    @check_exttrig_alert(hwinj_list, "EXTTRIG_ALERT_ACTIVE")
    def run(self):
        """ Execute method in a loop.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)

        # if there is no imminent hardware injection then recheck injections
        if not self.hwinj:
            return False

        # in dev mode ignore if detector is locked
        # otherwise check if detector is locked
        if ezca[lock_channel_name] == 1 or dev_mode:

            # check if detector in desired observing mode and
            # then make a jump transition to CREATE_GRACEDB_EVENT state
            latch = ezca[obs_channel_name] & obs_bitmask
            if ( latch == 1 and self.hwinj.observation_mode == 1 ) or \
                    ( latch == 0 and self.hwinj.observation_mode == 0 ):

                # legacy of the old setup to set TINJ_START_TIME
                current_gps_time = gpstime.utcnow().gps()
                ezca[start_channel_name] = current_gps_time

                # set legacy TINJ_OUTCOME value for pending injection
                ezca[outcome_channel_name] = 0

                return True

            # set legacy TINJ_OUTCOME value for detector not in desired
            # observation mode
            else:
                log("Ignoring hardware injection since detector is not in " \
                    + "the desired observation mode.")
                ezca[outcome_channel_name] = -5

        # set legacy TINJ_OUTCOME value for detector not locked
        else:
            log("Ignoring hardware injection since detector is not locked.")
            ezca[outcome_channel_name] = -6

        return False

class EXTTRIG_ALERT_ACTIVE(injtools.HwinjGuardState):
    """ The EXTTRIG_ALERT_ACTIVE state continuously loops checking
    if the most recent external alert is not within exttrig_wait_seconds
    seconds. Once the external alert is far enough in the past there will be a
    jump transition to the WAIT_FOR_NEXT_INJECT state.
    """

    # assign index for state
    index = 30

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    def main(self):
        """ Execute method once.
        """
        return False

    def run(self):
        """ Execute method in a loop.
        """

        # check if not external alert
        exttrig_alert_time = injtools.check_exttrig_alert(exttrig_channel_name,
                                                 exttrig_wait_seconds)
        if not exttrig_alert_time:
            return True

        return False

class CHECK_SCHEDULE_TIMES(injtools.HwinjGuardState):
    """ The CHECK_SCHEDULE_TIMES state checks if two injections are too close
    together. This is a safeguard against a user not validating the schedule
    themselves.
    """

    # assign index for state
    index = 35

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    def main(self):
        """ Execute this method once.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        # get a sorted list of hardware injections by their start time
        sorted_hwinj_list = sorted(hwinj_list, key=lambda hwinj: hwinj.schedule_time)

        # if this is the first injection that will be performed then do check
        # otherwise continue because check would have already been done
        if self.hwinj.schedule_time == sorted_hwinj_list[0].schedule_time \
                and len(sorted_hwinj_list) > 1:

            # check that no two injections are too close together
            # this is a safeguard to do before an injection in case someone
            # did not validate the schedule
            for hwinj_1, hwinj_2 in zip(sorted_hwinj_list, sorted_hwinj_list[1:]):
                dt = hwinj_2.schedule_time - hwinj_1.schedule_time
                if dt > 0 and abs(dt) < imminent_seconds:
                    message = "Schedule has two injections %f seconds"%dt \
                        + " apart but must be at least %f"%imminent_seconds \
                        + " seconds apart"
                    log(message)
                    log("Injections are %s and %s"%(str(hwinj_1), str(hwinj_2)))
                    return "FAILURE_SCHEDULED_TWO_INJECT_TOO_CLOSE"

        # print statement
        else:
            log("Skipping checking schedule times since its already been done.")

        return True

class CREATE_GRACEDB_EVENT(injtools.HwinjGuardState):
    """ The CREATE_GRACEDB_EVENT state uploads a HardwareInjection entry
    to GraceDB.
    """

    # assign index for state
    index = 40

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @check_exttrig_alert(hwinj_list, "ABORT_INJECT_FOR_EXTTRIG")
    def main(self):
        """ Execute method once.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        # legacy of the old setup to set TINJ_TYPE
        tinj_type_dict = {
            "INJECT_CBC_ACTIVE" : 1,
            "INJECT_BURST_ACTIVE" : 2,
            "INJECT_DETCHAR_ACTIVE" : 3,
            "INJECT_STOCHASTIC_ACTIVE" : 4,
        }
        ezca[type_channel_name] = tinj_type_dict[self.hwinj.schedule_state]

        # try to upload an event to GraceDB
        try:

            # map injection state to GraceDB group
            group = gracedb_group_dict[self.hwinj.schedule_state]

            # log meta-data file path
            log("Reading meta-data from %s"%self.hwinj.metadata_path)

            # upload hardware injection to GraceDB
            self.hwinj.gracedb_id = injtools.gracedb_upload_injection(self.hwinj,
                                           [ezca.ifo], group=group)
            log("GraceDB ID is " + self.hwinj.gracedb_id)

        # if an unexpected error was encountered then jump to failure state
        except:
            etype, val, tb = sys.exc_info()
            ftb = traceback.format_tb(tb)
            for line in ftb: log(line)
            log(str(etype) + " " + str(val))
            return "FAILURE_CREATE_GRACEDB_EVENT"

        return True

class CREATE_AWG_STREAM(injtools.HwinjGuardState):
    """ The CREATE_AWG_STREAM state will create a awg.ArbitraryStream instance
    for the most imminent hardware injection. The stream can be called by
    the class attribute HardwareInjection.stream.
    """

    # assign index for state
    index = 50

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @check_exttrig_alert(hwinj_list, "ABORT_INJECT_FOR_EXTTRIG")
    def main(self):
        """ Execute method once.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        # create and open an ArbitraryStream for HardwareInjection
        # this is the object from the awg module that will control
        # the injection
        try:
            self.hwinj.create_stream(ezca.ifo + ":" + exc_channel_name, sample_rate)
        except:
            etype, val, tb = sys.exc_info()
            ftb = traceback.format_tb(tb)
            for line in ftb: log(line)
            log(str(etype) + " " + str(val))
            return "FAILURE_TO_CREATE_STREAM"

        return True

class READ_WAVEFORM(injtools.HwinjGuardState):
    """ The READ_WAVEFORM state reads the data from the waveform file and
    stores it as a HardwareInjection class attribute.
    """

    # assign index for state
    index = 60

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @check_exttrig_alert(hwinj_list, "ABORT_INJECT_FOR_EXTTRIG")
    def main(self):
        """ Execute method once.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        # legacy of the old setup to set TINJ_TYPE
        tinj_type_dict = {
            "INJECT_CBC_ACTIVE" : 1,
            "INJECT_BURST_ACTIVE" : 2,
            "INJECT_DETCHAR_ACTIVE" : 3,
            "INJECT_STOCHASTIC_ACTIVE" : 4,
        }
        ezca[type_channel_name] = tinj_type_dict[self.hwinj.schedule_state]

        # create a dict for formatting strings
        format_dict = {
            "ifo" : ezca.ifo,
        }

        # try to read waveform file
        try:
            log("Reading waveform data from %s"%self.hwinj.waveform_path.format(**format_dict))
            self.hwinj.data = self.hwinj.read_data(format_dict=format_dict)

        # if an unexpected error was encountered then jump to failure state
        except:
            etype, val, tb = sys.exc_info()
            ftb = traceback.format_tb(tb)
            for line in ftb: log(line)
            log(str(etype) + " " + str(val))
            return "FAILURE_READ_WAVEFORM"

        return True

class AWG_STREAM_OPEN_PREINJECT(injtools.HwinjGuardState):
    """ We open the stream with awg in advance of the start time of the
    injection. Therefore there is some time before the injection will begin.
    The AWG_STREAM_OPEN continuously checks the time, and for external alerts.
    Then once its time for the injection to begin there will be a jump
    transition to the specified _INJECT_STATE_ACTIVE subclass state.

    Having this state is a safe-guard against long upload times to GraceDB or
    reading large waveform files. If there is a FAILURE_INJECT_IN_PAST leading
    up to this state, you should try increasing the imminent_seconds variable.
    """

    # assign index for state
    index = 70

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    def main(self):
        """ Execute method once.
        """
 
        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        return False

    @check_exttrig_alert(hwinj_list, "ABORT_INJECT_FOR_EXTTRIG")
    def run(self):
        """ Execute method in a loop.
        """

        # notify operator
        notify("INJECTION IMMINENT: %f"%self.hwinj.schedule_time)

        # check if its time to jump to the corresponding _INJECT_STATE_ACTIVE subclass
        current_gps_time = gpstime.utcnow().gps()
        if current_gps_time > self.hwinj.schedule_time - jump_to_inj_seconds:
            return self.hwinj.schedule_state
        elif current_gps_time > self.hwinj.schedule_time:
            return "FAILURE_INJECT_IN_PAST"

        return False

class _INJECT_STATE_ACTIVE(injtools.HwinjGuardState):
    """ The _INJECT_STATE_ACTIVE state is a subclass that injects the signal
    into the detector. The stream is opened and data is sent in this state.
    The signal is injected using the awg.ArbitraryStream.close class function.

    The _INJECT_STATE_ACTIVE state will close the stream that already has
    the waveform data. This is when the injection is actually performed.

    This state is subclassed for a variety of injection types and will not
    appear in the state graph.
    """

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @check_exttrig_alert(hwinj_list, "ABORT_INJECT_FOR_EXTTRIG")
    def main(self):
        """ Execute method once.
        """

        # get hardware injection in the future that is soonest
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)
        notify("INJECTION ACTIVE: %f"%self.hwinj.schedule_time)
        if not self.hwinj: return "FAILURE_INJECT_IN_PAST"

        # close stream and perform injection
        # waits for injection to finish
        try:
            self.hwinj.stream.send(self.hwinj.data)
        except:
            etype, val, tb = sys.exc_info()
            ftb = traceback.format_tb(tb)
            for line in ftb: log(line)
            log(str(etype) + " " + str(val))
            return "FAILURE_DURING_ACTIVE_INJECT"

        # check if stream is open when it should be closed
        if self.hwinj.stream.opened:
            self.hwinj.stream.abort()
            return "FAILURE_AWG_STREAM_NOT_CLOSED"

        # explicitly record the data from the schedule file
        log("GPS start time: %f"%self.hwinj.schedule_time)
        log("Requested state: %s"%self.hwinj.schedule_state)
        log("Requested observation mode: %d"%self.hwinj.observation_mode)
        log("Scale factor: %f"%self.hwinj.scale_factor)
        log("Waveform path: %s"%self.hwinj.waveform_path)
        log("Meta-data path: %s"%self.hwinj.metadata_path)

        return True

class INJECT_CBC_ACTIVE(_INJECT_STATE_ACTIVE):
    """ The INJECT_CBC_ACTIVE state will perform a CBC hardware injection.
    """

    # assign index for state
    index = 101

class INJECT_BURST_ACTIVE(_INJECT_STATE_ACTIVE):
    """ The INJECT_BURST_ACTIVE state will perform a burst hardware injection.
    """

    # assign index for state
    index = 102

class INJECT_STOCHASTIC_ACTIVE(_INJECT_STATE_ACTIVE):
    """ The INJECT_STOCHASTIC_ACTIVE state will perform a stochastic
    hardware injection.
    """

    # assign index for state
    index = 103

class INJECT_DETCHAR_ACTIVE(_INJECT_STATE_ACTIVE):
    """ The INJECT_DETCHAR_ACTIVE state will perform a detector
     characterization hardware injection.
    """

    # assign index for state
    index = 104

class INJECT_SUCCESS(injtools.HwinjGuardState):
    """ The INJECT_SUCCESS state is an intermediary state for an injection
    that was successfully performed. There is a jump transition to the
    WAIT_FOR_NEXT_INJECT state.
    """

    # assign index for state
    index = 200

    @kill_all_streams(hwinj_list)
    @gracedb_post_inject_update(hwinj_list, "Injection was successful.", label="INJ")
    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for successful injection
        ezca[outcome_channel_name] = 1

        # legacy of the old setup to set TINJ_END_TIME
        current_gps_time = gpstime.utcnow().gps()
        ezca[end_channel_name] = current_gps_time

        return "WAIT_FOR_NEXT_INJECT"

class INJECT_KILL(injtools.HwinjGuardState):
    """ Request INJECT_KILL to end a currently running injection.
    The INJECT_KILL state will close all streams for all injections
    loaded from the schedule.
    """

    # assign index for state
    index = 210

    # determines if state appears on guardian MEDM screen dropdown menu
    request = True

    # automatically assign edges from every other state
    goto = True

    @kill_all_streams(hwinj_list)
    def main(self):
        """ Execute method once.
        """
        # set legacy TINJ_OUTCOME value for killed injection
        ezca[outcome_channel_name] = -11

        return False

    def run(self):
        """ Execute method in a loop.
        """
        return True

class ABORT_INJECT_FOR_EXTTRIG(injtools.HwinjGuardState):
    """  The ABORT_INJECT_FOR_EXTTRIG state is for a hardware injection that
    was aborted because of an external alert. It will make a jump transition
    to the EXTTRIG_ALERT_ACTIVE state.
    """

    # assign index for state
    index = 220

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @kill_all_streams(hwinj_list)
    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for failed injection
        ezca[outcome_channel_name] = -4

        # legacy of the old setup to set TINJ_END_TIME
        current_gps_time = gpstime.utcnow().gps()
        ezca[end_channel_name] = current_gps_time

        return True

class _INJECT_FAILURE(injtools.HwinjGuardState):
    """ The _INJECT_FAILURE state is for a hardware injection that
    was not successfully performed because of an unexpected error.

    The guardian node should remain in the _INJECT_FAILURE state
    unless the operator has requested another state.

    This state is subclassed for a variety of failures and will not appear
    in the state graph.
    """

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @kill_all_streams(hwinj_list)
    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for failed injection
        ezca[outcome_channel_name] = -4

        # legacy of the old setup to set TINJ_END_TIME
        current_gps_time = gpstime.utcnow().gps()
        ezca[end_channel_name] = current_gps_time

        return False

    def run(self):
        """ Execute method in a loop.
        """

        # notify operator
        notify("ERROR")

        return False

class _INJECT_FAILURE_GRACEDB(injtools.HwinjGuardState):
    """ This is an internal sate that kills all streams after an error
    occurred uploading an event to GraceDB.
    """

    # determines if state appears on guardian MEDM screen dropdown menu
    request = False

    @kill_all_streams(hwinj_list)
    def main(self):
        """ Execute method once.
        """

        # set legacy TINJ_OUTCOME value for failed injection
        ezca[outcome_channel_name] = -4

        # legacy of the old setup to set TINJ_END_TIME
        current_gps_time = gpstime.utcnow().gps()
        ezca[end_channel_name] = current_gps_time

        return False

    def run(self):
        """ Execute method in a loop.
        """

        # notify operator
        notify("ERROR")

        return False

class FAILURE_CREATE_GRACEDB_EVENT(_INJECT_FAILURE_GRACEDB):
    """ The FAILURE_CREATE_GRACEDB_EVENT state is for an unexpected error while
    uploading an event to GraceDB.
    """

    # assign index for state
    index = 230

class FAILURE_TO_FIND_GRACEDB_ID(_INJECT_FAILURE_GRACEDB):
    """ The FAILURE_TO_FIND_GRACEDB_ID state indicates that the guardian state
    could not find the GraceDB ID of the hardware injection.

    For debugging purposes GraceDB IDs are stored as a class attribute
    HardwareInjection.gracedb_id.
    """

    # assign index for state
    index = 231

class FAILURE_ADDING_GRACEDB_MESSAGE(_INJECT_FAILURE_GRACEDB):
    """ The FAILURE_ADDING_GRACEDB_MESSAGE state indicates that there was
    an error uploading a message to GraceDB.

    For debugging purposes check that you can ping GraceDB.
    """

    # assign index for state
    index = 232

class FAILURE_READ_WAVEFORM(_INJECT_FAILURE):
    """ The FAILURE_READ_WAVEFORM state is for an unexpected error while
    reading the waveform file.
    """

    # assign index for state
    index = 240

class FAILURE_INJECT_IN_PAST(_INJECT_FAILURE):
    """ The FAILURE_INJECT_IN_PAST state is a state used to log
    when a hardware injection was aborted because the scheduled
    injection has already past in time before the guardian node
    was able to transition to the _INJECT_STATE_ACTIVE to perform the
    injection.

    This is a safeguard. The schedule validation script should be
    run whenever updating the schedule file.
    """

    # assign index for state
    index = 250

class FAILURE_AWG_STREAM_NOT_CLOSED(_INJECT_FAILURE):
    """ The FAILURE_AWG_STREAM_NOT_CLOSED state indicates that after performing
    the injection, that awg did not close the stream when it should have.
    """

    # assign index for state
    index = 280

class FAILURE_DURING_ACTIVE_INJECT(_INJECT_FAILURE):
    """ The FAILURE_DURING_ACTIVE_INJECT state indicates that
    the call to awg.ArbitraryStream.close failed.
    """

    # assign index for state
    index = 300

class FAILURE_SCHEDULED_TWO_INJECT_TOO_CLOSE(_INJECT_FAILURE):
    """ The FAILURE_SCHEDULED_TWO_INJECT_TOO_CLOSE state indicates that
    the schedule file has two injections that are too close together.
    """

    # assign index for state
    index = 310

# define directed edges that connect guardian states
edges = (
    # these are edges for starting the node
    ("INIT", "WAIT_FOR_NEXT_INJECT"),
    # edge for killing injection
    ("INJECT_KILL", "WAIT_FOR_NEXT_INJECT"),
    # edges that happen before a successful injection
    ("WAIT_FOR_NEXT_INJECT", "CHECK_SCHEDULE_TIMES"),
    ("CHECK_SCHEDULE_TIMES", "CREATE_GRACEDB_EVENT"),
    ("CREATE_GRACEDB_EVENT", "CREATE_AWG_STREAM"),
    ("CREATE_AWG_STREAM", "READ_WAVEFORM"),
    ("READ_WAVEFORM", "AWG_STREAM_OPEN_PREINJECT"),
    ("AWG_STREAM_OPEN_PREINJECT", "INJECT_CBC_ACTIVE"),
    ("AWG_STREAM_OPEN_PREINJECT", "INJECT_BURST_ACTIVE"),
    ("AWG_STREAM_OPEN_PREINJECT", "INJECT_STOCHASTIC_ACTIVE"),
    ("AWG_STREAM_OPEN_PREINJECT", "INJECT_DETCHAR_ACTIVE"),
    # edges that happen after a successful injection
    ("INJECT_CBC_ACTIVE", "INJECT_SUCCESS"),
    ("INJECT_BURST_ACTIVE", "INJECT_SUCCESS"),
    ("INJECT_STOCHASTIC_ACTIVE", "INJECT_SUCCESS"),
    ("INJECT_DETCHAR_ACTIVE", "INJECT_SUCCESS"),
    # edge for external alerts
    ("ABORT_INJECT_FOR_EXTTRIG", "EXTTRIG_ALERT_ACTIVE"),
    ("EXTTRIG_ALERT_ACTIVE", "WAIT_FOR_NEXT_INJECT"),
    # edges for failures
    ("FAILURE_CREATE_GRACEDB_EVENT", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_TO_FIND_GRACEDB_ID", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_ADDING_GRACEDB_MESSAGE", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_READ_WAVEFORM", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_INJECT_IN_PAST", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_AWG_STREAM_NOT_CLOSED", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_DURING_ACTIVE_INJECT", "WAIT_FOR_NEXT_INJECT"),
    ("FAILURE_SCHEDULED_TWO_INJECT_TOO_CLOSE", "WAIT_FOR_NEXT_INJECT"),
)

