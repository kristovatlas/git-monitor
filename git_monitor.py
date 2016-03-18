'''
Author: Kristov Atlas <firstname lastname @ gmail.com>
Description: This script will look for user-configurable substrings in git
    projects' commit histories. It can be run on-demand or as a scheduled job.
'''

import ConfigParser
import os.path
import sys
import subprocess

import const #const.py
from util import (get_md5, html_file_printline, is_not_blank_or_whitespace,
                  get_timestamp, get_timestamp_filename_friendly, string2bool,
                  get_matches) #util.py

const.config_filename = 'git-monitor.cfg'

class DictConfigParser(ConfigParser.ConfigParser):
    """Dictionary class for parsing config file.

    From:
    http://stackoverflow.com/questions/3220670/read-all-the-contents-in-ini-file-into-dictionary-with-python
    """
    def as_dict(self):
        """Access config attriutes as dictionary"""
        dic = dict(self._sections)
        for key in dic:
            dic[key] = dict(self._defaults, **dic[key])
            dic[key].pop('__name__', None)
        return dic

class SearchCriteria(object):
    """Encapsulates criteria for searching for a pattern in a GitHub repo."""
    label = ''
    regex = ''
    git_project_location = ''
    case_sensitive = False
    exclude_these_file_extensions = []
    github_link = ''

    def __init__(self, label):
        """Constructor"""
        self.label = label

    def __str__(self):
        """Convert object to string for printing"""
        return (("{label:%s,regex:%s,git_project_location:%s,case_sensitive:%s,"
                 "exclude_these_file_extensions:%s,github_link:%s") %
                (self.label, self.regex, self.git_project_location,
                 string2bool(self.case_sensitive),
                 str(self.exclude_these_file_extensions), self.github_link))

class SearchResult(object):
    """Encapsulating results for a search."""
    commit_hash = ''
    #TODO: break into path and name separately
    file_path_and_name = ''
    match_string = ''

def generate_github_link(project_link, commit_hash, file_path_and_name):
    """Generate GitHub anchor tag that links to file in a commit.

    Args:
        project_link (str): A link to a projet on GitHub, e.g.:
            https://github.com/github/linguist
        commit_hash (str): Hash of git commit
        file_path_and_name (str): File path in project and filename. The MD5
            hash can be used as an anchor to jump to this section of a
            multi-file commit on GitHub.
    """
    #TODO: detect when inserting forward slashes is necessary and add as needed
    #rather than assuming.

    url = ("%s/commit/%s#diff-%s" %
           (project_link, commit_hash, get_md5(file_path_and_name)))

    return '<a href="%s">GitHub Link</a>' % url

def dprint(string):
    """Print debugging info"""
    if const.print_debug:
        timestamp = get_timestamp()
        print "DEBUG [%s]: %s" % (timestamp, string)

def run_search(regex, git_project_location, case_sensitive):
    """Execute search for regex"""
    #change to the correct directory for the git project; I couldn't get this
    #working with flags passed to the 'git' command.
    os.chdir(git_project_location)

    #run the git log search and return the results
    if const.detect_pattern is 'all':
        return run_search_command_all(regex, case_sensitive)
    elif const.detect_pattern is 'added_only':
        return run_search_command_added_only(regex, case_sensitive)
    else:
        sys.exit("Invalid value for DETECT_PATTERN option.")

def get_author_of_commit(commit_hash):
    """Return the author of the specified git commit."""
    raise NotImplementedError

def grep_git_command(git_command, grep_command):
    """Execute custom grep command on a git command and return result.

    From:
    http://stackoverflow.com/questions/7353054/call-a-shell-command-containing-a-pipe-from-python-and-capture-stdout
    """
    git_process = subprocess.Popen(git_command, stdout=subprocess.PIPE)
    grep_process = subprocess.Popen(
        grep_command, stdin=git_process.stdout, stdout=subprocess.PIPE)

    # Allow git_process to receive a SIGPIPE if grep_process exits.
    git_process.stdout.close()
    output, err = grep_process.communicate()

    dprint("search='%s' output='%s' err='%s'" %
           (str(git_command) + str(grep_command), output, err))
    return output.split("\n")

def run_search_command_added_only(regex, case_sensitive):
    """Search git logs for commits that add the specified regex to the code.

    This will only include the branch currently selected by git.

    Runs:
    `git log --format=format:%H -S expression [-i] | xargs git grep [-i] expression`
    """

    git_command = ['git', 'log', '--format=format:%H', '-S', regex]
    if not case_sensitive:
        git_command.append('-i')
    grep_command = ['xargs', 'git', 'grep']
    if not case_sensitive:
        grep_command.append('-i')
    grep_command.append(regex)

    return grep_git_command(git_command, grep_command)

