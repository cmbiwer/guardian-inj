# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ GraceDB module

This defines how to upload injections to GraceDB.
'''

##################################################
# IMPORTS
##################################################

import tempfile
import ligo.gracedb.rest as gracedb_rest
from glue.ligolw import ligolw, lsctables, table, utils

# setup content handler for LIGOLW XML
@lsctables.use_in
class ContentHandler(ligolw.LIGOLWContentHandler):
    pass

##################################################
# VARIABLES
##################################################

# URL to injection SVN that contains waveform files
injection_svn_url = 'https://daqsvn.ligo-la.caltech.edu/svn/injection/hwinj/Details/'

##################################################
# FUNCTIONS
##################################################

def upload_gracedb_event(inj):
    ''' Uploads an event to GraceDB.
    '''

    # begin GraceDB API
    client = gracedb_rest.GraceDb()

    # read XML file
    xmldoc = utils.load_filename(inj.metadata_path,
        contenthandler=ContentHandler)

    # get first sim inspiral row
    sim_table = table.get_table(xmldoc,
        lsctables.SimInspiralTable.tableName)
    sim = sim_table[0]

    # get geocentric end time
    dt = sim.geocent_end_time - inj.scheduled_time
    sim.geocent_end_time = inj.scheduled_time + dt

    # get H1 end time
    dt = sim.h_end_time - inj.scheduled_time
    sim.h_end_time = inj.scheduled_time + dt

    # get L1 end time
    dt = sim.l_end_time - inj.scheduled_time
    sim.l_end_time = inj.scheduled_time + dt

    # get XML content as a str
    fp = tempfile.NamedTemporaryFile()
    xmldoc.write(fp)
    fp.seek(0)
    filecontents = fp.read()
    fp.close()

    # get GraceDB inputs for inj type
    group = 'Test'
    pipeline = 'HardwareInjection'
    filename = inj.metadata_path
    ifo = ezca.ifo

    # upload event to GraceDB
    out = client.createEvent(group, pipeline, filename,
        filecontents=filecontents, insturment=ifo,
        source_channel='', destination_channel='')
    graceid = out.json()['graceid']

    # add URL to waveform and parameter files
    waveform_url = injection_svn_url + '/Inspiral/' + ifo + '/' + basename(inj.waveform_path)
    metadata_url = injection_svn_url + '/Inspiral/' + basename(inj.metadata_path)
    message  = ''
    message += '<a href='+waveform_url+'>waveform file</a>'
    message += '<br>'
    message += '<a href='+metadata_url+'>original XML parameter file</a>'
    out2 = client.writeLog(graceid, message, tagname='analyst comments')

