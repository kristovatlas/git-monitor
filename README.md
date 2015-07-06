# git-monitor
Monitor git repositories for the presence of configurable substrings. This will search all branches and all past history of each git repository.

Author: Kristov Atlas

## Applications

This can be used by engineers to detect regular expressions of concern in git repositories, such as the introduction of unsafe function usage.

Monitoring will typically involve the following phases:

1. Adding a new search term to the config file.
2. Training: review results of new search term, exclude findings you've reviewed from future searches.
3. Monitoring: Continue to run this program intermittently to identify new search results.

## Setup

1. Modify ```git-mointor.cfg``` (use ```git-monitor-example.cfg``` as a reference).

2. Execute: ```python git-monitor.py```.

## TODOs:

  * (High priority) Add option to automatically update git project first (git pull)
  * (High priority) Add option to send email alert when new search results found
  * (Medium priority) Allow search to apply only to specific extensions (whitelist), e.g. search only for "strcpy" in ".c" files.
  * (Low priority) Add option to specify or exclude specific repository branches
  * (Low priority) Move TODOs to GitHub issues
  * (Low priority) Add unit testing