def run_search_command_all(regex, case_sensitive):
    """Search a list of git commits for specified regex.

    This will include everyone commit in the entire git history, in which the
    specified expression is present, across all branches in the repository.

    Runs:
    `git rev-list --all | xargs git grep [-i] expression`
    """

    git_command = ['git', 'rev-list', '--all']
    grep_command = ['xargs', 'git', 'grep']
    if not case_sensitive:
        grep_command.append('-i')
    grep_command.append(regex)

    return grep_git_command(git_command, grep_command)

def get_search_criteria(config, section_name):
    """Read in new search criteria from configuration file.

    Returns:
        `SearchCriteria`
    """
    label = section_name[7:]
    regex = ''
    git_project_location = ''
    exclude_these_file_extensions_list = ''
    case_sensitive = False
    github_link = ''

    name_value_pairs = config.items(section_name)
    for name, value in name_value_pairs:
        if name == 'regex':
            regex = value
        elif name == 'git_project_location':
            git_project_location = value
        elif name == 'exclude_these_file_extensions':
            exclude_these_file_extensions_list = value
        elif name == 'case_sensitive':
            case_sensitive = string2bool(value)
        elif name == 'github_link':
            github_link = value
        else:
            sys.exit(("Invalid configuration syntax '%s' under section '%s' in "
                      "'%s'. Please fix.") %
                     (name, section_name, const.config_filename))

    search_crit = SearchCriteria(label)
    search_crit.regex = regex
    search_crit.git_project_location = git_project_location
    if case_sensitive:
        search_crit.case_sensitive = True # False by default in class

    #split list as string into actual list
    if is_not_blank_or_whitespace(exclude_these_file_extensions_list):
        search_crit.exclude_these_file_extensions = exclude_these_file_extensions_list.split(',')

    search_crit.github_link = github_link

    return search_crit

def get_search_results(search, file_extension_exclusions,
                       commit_hash_exclusions):
    """Get the search results for the specified search criteria.

    Args:
        search (`SearchCriteria`): The search criteria to use for searching.
        file_extension_exclusions (List[str]): Filename suffixes to exclude from
            search results.
        commit_hash_exclusions (List[str]): Commits to exclude from search
            results, identifed by hash.

    Returns:
        List of `SearchResult` objects.
    """
    result_lines = run_search(
        search.regex, search.git_project_location, search.case_sensitive)

    results = []

    for line in result_lines:
        #start by assuming line should not be excluded, then rule it out if necessary
        exclude_this_line = False

        if line == '':
            continue

        #TODO: the following will be confounded by filenames with colons
        matches = get_matches(r'(\w+):([^:]+):(.*)', line)
        if matches is not None and matches.group() is not None:
            #found some matches, now eliminate the ones that should be excluded
            commit_hash = matches.group(1)
            filename = matches.group(2)
            match = matches.group(3)

            result = SearchResult()
            result.commit_hash = commit_hash
            result.file_path_and_name = filename
            result.match_string = match

            dprint("commit_hash='%s' filename='%s' match='%s'" %
                   (commit_hash, filename, match))

            for file_ext_to_exclude_for_this_search in search.exclude_these_file_extensions:
                if filename.endswith(file_ext_to_exclude_for_this_search):
                    exclude_this_line = True
                    dprint(("Ignoring this line because the search criteria "
                            "requires the file extension to be ignored."))
                    break

            if exclude_this_line:
                continue

            for file_ext_to_exclude_always in file_extension_exclusions:
                if filename.endswith(file_ext_to_exclude_always):
                    exclude_this_line = True
                    dprint(("Ignoring this line because the config file "
                            "requires the file extension to be ignored in all "
                            "searches."))
                    break

            if exclude_this_line:
                continue

            for commit_hash_to_exclude in commit_hash_exclusions:
                if commit_hash == commit_hash_to_exclude:
                    exclude_this_line = True
                    dprint(("Ignoring this line because the config file "
                            "requires this commit to be ignored in all "
                            "searches."))
                    break

            if exclude_this_line:
                continue

            #no reason to exclude this result, include it as a result to return
            results.append(result)

    return results

