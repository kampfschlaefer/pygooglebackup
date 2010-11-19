#!/usr/bin/env python
# - encoding: utf8 -
#
# Copyright 2010 by Arnold Krille <arnold@arnoldarts.de>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, version 3 of the License.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.
#  If not, see <http://www.gnu.org/licenses/gpl-3.0.html>.
#

import sys, os, time, datetime, ConfigParser, stat
import getpass, optparse

try:
    import gdata.gauth
    import gdata.docs.service
    import gdata.spreadsheet.service
except:
    print >> sys.stderr, " You don't seem to have gdata installed!\n Fetch it from http://code.google.com/p/gdata-python-client/downloads/list and install it anywhere where python can find it.\n Best let the setup-tools do their job..."
    sys.exit(-1)


def downloadfile(service, entry, filename, ending):
    service.Download(entry, filename, ending)
    modtime = time.mktime(updated.timetuple())
    os.utime(filename, (int(time.time()), int(modtime)))


config = ConfigParser.SafeConfigParser()
config.add_section('googlebackup')
config.set('googlebackup', 'backupdir', '~/googlebackup')
config.set('googlebackup', 'lastrun', '1900-01-01T00:00:00.0')

def saveconfig():
    if not os.path.exists(os.path.expanduser('~/.config/googlebackup')):
        os.mkdir(os.path.expanduser('~/.config/googlebackup'))
    configpath = os.path.expanduser('~/.config/googlebackup/googlebackup.conf')
    if os.path.exists(configpath):
        os.rename(configpath, configpath+'~')
    config.write(open(configpath,'wb'))
    os.chmod(configpath, stat.S_IRUSR|stat.S_IWUSR)

if len(config.read(['/etc/googlebackup/googlebackup.conf', os.path.expanduser('~/.config/googlebackup/googlebackup.conf')])) < 1:
    saveconfig()

description="""
%prog fetches all documents from google-docs to a local directory.
Its primary use is for local backups. That is in collaboration with whatever backup-mechanism you already use...
%prog will fetch the last version of a document from google and overwrite whatever older version you had on disk. To actually have a longer backup, you have to add this directory into the tree your backup-application backs up. Best is to make your backup-app to run %prog before the real backup-run.
"""
parser = optparse.OptionParser(version='%prog 0.1', description=description)
parser.add_option('', '--debug', help='Add debugging output', default=False)
parser.add_option('-q', '--quiet', help='Run really quiet. No output apart from important errors (which are sent to stderr).', action='store_true', default=False)
parser.add_option('-i', '--interactive', help='Run interactively if needed.', dest='interactive', default=True, action='store_true')
parser.add_option('-n', '--non-interactive', help='Don\'t run interactive. The apps fails if there is no valid login token for google and no username/passwd in the config-file.', dest='interactive', action='store_false')

options, args = parser.parse_args()

verbose = options.debug

backupdir = os.path.expanduser(config.get('googlebackup', 'backupdir'))

if not os.path.exists(backupdir):
    raise OSError('The directory \'%s\' for the backup files doesn\'t exist.\n Either create that dir or change the value of backupdir in the config-file.' % backupdir)

loginworked = False

docsservice = gdata.docs.service.DocsService()
spreadsheetservice = gdata.spreadsheet.service.SpreadsheetsService()
try:
    docsservice.SetClientLoginToken(config.get('googlebackup', 'docstoken'))
    spreadsheetservice.SetClientLoginToken(config.get('googlebackup', 'spreadsheettoken'))
    docsservice.GetDocumentListFeed().entry
    loginworked = True
except:
    loginworked = False

if not loginworked:
    username = ''
    passwd = ''
    if config.has_option('googlebackup', 'username') and config.has_option('googlebackup', 'passwd'):
        print 'Using username and passwd from the config-file'
        username = config.get('googlebackup', 'username')
        passwd = config.get('googlebackup', 'passwd')
    elif options.interactive:
        username = raw_input('Username: ')
        passwd = getpass.getpass()

    try:
        docsservice.ClientLogin(username, passwd, source="Python Google Docs Backup")
        spreadsheetservice.ClientLogin(username, passwd, source="Python Google Docs Backup")
        config.set('googlebackup', 'docstoken', docsservice.GetClientLoginToken())
        config.set('googlebackup', 'spreadsheettoken', spreadsheetservice.GetClientLoginToken())
        loginworked = True
        saveconfig()
    except:
        loginworked = False

if loginworked == False:
    print >> sys.stderr, "Login failed!"
    if not options.interactive:
        print >> sys.stderr, """You have to run this app interactively at least once to enter username and password and retrieve a valid login token from google.
Or add username and passwd to the configuration file. (Note that these aren't saved in interactive sessions.)"""
    sys.exit(-1)

lastrun = datetime.datetime.strptime(config.get('googlebackup', 'lastrun').split('.')[0], '%Y-%m-%dT%H:%M:%S')

alldocuments = docsservice.GetDocumentListFeed().entry

if verbose:
    print str(alldocuments[0]).replace('><', '>\n<'), '\n'
    print alldocuments[0].link, '\n'
    print alldocuments[0].category, '\n'


endings = {
        'document': 'odt',
        'spreadsheet': 'ods',
        'pdf': 'pdf',
        'drawing': 'svg',
        'file': '',
        }

for entry in alldocuments:
    #print str(entry).replace('><', '>\n<')
    if verbose:
        print "> %s <  %s %s %s" % (entry.title.text, entry.GetDocumentType(), entry.resourceId.text, entry.updated.text)
    else:
        if not options.quiet:
            print "> %s <  %s" % (entry.title.text, entry.updated.text)

    parentdir = ''
    hidden = ''
    for cat in entry.category:
        if cat.label == 'hidden':
            hidden = '.'
        if verbose:
            print '  In category: %s' % cat.label
    for link in entry.link:
        if link.rel.endswith('#parent'):
            parentdir = link.title
        if verbose:
            print '  Has link: %s, %s, %s, %s' % (link.rel, link.title, link.type, link.href)

    #print ' Type is %s' % entry.GetDocumentType()

    pathdir = os.path.join(backupdir, parentdir)
    ending=''
    if entry.GetDocumentType() in endings:
        ending = endings[entry.GetDocumentType()]
    filename = os.path.join(pathdir, hidden + entry.title.text + '.' + ending)


    published = datetime.datetime.strptime(entry.published.text.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    updated = datetime.datetime.strptime(entry.updated.text.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    if lastrun < updated or not os.path.exists(filename):
        if not options.quiet:
            print " Have to get this file again!"

        if not os.path.exists(pathdir):
            os.makedirs(pathdir)
        if ending is endings['spreadsheet']:
            #
            # downloading spreadsheets requires the authentication token from the spreadsheet service.
            #
            docstoken = docsservice.GetClientLoginToken()
            docsservice.SetClientLoginToken(spreadsheetservice.GetClientLoginToken())
            try:
                downloadfile(docsservice, entry, filename, ending)
            except Exception, e:
                print 'Exception: ', e
            finally:
                docsservice.SetClientLoginToken(docstoken)
        else:
            #
            # Anything else will just work with the normal docservice auth-token
            #
            try:
                downloadfile(docsservice, entry, filename, ending)
            except Exception, e:
                print 'Exception: ', e

config.set('googlebackup', 'lastrun', datetime.datetime.now().isoformat('T'))

saveconfig()

# vim: et
