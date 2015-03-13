#pygooglebackup

## What does it do?

Despite google's efforts and claims, some people feel safer when they have a
copy of their documents in their local backups. pygooglebackup tries to solve
this.

It is not a complete backup solution, its 'only' a small script to be run
before your backup-process does its job.

# How does it work?

It looks for valid authentication tokens in the configuration file. Then it
fetches a list of all documents it can see in that account. If a document
doesn't exist on the local disc, it is fetched. If a document in the account was
modified after the last run of the script, it is fetched.

# How to use it?

If you do not want to save authorization tokens for your main account on your
hard-disk (hint in a file only readable by you), create a 'dumb' google-account
and publish all your documents for that account to see (but not edit).

Then start the script once in interactive mode to ask you for username and
password (these will not be stored on disk) to fetch valid authorization tokens.
Edit the config file (~/.config/pygooglebackup/pygooglebackup.conf) afterwards
to adopt the backup directory and create that directory.

Finally add the script to cron to make it run before the systems backup is
running.

# What else?

Currently there are no finished downloads.

Also there is no setup.py script.

There is only a working script to download via the [source](https://github.com/kampfschlaefer/pygooglebackup) link above.

This script needs the fine [gdata-python-client](https://github.com/google/gdata-python-client).
