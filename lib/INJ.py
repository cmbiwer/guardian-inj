import logging
from ezca import Ezca
from gpstime import gpstime
from guardian import GuardState
from time import sleep

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_time = 2

# seconds to check for electromagnetic alert
exttrig_wait_time = 300

class INIT(GuardState):
    ''' State that is first entered when starting Guardian daemon.
    '''

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # print statement
        print 'INIT'

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

        # setup EPICS reading and writing
        ezca = Ezca(prefix)

        # get the current GPS time
        current_gps_time = gpstime.tconvert('now').gps()

        # check if injections enabled
        tinj_enable = ezca.read('TINJ_ENABLE')
        print 'The value of %s is %f'%(ezca.prefix+'TINJ_ENABLE', tinj_enable)

        # check if electromagnetic alert
        exttrig_alert_time = ezca.read('EXTTRIG_ALERT_TIME')
        print 'The value of %s is %f'%(ezca.prefix+'EXTTRIG_ALERT_TIME', exttrig_alert_time)

        # if injections enabled and no electromangetic alert go to IDLE state
        if tinj_enable and current_gps_time - exttrig_alert_time > exttrig_wait_time:
            return 'IDLE'

        # else sleep
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

        # print statement
        print 'IDLE'

        # sleep
        sleep(sleep_time)

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
        pass

# initialize log
#logging_level = logging.WARN
#logging.basicConfig(file='INJ.log', format='%(asctime)s : %(message)s', level=logging_level)
