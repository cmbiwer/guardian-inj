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
