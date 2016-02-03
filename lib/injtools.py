from gpstime import gpstime
from subprocess import Popen, PIPE

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

def read_schedule(schedule_path):
    """ Parses schedule file.

    Parameters
    ----------
    schedule_path: str
        Path to the schedule file.

    Returns
    ----------
    inj_list: list
        A list where each element is an HardwareInjection instance.
    """

    # initialize empty list to store HardwareInjection
    hwinj_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert("now").gps()

    # read lines of schedule file
    fp = open(schedule_path, "rb")
    lines = fp.readlines()
    fp.close()

    # loop over lines in schedule file
    for line in lines:

        # get line in schedule as a list of strings
        data = line.split()

        # parse line
        i = 0
        schedule_time = float(data[i]); i += 1
        schedule_state = data[i]; i += 1
        observation_mode = int(data[i]); i+= 1
        scale_factor = float(data[i]); i += 1
        waveform_path = data[i]; i += 1
        metadata_path = data[i]; i += 1

        # add a new HardwareInjection to list if its in the future
        if schedule_time - current_gps_time > 0:
            hwinj = HardwareInjection(schedule_time, schedule_state,
                                      observation_mode, scale_factor,
                                      waveform_path, metadata_path)
            hwinj_list.append(hwinj)

    return hwinj_list

def check_imminent_injection(hwinj_list, imminent_wait_time):
    """ Find the most imminent hardware injection.

    Parameters
    ----------
    hwinj_list: list
        A list of HardwareInjection instances.

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
        If external alert within wait period then return the GPS time of the alert.
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

def make_external_call(cmd_list, stdout=PIPE, stderr=PIPE, shell=False):
    """ Make an external call on the command line.

    Parameters
    ----------
    cmd_list: list
        A list where the elements are the command line arguments.
    stdout: object
        Where to write stdout.
    stderr: object
        Where to write stderr.
    shell: boolean
        If True then execute external call through the shell.

    Retuns
    ----------
    process.returncode: int
        The exit code of the external call.
    """

    # run command
    cmd_list = map(str, cmd_list)
    cmd_str = " ".join(cmd_list)
    process = Popen(cmd_list, shell=shell,
                  stdout=stdout, stderr=stderr)

    # get standard output and standard error
    stdout, stderr = process.communicate()

    return process.returncode








