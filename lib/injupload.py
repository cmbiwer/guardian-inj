# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

'''
INJ GraceDB module

This defines how to upload injections to GraceDB.
'''

from glue.ligolw import ligolw, lsctables, table, utils

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

