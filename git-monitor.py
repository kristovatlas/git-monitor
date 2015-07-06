'''
Author: Kristov Atlas <firstname lastname @ gmail.com>
Description: This script will look for user-configurable substrings in git projects' commit histories. It can be run on-demand or as a scheduled job.
'''

###########
# IMPORTS #
###########

import ConfigParser	# Configuration file
import os.path 		# Helps direct git to correct directory
import sys 			# sys.exit
import subprocess 	# For running the git command in shell
import re 			# Grepping for stuff
import time			# Timestamp
import datetime		# Timestamp

####################
# GLOBAL VARIABLES #
####################

config_filename = 'git-monitor.cfg'

###########
# CLASSES #
###########

#From: http://stackoverflow.com/questions/3220670/read-all-the-contents-in-ini-file-into-dictionary-with-python
class DictConfigParser(ConfigParser.ConfigParser):
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d

class SearchCriteria:
	label = ''
	regex = ''
	git_project_location = ''
	case_sensitive = False
	exclude_these_file_extensions = []
	
	def __init__(self, label):
		self.label = label
	
	def __str__(self):
		ret = "{label:%s,regex:%s,git_project_location:%s,case_sensitive:%s,exclude_these_file_extensions:[" % (self.label, self.regex, self.git_project_location, string2bool(self.case_sensitive))
		for file_extension in self.exclude_these_file_extensions:
			 ret = ret + file_extension + ","
		ret = ret[:-1] #remove trailing comma
		ret = ret + ']}'
		return ret
	
#############
# FUNCTIONS #
#############

def is_not_blank_or_whitespace(string):
	if (string == '' or string.isspace()):
		return False
	else:
		return True

def get_timestamp():
	timestamp_format = '%Y-%m-%d %H:%M:%S'
	timestamp = datetime.datetime.fromtimestamp(time.time()).strftime(timestamp_format)
	return timestamp

#print debugging info if enabled by PRINT_DEBUG
def dprint(string):
	if (PRINT_DEBUG):
		timestamp = get_timestamp()
		print("DEBUG [%s]: %s" % (timestamp, string))

def string2bool(bool_as_string):
	return (True if bool_as_string == 'True' else False)

def bool2string(bool):
	return ('True' if bool else 'False')

def run_search(regex, git_project_location, case_sensitive):
	#change to the correct directory for the git project; I couldn't get this working with flags passed to the 'git' command.
	try:
		os.chdir(git_project_location)
	except Exception:
		sys.exit("Could not change to git project directory '%'" % git_project_location)
	
	#run the git log search and return the results
	return run_search_command(regex, case_sensitive)

#From: http://stackoverflow.com/questions/7353054/call-a-shell-command-containing-a-pipe-from-python-and-capture-stdout		
def run_search_command(regex, case_sensitive):
	#git rev-list --all | xargs git grep [-i] expression
	git_command = ['git','rev-list','--all']
	grep_command = ['xargs','git','grep']
	if (case_sensitive == False):
		grep_command.append('-i')
	grep_command.append(regex)
	
	git_process = subprocess.Popen(git_command, stdout=subprocess.PIPE)
	grep_process = subprocess.Popen(grep_command, stdin=git_process.stdout, stdout=subprocess.PIPE)
	git_process.stdout.close() # Allow git_process to receive a SIGPIPE if grep_process exits.
	output,err = grep_process.communicate()
	
	dprint("search='%s' output='%s' err='%s'" % (regex, output, err))
	return output.split("\n")
	
#read in new search criteria from configuration file
def get_search_criteria(config, section_name):
	label = section_name[7:]
	regex = ''
	git_project_location = ''
	exclude_these_file_extensions_list = ''
	case_sensitive = False
	
	name_value_pairs = config.items(section_name)
	for name, value in name_value_pairs:
		if (name == 'regex'):
			regex = value
		elif (name == 'git_project_location'):
			git_project_location = value
		elif (name == 'exclude_these_file_extensions'):
			exclude_these_file_extensions_list = value
		elif (name == 'case_sensitive'):
			case_sensitive = string2bool(value)
		else:
			sys.exit("Invalid configuration syntax '%s' under section '%s' in '%s'. Please fix." % (name, section_name, config_filename))
	s = SearchCriteria(label)
	s.regex = regex
	s.git_project_location = git_project_location
	if (case_sensitive == True):
		s.case_sensitive == True # False by default in class
	
	#split list as string into actual list
	if (is_not_blank_or_whitespace(exclude_these_file_extensions_list)):
		s.exclude_these_file_extensions = exclude_these_file_extensions_list.split(',')
	
	return s

