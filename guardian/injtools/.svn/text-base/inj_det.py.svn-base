# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ detector guardian module

This module provides functions performing checks on detector data.

2016 - Christopher M. Biwer
"""

from gpstime import gpstime

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
    current_gps_time = gpstime.utcnow().gps()

    # read EPICs record for most recent external trigger alert GPS time
    exttrig_alert_time = ezca.read(exttrig_channel_name)

    # if alert is within wait period then return the GPS time
    if abs(current_gps_time - exttrig_alert_time) < exttrig_wait_time:
        return exttrig_alert_time
    else:
        return None

