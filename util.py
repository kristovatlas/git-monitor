"""Various utility functions factored out of git-monitor.py"""

import re
import sys
import time
import datetime
import md5

def get_md5(string):
    """Return MD5 digest of string"""
    m = md5.new()
    m.update(string)
    return m.hexdigest()

def html_file_printline(fh, message):
    """Write a string to specified file"""
    try:
        fh.write(message + "\n")
    except Exception as e:
        sys.exit(e.errno)

def is_not_blank_or_whitespace(string):
    """Is the string empty or all whitespace?"""
    if (string == '' or string.isspace()):
        return False
    else:
        return True

def get_timestamp():
    """Get current timestamp string"""
    timestamp_format = '%Y-%m-%d %H:%M:%S'
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)
    return timestamp

def get_timestamp_filename_friendly():
    """Genereate a current timestamp that won't break a filename."""
    timestamp_format = '%Y-%m-%d_%H-%M-%S'
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)
    return timestamp

def string2bool(bool_as_string):
    """Convert string to boolean"""
    return (True if bool_as_string == 'True' else False)

def bool2string(bool):
    """Convert boolean to string"""
    return ('True' if bool else 'False')

def get_matches(regex, string):
    p = re.compile(regex)
    m = p.match(string)
    return m
