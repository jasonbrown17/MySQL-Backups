#!/usr/bin/python -tt

'''
  This is to be used on a slave MySQL server to perform backups

  Version 0.1
    Inital script creation
    Dumps files for backup, compresses, and tarballs

  Version 0.5
    Dumping files as backup user
    Created log file
    Emails log file to recipients


  ---------------------------------------------------------------------
  Released under the GNU GPLv3 license

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
  ---------------------------------------------------------------------

'''

__author__ = "Jason Brown"
__email__ = "jason@jasonbrown.us"
__date__ = "20110125"
__status__ = "Production"
__version__ = "0.5"

''' Module Imports '''
import MySQLdb
import os
import smtplib
from sys import exit
from subprocess import call
from time import strftime
from base64 import b64decode as decode
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from socket import gethostname

def AllDB():
  ''' Tries to connect to the database.  Displays error code if its unable to connect'''
  try:
    conn = MySQLdb.connect (host = HOSTNAME,
                            user = USERNAME,
                            passwd = PASSWD)
    cursor = conn.cursor ()
    '''
      Stops the slave from receiving updates.  Displays all of the databases and places them into a list.
      Then closes out the connection
    '''
    LOGFILE = ('%s/log%s' % (WORKINGDIR, LOGTIME))
    f = open(LOGFILE, 'w')
    f.write("-------------------------------------\n")
    f.write(" Database backup for %s \n" % (TIME))
    f.write("-------------------------------------\n")
    f.write("\n")
    f.write("---------- \t ------\n")
    f.write("|Database| \t |Size|\n")
    f.write("---------- \t ------\n")
    cursor.execute ("STOP SLAVE;")
    cursor.execute ("show databases;")
    row = cursor.fetchall ()
    database = []
    for i in row:
      database.append("%s" % (i))
    cursor.execute ("START SLAVE;")
    cursor.close ()
    conn.close ()

    '''
      Loops through the database list, skipping the mysql and information schema databases.
      Then does the following:
        1) mysqldump
        2) Creates an md5 checksup against the sql file
        3) Gets file size of backup then writes it to file
        4) bzip's
        5) Creates tar file and appends the current date
    '''
    for DB in database:
      if DB == "information_schema" or DB == "mysql":
        continue
      call('/usr/bin/mysqldump -u%s -p%s %s > %s/%s.sql' % (USERNAME, PASSWD, DB, WORKINGDIR, DB), shell=True)
      call('/usr/bin/md5sum %s/%s.sql >> %s/checksum' % (WORKINGDIR, DB, WORKINGDIR), shell=True)
      SIZE = (os.path.getsize('%s/%s.sql' % (WORKINGDIR, DB)) / 1024)
      f.write('%s \t %s kbytes\n' % (DB, SIZE))
      call('/usr/bin/bzip2 -z -9 %s/%s.sql' % (WORKINGDIR, DB), shell=True)
    f.close()
    call('/bin/tar -cf %s/backup%s.tar %s/*.sql.bz2 %s/checksum --remove-files' % (WORKINGDIR, LOGTIME, WORKINGDIR, WORKINGDIR), shell=True)
    return LOGFILE
  except MySQLdb.Error, e:
    print "Error %d: %s" % (e.args[0], e.args[1])
    exit(1)

def Email():
  '''
    Emails log file to recipients found in the EMAILADDR variable under main
  '''
  LOGFILE = ('%s/log%s' % (WORKINGDIR, LOGTIME))
  log = open(LOGFILE, 'r')
  msg = MIMEMultipart()
  msg = MIMEText(log.read())
  addrs = EMAILADDR
  msg['Subject'] = "MySQL Backups on %s for %s" % (gethostname(), TIME)
  msg['From'] = FROMADDR
  msg['To'] = "Undisclosed"
  try:
    s = smtplib.SMTP(SMTPSERVER)
    s.sendmail(FROMADDR, EMAILADDR, msg.as_string())
    s.quit()
    log.close()
  except:
    print "***Connection Error***"



if __name__ == '__main__':

  ''' Constants '''
  LOGTIME = strftime("%Y%m%d")
  TIME = strftime("%B %d %Y")
  WORKINGDIR = "/opt/mysqlbackups"
  EMAILADDR = '<TO ADDRESS>'
  FROMADDR = '<FROM ADDRESS>'
  SMTPSERVER = '<SMTP SERVER ADDRESS>'

  ''' User credentials '''
  HOSTNAME = "<ENTER HOST>"
  USERNAME = "<ENTER USERNAME>"
  PASSWD = decode("<ENTER PASSWORD>")

  AllDB()
  Email()
