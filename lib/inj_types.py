# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

"""
INJ types guardian module

This module provides class for managing hardware injections.
"""

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

    def __repr__(self):
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

