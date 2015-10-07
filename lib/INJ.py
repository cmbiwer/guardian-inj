import logging
from ezca import Ezca
from guardian import GuardState
from time import sleep

# name of module
prefix = 'CAL-INJ'

# seconds to sleep after an operation
sleep_seconds = 2

class INIT(GuardState):

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # print statement
        print 'INIT'

        # sleep
        sleep(sleep_seconds)

        return 'DISABLED'

class DISABLED(GuardState):

    # automatically assign edges from every other state
    goto = True

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # check if injections disabled or an electromagnetic alert
        ezca = Ezca(prefix)
        epics_str = 'TINJ_ENABLE'
        epics_val = ezca.read(epics_str)
        print 'The value of %s is %f'%(ezca.prefix+epics_str, epics_val)

        # sleep
        sleep(sleep_seconds)

class IDLE(GuardState):

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''
        pass

class CBC(GuardState):

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''
        pass

# initialize log
logging_level = logging.WARN
logging.basicConfig(file='INJ.log', format='%(asctime)s : %(message)s', level=logging_level)
