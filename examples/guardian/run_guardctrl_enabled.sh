#! /bin/bash

# requests the ENABLED state
guardctrl request ENABLED INJ

# wait a moment or else it will be too fast and Guardian
# will miss the jump transition to ENABLED
sleep 4

# remove the request for ENABLED and the daemon should
# automatically move to the IDLE state
guardctrl request NONE INJ

