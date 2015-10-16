# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ base guardian module

This defines the behavior for all transient injections.
'''

##################################################
# IMPORTS
##################################################

# cannot use glue module yet

import logging
import ligo.gracedb.rest as gracedb_rest
from ezca import Ezca
from glue.ligolw import ligolw, lsctables, table, utils
from gpstime import gpstime
from guardian import GuardState
from os.path import basename
from time import sleep

##################################################
# VARIABLES
##################################################

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_time = 2

# seconds before injection to call awgstream
awgstream_time = 300

# full path to schedule file
path_schedule = '/ligo/home/christopher.biwer/src/fake_schedule'

# sample rate of excitation channel and waveform files
sample_rate = 16384

# list of IFOs
ifo_list = ['H1', 'L1']

##################################################
# FUNCTIONS
##################################################

def validate_schedule():
    ''' Validate formatting of schedule file.
    '''
    pass

def read_schedule():
    ''' Parses schedule and returns rows.
    '''

    # initialize empty list to store injections
    injection_list = []

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # open schedule file and add the injections to the list
    with open(path_schedule, 'rb') as fp:
        lines = fp.readlines()
        for line in lines:
            scheduled_time, injection_type, scale_factor, path = line.split()
            injection = Injection(scheduled_time, injection_type, scale_factor, path)

            # add injection to list if its in the future
            if injection.scheduled_time-current_gps_time > 0:
                injection_list.append(injection)

    return injection_list

def check_injections_enabled():
    ''' Check that injections are enabled.
    '''

    # check if injections enabled
    tinj_enable = ezca.read('TINJ_ENABLE')
    print 'The value of %s is %f'%(ezca.prefix+'TINJ_ENABLE', tinj_enable)

    # check if electromagnetic alert
    exttrig_alert_time = ezca.read('EXTTRIG_ALERT_TIME')
    print 'The value of %s is %f'%(ezca.prefix+'EXTTRIG_ALERT_TIME', exttrig_alert_time)

    # get the current GPS time
    current_gps_time = gpstime.tconvert('now').gps()

    # if injections enabled and no electromangetic alert return True
    if tinj_enable and (current_gps_time - exttrig_alert_time > awgstream_time):
        return True

    # else return False
    else:
        return False

def check_injections_imminent(injection_list):
    ''' Check for an imminent injection.
    '''

    # find most imminent injection
    if len(injection_list):
        imminent_injection = min(injection_list, key=lambda x: x.scheduled_time-current_gps_time)
    else:
        return None

    # if most imminent injection is within time to call awgstream then return that injection
    if imminent_injection.scheduled_time-current_gps_time > awgstream_time:
        return imminent_injection
    else:
        return None

def check_detector_enabled():
    ''' Check that the detector is in observation mode.
    '''
    pass

def check_filterbank_status():
    ''' Check that filterbank is ON.
    '''
    pass

def validate_xml_file():
    ''' Validate formatting of LIGOLW XML file.
    '''
    pass

def upload_gracedb_event(injection):
    ''' Uploads an event to GraceDB.
    '''

    # begin GraceDB API
    client = gracedb_rest.GraceDb()

    # read XML file
    inspiral_xml = utils.load_filename(injection.path,
        contenthandler=ContentHandler)

    # get first sim inspiral row
    sim_table = table.get_table(inspiral_xml,
        lsctables.SimInspiralTable.tableName)
    sim = sim_table[0]

    # check if times need to be changed in XML file
    if injection.scheduled_time:

        # get geocentric end time
        dt = sim.geocentric_end_time - injection.scheduled_time
        sim.gencentric_end_time = injection.scheduled_time + dt

        # get H1 end time
        dt = sim.h_end_time - injection.scheduled_time
        sim.h_end_time = injection.scheduled_time + dt

        # get L1 end time
        dt = sim.l_end_time - injection.scheduled_time
        sim.l_end_time = injection.scheduled_time + dt

    # get XML content as a str
    fp = tempfile.NamedTemporaryFile()
    xmldoc.write(fp)
    filecontents = fp.seek(0).read()
    fp.close()

    # loop over IFOs
    for ifo in ifo_list:

        # get GraceDB inputs for injection type
        group = 'Test'
        pipeline = 'HardwareInjection'
        filename = injection.path

        # upload event to GraceDB
        out = client.createEvent(group, pipeline, filename,
            filecontents=filecontents, insturment=ifo,
            source_channel='', destination_channel='')
        graceid = out.json()['graceid']

        # add URL to waveform and parameter files
        waveform_url = 'FIXME'
        parameter_url = basename(filename)
        message  = ''
        message += '<a href='+waveform_url+'>waveform file</a>'
        message += '<br>'
        message += '<a href='+parameter_url+'>original XML parameter file</a>'
        out2 = client.writeLog(graceid, message, tagname='analyst comments')


def external_call():
    ''' Make an external call on the command line.
    '''
    pass

##################################################
# OBJECTS
##################################################

class InjectionList(list):

    def __init__(self):
        self.imminient_injection = None

class Injection(object):
    ''' A class representing a single injection.
    '''

    def __init__(self, scheduled_time, injection_type,
                     scale_factor, path):

        self.scheduled_time = float(scheduled_time)
        self.injection_type = injection_type
        self.scale_factor = float(scale_factor)
        self.path = path

##################################################
# STATES
##################################################

class INIT(GuardState):
    ''' State that is first entered when starting Guardian daemon.
    '''

    def main(self):
        ''' Executate method once.
        '''

        # initialize log
        #logging_level = logging.WARN
        #logging.basicConfig(file='INJ.log', format='%(asctime)s : %(message)s', level=logging_level)

        # setup EPICS reading and writing
        ezca = Ezca(prefix)

        # setup content handler for LIGOLW XML
        @lsctables.use_in
        class ContentHandler(ligolw.LIGOLWContentHandler):
            pass

        return 'DISABLED'

    def run(self):
        ''' Execute method in a loop.
        '''

        return 'DISABLED'

class DISABLED(GuardState):
    ''' State for when injections are disabled. Either manually
    or from an electromagnetic alert.
    '''

    # automatically assign edges from every other state
    goto = True

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # if injections are enabled then move to IDLE state
        injections_enabled = check_injections_enabled()
        if injections_enabled:
            return 'IDLE'
        else:
            sleep(sleep_time)

class IDLE(GuardState):
    ''' State when the schedule is continously checked for injections.
    If an injection is imminent then the state will change to that
    injection type.
    '''

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # wait some set amount of time
        sleep(sleep_time)

        # read schedule
        injection_list = read_schedule()
        print 'There are ', len(injection_list), 'injections in the future'

        # check if injection is imminent
        imminent_injection = check_injections_imminent(injection_list)
        if imminent_injection:
            print 'Injection imminent', imminent_injection.scheduled_time
        else:
            print 'No injection imminent' 
            return 'IDLE'

        # if injections are disabled then move to DISABLED state
        injections_enabled = check_injections_enabled()
        if not injections_enabled: 
            return 'DISABLED'

        # if detector is in observation mode then change to injection-type state
        detector_enabled = check_detector_enabled()
        if not detector_enabled:
            print 'Detector is not in observation mode'
            return 'IDLE'
        else:
            return imminent_injection.injection_type

class CBC(GuardState):
    ''' State for performing a CBC injection.
    '''

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # read schedule

        # print information about injections (total num, future inj)

        # check if injection is imminent

        # print if injection is imminent

        # get full path to injection file

        # get injection type

        # if injections enabled and no electromangetic alert go to DISABLED state

        # if detector is locked and intent bit is on then continue

        # upload GraceDB hardware injection event

        # call awgstream

        # check that awgstream completed

        pass

##################################################
# EDGES
##################################################

# define directed edges that connect guardian states
edges = (
    ('INIT', 'DISABLED'),
    ('DISABLED', 'IDLE'),
    ('IDLE', 'CBC'),
)

