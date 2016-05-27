# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ types guardian module

This module provides class for managing hardware injections.

2016 - Christopher M. Biwer
"""

import awg
import inj_io
import numpy
import os.path
from gpstime import gpstime
from guardian import GuardState

class HwinjGuardState(GuardState):
    """ A subclass of the guardian GuardState that has a hwinj class attribute.
    This is hwinj class attribute is used to keep track of the active
    injection in the GuardState.

    A convenient method to find the most imminent hardware injection is:
        self.hwinj = injtools.check_imminent_injection(hwinj_list, imminent_seconds)

    A convient method to find the most recent hardware injection is:
        self.hwinj = injtools.check_last_injection(hwinj_list, look_back_seconds)

    Its default value is None, indicating that there is no injection. If there
    is an injection, it should be a HardwareInjection instance.
    """
    hwinj = None

class HardwareInjection(object):
    """ A class representing a single hardware injection.
    """

    def __init__(self, schedule_time, schedule_state, observation_mode,
                 scale_factor, waveform_path, metadata_path):

        self.schedule_time = float(schedule_time)
        self.schedule_state = schedule_state
        self.observation_mode = int(observation_mode)
        self.scale_factor = float(scale_factor)
        self.waveform_path = waveform_path
        self.metadata_path = metadata_path
        self.stream = None
        self.data = None
        self.gracedb_id = None

    def __repr__(self):
        """ String representation of instance.
        """
        return "<" + " ".join(map(str, [self.schedule_time, self.schedule_state])) + " HardwareInjection>"

    @property
    def waveform_start_time(self):
        """ Returns the GPS start time of the waveform. This assumes that
        the waveform file has the following format:

            IFO-TAG-GPS_START_TIME-DURATION.EXT

        Where IFO is the observatory, TAG is an arbitrary string that does not
        contain "-", GPS_START_TIME is the start time of the waveform file,
        DURATION is the length in seconds of the waveform file, and EXT is
        an arbitrary file extension.

        Returns
        ----------
        waveform_start_time: float
            Start time of the waveform file.
        """

        # get waveform file name
        filename = os.path.basename(self.waveform_path)

        # parse filename and get start time of waveform file
        waveform_start_time = filename.split("-")[-2]

        return float(waveform_start_time)

    def create_stream(self, channel_name, sample_rate):
        """ Creates an ArbitraryStream instance for the HardwareInjection. The
        ArbitraryStream is accessible with the self.stream attribute.

        Parameters
        ----------
        channel_name: str
            Name of excitation channel to inject signal.
        sample_rate: int
            Sample rate of the time series and excitation channel.
        """

        # call awg to create a stream
        self.stream = awg.ArbitraryStream(channel_name, rate=sample_rate,
                                          start=self.schedule_time)

    def read_data(self, format_dict=None):
        """ Reads waveform data.

        format_dict: dict
            A dict to be used with python built-in string formatting.
        """

        # read waveform file
        if format_dict is not None:
            path = self.waveform_path.format(**format_dict)
        else:
            path = self.waveform_path
        return inj_io.read_waveform(path)

def check_imminent_injection(hwinj_list, imminent_wait_time):
    """ Find the most imminent hardware injection, this is the injection in the
    future that is soonest to the current GPS time. The injection must
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
    current_gps_time = gpstime.utcnow().gps()

    # find the injection in the future and soonest to the present
    if len(hwinj_list):
        imminent_hwinj = min(hwinj_list,
                             key=lambda hwinj: hwinj.schedule_time-current_gps_time \
                                 if hwinj.schedule_time-current_gps_time > 0 else float("inf"))
        if imminent_hwinj.schedule_time-current_gps_time < imminent_wait_time \
                      and imminent_hwinj.schedule_time-current_gps_time > 0:
            return imminent_hwinj
    return None

def get_last_injection(hwinj_list):
    """ Find the most recent hardware injection, this is the injection that is
    in the past and closest to the current GPS time. The injection must be
    within look_back_seconds for it to be returned.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.

    Retuns
    ----------
    recent_hwinj: HardwareInjection
        A HardwareInjection instance is return if there is a recent
        injection found.
    """

    # get the current GPS time
    current_gps_time = gpstime.utcnow().gps()

    # find the injection in the past and most recent
    if len(hwinj_list):
        recent_hwinj = min(hwinj_list,
                           key=lambda hwinj: abs(hwinj.schedule_time-current_gps_time) \
                               if hwinj.schedule_time-current_gps_time < 0 else float("inf"))
        if recent_hwinj.schedule_time-current_gps_time < 0:
            return recent_hwinj
    return None

def close_all_streams(hwinj_list):
    """ Run abort and close for all streams.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.
    """

    # close all streams
    for hwinj in hwinj_list:
        hwinj.data = None
        if hwinj.stream is not None:
            hwinj.stream.abort()
            hwinj.stream.close()
            hwinj.stream = None