def get_matches(regex, string):
	p = re.compile(regex)
	m = p.match(string)
	return m
	
#param0: one SearchCriteria object
#param1: list of strings representing filename suffixes to exclude from search results
#param2: list of strings representing commit hashes to exclude from search results
def get_search_results(search, file_extension_exclusions, commit_hash_exclusions):
	resultLines = run_search(search.regex, search.git_project_location, search.case_sensitive)
	
	matching_lines = []
	
	for line in resultLines:
		#start by assuming line should not be excluded, then rule it out if necessary
		exclude_this_line = False
		
		if (line != ''): #ignore blank lines
			#TODO: the following will be confounded by filenames with colons
			m = get_matches('(\w+):([^:]+):(.*)', line)
			if (m.group() != None):
				#found some matches, now eliminate the ones that should be excluded
				commit_hash = m.group(1)
				filename = m.group(2)
				match = m.group(3)
				
				dprint("commit_hash='%s' filename='%s' match='%s'" % (commit_hash, filename, match))
				
				for file_ext_to_exclude_for_this_search in search.exclude_these_file_extensions:
					if (filename.endswith(file_ext_to_exclude_for_this_search)):
						exclude_this_line = True
						dprint("Ignoring this line because the search criteria requires the file extension to be ignored.")
						break
				
				if (exclude_this_line == True): # for...else is ugly -__-
					continue #exclude this line
				
				for file_ext_to_exclude_always in file_extension_exclusions:
					if (filename.endswith(file_ext_to_exclude_always)):
						exclude_this_line = True
						dprint("Ignoring this line because the config file requires the file extension to be ignored in all searches.")
						break
				
				if (exclude_this_line == True):
					continue #exclude this line
				
				for commit_hash_to_exclude in commit_hash_exclusions:
					if (commit_hash == commit_hash_to_exclude):
						exclude_this_line = True
						dprint("Ignoring this line because the config file requires this commit to be ignored in all searches.")
						break
				
				if (exclude_this_line == True):
					continue #exclude this line
				
				#no reason to exclude this line, include it as a line to return
				matching_lines.append(line)
	return matching_lines

################
# BEGIN SCRIPT #
################

''' GET CONFIGURATION FROM CONFIG FILE '''

config = DictConfigParser()

try:
	config.readfp(open(config_filename))
except ConfigParser.Error:
	sys.exit("Could not read or parse '%s'" % config_filename)

config.read(config_filename)

PRINT_DEBUG = False # Print DEBUG statements or not? (overridden by config file)

searches = [] #list of SearchCriteria objs
file_extension_exclusions = [] #list of strings
commit_hash_exclusions = [] #list of strings

for section_name in config.sections():
	if section_name == 'Global':
		PRINT_DEBUG = string2bool(config.get('Global','PRINT_DEBUG'))
	elif section_name[0:7] == 'search:':
		s = get_search_criteria(config, section_name)
		dprint("Appending this search criteria: %s" % s)
		searches.append(s)
		
	elif section_name == "Exclusions":
		#read in exclusions
		name_value_pairs = config.items(section_name)
		for name, value in name_value_pairs:
			if (name == 'always_ignore_these_filetypes'):
				if (is_not_blank_or_whitespace(value)):
					dprint("always_ignore_these_filetypes = '%s'" % value)
					#config file defines one or more filetype to ignore
					file_extension_exclusions = value.split(',')
					dprint("Added %d file extensions to ignore always: %s" % (len(file_extension_exclusions), value))
			elif (name == 'always_ignore_these_commits'):
				if (is_not_blank_or_whitespace(value)):
					#config file defines one or more commits to ignore
					commit_hash_exclusions = value.split(',')
					dprint("Added %d commits to ignore always: %s" % (len(commit_hash_exclusions), value))
			else:
				sys.exit("Invalid configuration syntax '%s' under section '%s' in '%s'. Please fix." % (name, section_name, config_filename))
	else:
		sys.exit("Found invalid section name '%s' in configuration file '%s'. Please fix the configuration file." % (section_name, config_filename))

''' PERFORM SEARCHES '''

for s in searches:
	result_lines = get_search_results(s, file_extension_exclusions, commit_hash_exclusions)
	if (result_lines != None and len(result_lines) != 0):
		print("Found %d matches for search criteria labeled '%s':" % (len(result_lines), s.label))
		for line in result_lines:
			print("\t" + line)
	else:
		print("No matches for search criteria labeled '%s'." % s.label)