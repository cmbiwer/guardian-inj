# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ awg guardian module

This module calls awg to inject a signal.

2016 - Christopher M. Biwer
"""

from awg import ArbitraryLoop

def awg_inject(channel_name, timeseries, gps_start_time,
               sample_rate, scale_factor=1.0, ramp_time=0):
    """ Injects a time series into channel.

    Parameters
    ----------
    channel_name: str
        Name of excitation channel to inject signal.
    timeseries: numpy.array
        Array with the time series to be injected.
    gps_start_time: float
        GPS start time of the injection.
    sample_rate: int
        Sample rate of the time series and excitation channel.
    scale_factor: float
        Factor that will be multipled to the time series before injection.
    ramp_time: str
        Time to ramp up the signal.
    """

    # call awg and inject the time series
    awg_exc = ArbitraryLoop(channel_name, timeseries, scale=scale_factor,
                            rate=sample_rate, start=gps_start_time)
    awg_exc.start(ramptime=ramp_time, wait=True)
    awg_exc.stop()

