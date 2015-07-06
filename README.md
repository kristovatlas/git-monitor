# git-monitor
Monitor git repositories for the presence of configurable substrings

Author: Kristov Atlas

## Applications

This can be used by engineers to detect regular expressions of concern in git repositories, such as the introduction of unsafe function usage.

## Setup

1. Modify ```git-mointor.cfg``` (use ```git-monitor-example.cfg``` as a reference).

2. Execute: ```python git-monitor.py```.

## TODOs:

  * Add option to automatically update git project first (git pull)
  * Add option to send email alert when new search results found
  * Allow search to apply only to specific extensions (whitelist), e.g. search only for "strcpy" in ".c" files.