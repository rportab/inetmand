#!/usr/bin/env python
"""RunPON - runs pon/poff scripts and shows the running time.
    http://erlug.linux.it/~da/soft/runpon/

    Copyright (C) 2009 Davide Alberani <da@erlug.linux.it>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import logging
import subprocess
import configparser
import warnings
from collections import defaultdict
import shlex

__version__ = VERSION = '0.5'


# If True, it doesn't execute any command.
DONT_RUN = False
#DONT_RUN = True
# Logging facility.
_LOGGING_LEVELS = {'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG}
#logging.basicConfig(level=logging.DEBUG, filename='/tmp/runpon.log')

# Where the configuration file resides.
#CONFIG_DIR = os.path.join('~', '.config', 'runpon')
CONFIG_DIR = '/opt/inetman'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'inetman.cfg')

# Default values for the configuration file.
CONFIG_DEFAULTS = {
    # Commands to be executed.
    'on': 'pon',
    'off': 'poff',
    # Interface to check.
    'check_interface': 'ppp0',
    # Run the 'off' command if the interface is no more with us.
    'run_off_if_fails': 'true',
    # Run the 'off' command at exit, if the timer is still running.
    'run_off_at_exit': 'true',
    # Check the interface every X seconds.
    'check_interval': '1800', #30 mins
    # Don't check the interface for the first X seconds; otherwise, if the
    # check is performed while the interface is not yet up, the 'off' command
    # will be called (only if 'run_off_if_fails' is True).
    # Keep it large enough. :-)
    'check_grace_time': '900',
    # Cumulative time (in seconds) of the connection.
    'cumulative_time': '0',
    # Length, in seconds, of a time slot.
    'cumulative_time_slot': '1'
}

# Default sections created in the configuration file.
_DEFAULT_OPTIONS = {'active': 'runpon'}
_DEFAULT_OPTIONS.update(CONFIG_DEFAULTS)
CONFIG_SECTIONS = {
    'DEFAULT': _DEFAULT_OPTIONS,
    'runpon': CONFIG_DEFAULTS
}

# Update the label every X seconds.
INTERVAL = 1

PRG_NAME = 'inetman'
RUNPON_HELP = """%s [%s] - runs pon/poff scripts.
         Based on RunPON: http://erlug.linux.it/~da/soft/runpon/

    -h (--help)     get this help and exits.

    --logging-level level   print logs of the specified level or higher.
    --logging-file  file    print logs into the given file.

    The configuration settings are stored in %s
