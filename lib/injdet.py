# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ tools guardian module

This module provides functions performing checks on detector data.
"""

from gpstime import gpstime

def check_imminent_injection(hwinj_list, imminent_wait_time):
    """ Find the most imminent hardware injection. The injection must
    be within imminent_wait_time for it to be considered imminent.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.
    imminent_wait_time: float
        Seconds to check from current time to determine if a hardware
        injection is imminent.

    Retuns
    ----------
    imminent_hwinj: HardwareInjection
        A HardwareInjection instance is return if there is an imminent
        injection found.
    """

    # get the current GPS time
    current_gps_time = gpstime.tconvert("now").gps()

    # find most imminent injection
    if len(hwinj_list):
        imminent_hwinj = min(hwinj_list, key=lambda hwinj: hwinj.schedule_time-current_gps_time)
        if imminent_hwinj.schedule_time-current_gps_time < imminent_wait_time \
                      and imminent_hwinj.schedule_time-current_gps_time > 0:
            return imminent_hwinj
    return None

def check_exttrig_alert(exttrig_channel_name, exttrig_wait_time):
    """ Check if there is an external trigger alert.

    Parameters
    ----------
    exttrig_channel_name: str
        Name of the EPICs record channel to check for most recent alert time.
    exttrig_wait_time: float
        Amount of time to wait for an external alert.

    Retuns
    ----------
    exttrig_alert_time: float
        If external alert within wait period then return the GPS time of
        the alert.
    """

    # get the current GPS time
    current_gps_time = gpstime.tconvert("now").gps()

    # read EPICs record for most recent external trigger alert GPS time
    exttrig_alert_time = ezca.read(exttrig_channel_name)

    # if alert is within wait period then return the GPS time
    if abs(current_gps_time - exttrig_alert_time) < exttrig_wait_time:
        return exttrig_alert_time
    else:
        return None

