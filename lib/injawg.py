# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ awg guardian module

This module calls awg to inject a signal.
"""

from awg import ArbitraryLoop

def awg_inject(channel_name, timeseries, gps_start_time,
               sample_rate, scale_factor=1.0, ramptime=0):
    """ None.
    """

    awg_exc = ArbitraryLoop(channel_name, timeseries, scale=scale_factor,
                            rate=sample_rate, start=gps_start_time)
    awg_exc.start(ramptime=ramptime, wait=True)
    awg_exc.stop()

    return 0
