#! /usr/bin/python

import logging
from ezca import Ezca
from guardian import GuardState, NodeManager
from inspect import currentframe
from time import sleep

# name of the model
prefix = 'CAL-INJ'

class SAFE(GuardState):

    # automatically assign edges from every other state
    goto = True

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''
        pass

class STATE1(GuardState):

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''

        # print state
        class_name = type(self).__name__
        func_name = currentframe().f_code.co_name
        logging.info('Executing method %s.%s', class_name, func_name)

        # wait
        wait_time = 2
        timer_name = 'timer_wait'
        logging.info('Wil wait %d seconds', wait_time)
        self.timer[timer_name] = wait_time
        while not self.timer[timer_name]:
            pass

        # read an EPICS channel
        ezca = Ezca(prefix)
        epics_str = 'TINJ_PAUSE'
        epics_val = ezca.read(epics_str)
        logging.info('The value of %s is %f',
            ezca.prefix+epics_str, epics_val) 

        # check a filter module is engaged in a filterbank
        fbank_name = 'TRANSIENT'
        fbank_module = 'FM1'
        fbank = ezca.get_LIGOFilter(fbank_name)
        tmp = fbank.is_engaged(fbank_module)
        logging.info('%s %s is engaged is %s',
            fbank.ezca.prefix+fbank.filter_name, fbank_module, tmp)

        # if a state method returns a string it is
        # interpreted as a state name (ie. jump transition)
        return 'STATE2'


class STATE2(GuardState):

    def main(self):
        ''' Executate method once.
        '''
        pass

    def run(self):
        ''' Execute method in a loop.
        '''
        pass

# edges between states as a tuple (FROM_STATE, TO_STATE)
edges = [
    ('SAFE', 'STATE1'),
]

# initialize log
logging_level = logging.DEBUG
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging_level)

# initialize state object
state = STATE1()

# execute main method
state.main()

# execute run method in a loop
while True:
    status = state.run()
    if status not in [None, False]:
        break

