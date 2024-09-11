""" ============ Begin - globals.py (No changes) ============ """
#!/usr/bin/env python

# Do we want verbose logging
verbose = True

# Are we runing within the unit tests
isunittests = False

# For iocIsBorn.py
# New format indicator
formatIndicator = '# FORMAT='

# screeniocs formatting version
format = 1


class UserParamsException(Exception):
    '''Raised when there is an error in the parameters passed into the utility (like a missing IOC argument).
    Code raising this exception is expected to provide a easily understandable message as to why the parameters are inadequate.
    The controllers catch this exception and print only the message - unless we have verbose on in which case we let it thru to get a stack trace'''
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return self.value
""" ============ End - globals.py ============ """