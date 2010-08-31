#!/usr/bin/env python
# - encoding: utf8 -
#
# Copyright 2010 by Arnold Krille <arnold@arnoldarts.de>
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
parser.add_option('-n', '--non-interactive', help='Don\'t run interactive. The apps fails if there is no valid login token for google in the config-file.', dest='interactive', action='store_false')

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
    loginworked = True
except:
    loginworked = False

if options.interactive and not loginworked:
    print "No previous token was found (or could be used). Please enter your google-username and -password to authenticate."
    username = raw_input('Username: ')
    passwd = getpass.getpass()
    try:
        docsservice.ClientLogin(username, passwd, source="Python Google Docs Backup")
        spreadsheetservice.ClientLogin(username, passwd, source="Python Google Docs Backup")
        config.set('googlebackup', 'docstoken', docsservice.GetClientLoginToken())
        config.set('googlebackup', 'spreadsheettoken', spreadsheetservice.GetClientLoginToken())
        loginworked = True
    except:
        loginworked = False

if loginworked == False:
    print >> sys.stderr, "Login failed!"
    if not options.interactive:
        print >> sys.stderr, "You have to run this app interactively at least once to enter username and password and retrieve a valid login token from google."
    sys.exit(-1)

lastrun = datetime.datetime.strptime(config.get('googlebackup', 'lastrun'), '%Y-%m-%dT%H:%M:%S.%f')

alldocuments = docsservice.GetDocumentListFeed().entry

if verbose:
    print str(alldocuments[0]).replace('><', '>\n<'), '\n'
    print alldocuments[0].link, '\n'
    print alldocuments[0].category, '\n'


endings = {
        'document': 'odt',
        'spreadsheet': 'ods',
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
    ending='html'
    if entry.GetDocumentType() in endings:
        ending = endings[entry.GetDocumentType()]
    filename = os.path.join(pathdir, hidden + entry.title.text + '.' + ending)


    published = datetime.datetime.strptime(entry.published.text, '%Y-%m-%dT%H:%M:%S.%fZ')
    updated = datetime.datetime.strptime(entry.updated.text, '%Y-%m-%dT%H:%M:%S.%fZ')
    if lastrun < updated or not os.path.exists(filename):
        if not options.quiet:
            print " Have to get this file again!"

        if not os.path.exists(pathdir):
            os.makedirs(pathdir)
        if ending is 'ods':
            docstoken = docsservice.GetClientLoginToken()
            docsservice.SetClientLoginToken(spreadsheetservice.GetClientLoginToken())
            try:
                docsservice.Download(entry, filename, ending)
            except Exception, e:
                print e
            docsservice.SetClientLoginToken(docstoken)
        else:
            try:
                docsservice.Download(entry, filename, ending)
            except Exception, e:
                print e
        modtime = time.mktime(updated.timetuple())
        os.utime(filename, (int(time.time()), int(modtime)))

config.set('googlebackup', 'lastrun', datetime.datetime.now().isoformat('T'))

saveconfig()

# vim: et