""" % (PRG_NAME, VERSION, CONFIG_FILE)


class RunPONConfigParser(configparser.ConfigParser):
    """Custom configuration parser."""
    def getValue(self, key, converter=None, default=None):
        """Return the value of the specified key, looking first into the
        active section (specified with the 'active' option of the 'DEFAULT'
        section.

        *key*       the key to search for.
        *converter* a callable that will be applied to the return value.
        *default*   the default value to return if the key is not found."""
        if converter is bool and default is None:
            default = False
        try:
            active = self.getActiveSection()
            # Get the value from the active section.
            value = self.get(active, key)
            if not value:
                return default
            if converter:
                try:
                    if converter is bool:
                        value = self._boolean_states[value.lower()]
                    else:
                        value = converter(value)
                except Exception:
                    return default
            return value
        except ConfigParser.Error:
            return default

    def setValue(self, option, value):
        """Set a value in the active section."""
        active = self.getActiveSection()
        self.set(active, option, value)

    def getActiveSection(self):
        """Return the active section (DEFAULT is the fall-back option)."""
        try:
            # First of all, tries to identify the active section; if it's
            # not set, falls back to DEFAULT.
            active = self.get('DEFAULT', 'active')
            if not self.has_section(active):
                active = 'DEFAULT'
        except ConfigParser.Error:
            active = 'DEFAULT'
        return active

    def addSection(self, section):
        """Add a new section, populating it with default values."""
        try:
            self.add_section(section)
        except ConfigParser.DuplicateSectionError:
            return
        for key, value in CONFIG_DEFAULTS.items():
            self.set(section, key, value)


def manageConfigFile():
    """Return a ConfigParser instance, reading values from a file and
    creating it, if it doesn't exist."""
    confFN = os.path.expanduser(CONFIG_FILE)
    _creating = False
    _gotFile = True
    try:
        cfgFile = open(confFN)
    except (IOError, OSError):
        # We're trying to create the file.
        _creating = True
        try:
            os.makedirs(os.path.expanduser(CONFIG_DIR))
        except (IOError, OSError):
            pass
        try:
            cfgFile = open(confFN, 'w+')
        except (IOError, OSError):
            # Uh-oh! We can't get a file - go on with the default values.
            _gotFile = False
    config = RunPONConfigParser()
    if _gotFile:
        config.readfp(cfgFile)
    if _creating:
        # Populate the new configuration object.
        for section, options in CONFIG_SECTIONS.items():
            if section != 'DEFAULT':
                config.add_section(section)
            for key, value in options.items():
                config.set(section, key, value)
        if _gotFile:
            config.write(cfgFile)
    return config


def get_status_output(*args, **kwargs):
    p = subprocess.run(*args, **kwargs)
    return p.returncode, p.stdout



def executeCommand(cmdLine, _force=False):
    """Execute the given command line, returning a (status, output) tuple.
    If an exception is caught, status is set to None and output to a string
    representing the exception.  If _force is True the command is executed
    even if DONT_RUN is True."""
    if DONT_RUN and not _force:
        logging.info('I WOULD RUN %s' % cmdLine)
        return 0, ''
    try:
        status, output = get_status_output(shlex.split(cmdLine))
    except Exception as e:
        status, output = None, str(e)
    return status, output


class Timer(object):
    """Keep track of the elapsed time."""
    # Today is the first day of... the Epoch.
    _timeZero = time.gmtime(0)

    def __init__(self, initSec=None, running=False, format='%H:%M:%S'):
        """Initialize the Timer instance.

        *initSec*   float representation of time (current time, if None).
        *running*   the timer is running? (False by default).
        *format*    format of the displayed time."""
        self.running = running
        if initSec is None:
            self.reset()
        else:
            self.initSec = initSec
        self.format = format

    def getTime(self, format=None):
        """Return the elapsed time in the specified format."""
        if format is None:
            format = self.format
        if self.running:
            diffTime = time.gmtime(float(self))
        else:
            # A nice '00:00:00' or something like that.
            diffTime = self._timeZero
        return time.strftime(format, diffTime)

    def reset(self):
        """Reset the timer."""
        self.initSec = time.time()

    def start(self):
        """Start the timer."""
        self.running = True

    def restart(self):
        """Restart the timer."""
        self.reset()
        self.start()

    def stop(self):
        """Stop the timer."""
        self.running = False

    def setStatus(self, status):
        """Set the running status; it can be 'on' or 'off'."""
        if status == 'on':
            self.restart()
        elif status == 'off':
            self.stop()

    def __str__(self):
        """Return the elapsed time as a string."""
        return self.getTime()

    def __int__(self):
        """Return the elapsed time as an integer."""
        return int(time.time() - self.initSec)

    def __float__(self):
        """Return the elapsed time as a float."""
        return time.time() - self.initSec

    def __cmp__(self, other):
        """Numeric comparisons."""
        _fs = float(self)
        if _fs < other:
            return -1
        if _fs > other:
            return 1
        return 0


class Observable(defaultdict):
    """Event dispatcher.  Not-so-loosely based on:
    http://en.wikipedia.org/wiki/Observer_pattern ."""
    def __init__(self, *args, **kwds):
        """Initialize the instance."""
        # Values are assumed to be Python objects (callables, hopefully).
        super(Observable, self).__init__(object, *args, **kwds)

    def register(self, subscriber):
        """Register a new subscriber to this event."""
        self[subscriber]

    def notify(self, *args, **kwds):
        """Notify every subscriber of the event, storing the result."""
        for subscriber in self:
            # XXX: so far, storing the return is useless.
            #      Catch every exception?
            self[subscriber] = subscriber(*args, **kwds)


def connect(wait=False):
    if not connected():
        executeCommand(config.getValue('on', None, 'pon'))
        while wait and not connected(timeout=20):
            pass


def disconnect():
    if connected():
        executeCommand(config.getValue('off', None, 'poff'))


def wait_for_iface(dev, timeout=20, interval=1.0):
    # Check sysfs presence to avoid racing netifd
    path = f"/sys/class/net/{dev}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return True
        time.sleep(interval)
    return False


def connected(timeout=1):
    return wait_for_iface(config.getValue('check_interface'), timeout=timeout)


if __name__ == '__main__':
    """Things to do when called by the command line."""
    import getopt
    try:
        optList, args = getopt.getopt(sys.argv[1:], 'h',
                            ['logging-level=', 'logging-file=', 'help'])
    except getopt.error as e:
        print('Trouble with the arguments:', e)
        print('')
        print(RUNPON_HELP)
        sys.exit(1)
    kwds = {}
    loggingLevel = logging.NOTSET
    loggingFile = None
    for opt, value in optList:
        if opt == '--logging-level':
            loggingLevel = _LOGGING_LEVELS.get(value, logging.NOTSET)
        elif opt == '--logging-file':
            loggingFile = value
        elif opt in ('-h', '--help'):
            print(RUNPON_HELP)
            sys.exit(0)
    if kwds.get('hideWindow') is True and kwds.get('withTray') is False:
        print('--tray option is incompatible with --no-tray')
        print('')
        print(RUNPON_HELP)
        sys.exit(1)
    if loggingLevel != logging.NOTSET:
        logging.basicConfig(level=loggingLevel, filename=loggingFile,
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(filename=CONFIG_FILE)

config = manageConfigFile()