def set_globals_from_config():
    """Set global consts from config file values and returns search parameters.

    Defaults:
        print_debug: False (can be set to True)
        output_format: plaintext (can be set to 'HTML')
        detect_pattern: all (can be set to 'added_only')

    Returns:
        A tuple of (searches, file_extension_exclusions, commit_hash_exclusions)
            searches: A list of SearchCriteria objects to be processed.
            file_extension_exclusions: A list of file extensions to exclude from
                search.
            commit_hash_exclusions: A list of commit hashes to exclude from
                search.
    """
    config = DictConfigParser()

    try:
        config.readfp(open(const.config_filename))
    except ConfigParser.Error:
        sys.exit("Could not read or parse '%s'" % const.config_filename)

    config.read(const.config_filename)

    searches = [] #list of SearchCriteria objs
    file_extension_exclusions = [] #list of strings
    commit_hash_exclusions = [] #list of strings

    for section_name in config.sections():
        if section_name == 'Global':
            const.print_debug = string2bool(config.get('Global', 'PRINT_DEBUG'))
            if config.get('Global', 'OUTPUT_FORMAT') == 'HTML':
                const.output_format = 'HTML'
            if config.get('Global', 'DETECT_PATTERN') == 'added_only':
                const.detect_pattern = 'added_only'
        elif section_name[0:7] == 'search:':
            search_crit = get_search_criteria(config, section_name)
            dprint("Appending this search criteria: %s" % search_crit)
            searches.append(search_crit)
        elif section_name == 'Excluded Filetypes':
            #read in file types to exclude from search results always
            name_value_pairs = config.items(section_name)
            for name in name_value_pairs:
                file_extension_exclusions.append(name)
            dprint("Added %d file extension(s) to ignore    always: %s" %
                   (len(file_extension_exclusions), file_extension_exclusions))
        elif section_name == 'Excluded Commits':
            name_value_pairs = config.items(section_name)
            for name in name_value_pairs:
                commit_hash_exclusions.append(name)
            dprint("Added %d commit(s) to ignore always: %s" %
                   (len(commit_hash_exclusions), commit_hash_exclusions))
        else:
            sys.exit(("Found invalid section name '%s' in configuration file "
                      "'%s'. Please fix the configuration file.") %
                     (section_name, const.config_filename))

    #Set default constants if not set in config file
    try:
        const.print_debug = False
    except:
        pass
    try:
        const.output_format = 'plaintext'
    except:
        pass
    try:
        const.detect_pattern = 'all'
    except:
        pass

    return (searches, file_extension_exclusions, commit_hash_exclusions)

def main():
    """Get search config, perform searches, output results, get paid."""

    result = set_globals_from_config()
    searches, file_extension_exclusions, commit_hash_exclusions = result

    html_file = None
    if const.output_format == 'HTML':
        html_filename = 'git-monitor_%s.html' % get_timestamp_filename_friendly()
        html_file = open(html_filename, "a")
        html_file_printline(html_file,
                            ("<!DOCTYPE html><html><!--generated by "
                             "git-monitor.py--><head><style>table{"
                             "border-collapse:collapse;}table,td,th{border:1px "
                             "solid black;}</style></head><body>"))

    for search in searches:
        results = get_search_results(
            search, file_extension_exclusions, commit_hash_exclusions)

        if results != None and len(results) != 0:
            msg = ("Found %d matches for search criteria labeled '%s':" %
                   (len(results), search.label))
            if const.output_format == 'HTML':
                html_file_printline(html_file, '<p>' + msg + '</p>')
            elif const.output_format == 'plaintext':
                print msg

            if const.output_format == 'HTML':
                html_file_printline(html_file,
                                    ("<table><tr><td><u>#</u></td><td>"
                                     "<u>commit hash</u></<td><td><u>file path "
                                     "and name</u></td><td><u>match</u></td>"
                                     "<td><u>github link</u></td></tr>"))

            result_num = 0
            for result in results:
                result_num = result_num + 1
                if const.output_format == 'HTML':
                    search_result = (("<tr><td>%d</td><td>%s</td><td>%s</td>"
                                      "<td>%s</td><td>") %
                                     (result_num, result.commit_hash,
                                      result.file_path_and_name,
                                      result.match_string))
                    if is_not_blank_or_whitespace(search.github_link):
                        search_result += generate_github_link(
                            project_link=search.github_link,
                            commit_hash=result.commit_hash,
                            file_path_and_name=result.file_path_and_name)
                    search_result += '</td></tr>' #end HTML row
                    html_file_printline(html_file, search_result)
                elif const.output_format == 'plaintext':
                    print("\t%s:%s:%s" % (result.commit_hash,
                                          result.file_path_and_name,
                                          result.match_string))

            if const.output_format == 'HTML':
                html_file_printline(html_file, '</table>') #end table for this search
        else:
            msg = "No matches for search criteria labeled '%s'." % search.label
            if const.output_format == 'HTML':
                html_file_printline(html_file, "<p>%s</p>" % msg)
            elif const.output_format == 'plaintext':
                print msg

    if const.output_format == 'HTML':
        html_file_printline(html_file,
                            '<!-- done with search results --></body></html>')
        html_file.close()

if __name__ == "__main__":
    main()
