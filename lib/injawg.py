from awg import ArbitraryLoop

def awg_inject(channel_name, timeseries, gps_start_time,
               sample_rate, ramptime=0):
    """ None.
    """

    awg_exc = ArbitraryLoop(chan, timeseries, scale=scale_factor,
                            rate=sample_rate, start=gps_start_time)
    awg_exc.start(ramptime=ramptime, wait=True)
    awg_exc.stop()

    return 0
