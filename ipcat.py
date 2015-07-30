#!/bin/bash
from __future__ import print_function

import os
import sqlite3
import sys
import time
import urllib

LAST_UPDATE = None
SQLITE_CURSOR = None
DOWNLOAD_FRESH_IPCAT_DELTA_DAYS = 4
IPCAT_HOME = os.path.join(os.path.expandvars(os.path.expanduser("~")), ".ipcat")
IPCAT_FILENAME = os.path.join(IPCAT_HOME, "ipcat.csv")
IPCAT_SQLITE = os.path.join(IPCAT_HOME, "ipcat.sqlite")
IPCAT_URL = "https://raw.github.com/client9/ipcat/master/datacenters.csv"

def _addr_to_int(value):
    _ = value.split('.')
    return (long(_[0]) << 24) + (long(_[1]) << 16) + (long(_[2]) << 8) + long(_[3])

def _retrieve_url(url, filename=None):
    try:
        filename, _ = urllib.urlretrieve(url, filename)
    except:
        filename = None
    return filename

def _update():
    global SQLITE_CURSOR
    global LAST_UPDATE

    try:
        if LAST_UPDATE and (time.time() - LAST_UPDATE) / 3600 / 24 < DOWNLOAD_FRESH_IPCAT_DELTA_DAYS:
            return

        if not os.path.exists(IPCAT_HOME):
            print("[i] creating directory '%s' for database storage" % IPCAT_HOME, file=sys.stderr)

            os.makedirs(IPCAT_HOME)

        if not os.path.exists(IPCAT_FILENAME) or (time.time() - os.stat(IPCAT_FILENAME).st_mtime) / 3600 / 24 >= DOWNLOAD_FRESH_IPCAT_DELTA_DAYS:
            print("[i] retrieving '%s'" % IPCAT_URL, file=sys.stderr)

            filename = _retrieve_url(IPCAT_URL, IPCAT_FILENAME)

            if SQLITE_CURSOR:
                SQLITE_CURSOR.connection.close()
                SQLITE_CURSOR = None

            if os.path.exists(IPCAT_SQLITE):
                os.remove(IPCAT_SQLITE)

        if not os.path.exists(IPCAT_SQLITE):
            print("[i] creating database '%s'" % IPCAT_SQLITE, file=sys.stderr)

            if SQLITE_CURSOR:
                SQLITE_CURSOR.connection.close()
                SQLITE_CURSOR = None

            with sqlite3.connect(IPCAT_SQLITE) as con:
                cur = con.cursor()
                cur.execute("CREATE TABLE ranges (start_int INT, end_int INT, name TEXT)")

                with open(IPCAT_FILENAME) as f:
                    for row in f.xreadlines():
                        if not row.startswith('#') and not row.startswith('start'):
                            row = row.strip().split(",")
                            cur.execute("INSERT INTO ranges VALUES (?, ?, ?)", (_addr_to_int(row[0]), _addr_to_int(row[1]), row[2]))

                cur.close()
                con.commit()

        LAST_UPDATE = time.time()

    except Exception, ex:
        print("[x] something went wrong during database update ('%s')" % str(ex), file=sys.stderr)

def lookup(address):
    global SQLITE_CURSOR

    retval = None

    _update()

    if SQLITE_CURSOR is None:
        SQLITE_CURSOR = sqlite3.connect(IPCAT_SQLITE).cursor()

    try:
        _ = _addr_to_int(address)
        SQLITE_CURSOR.execute("SELECT name FROM ranges WHERE start_int <= ? AND end_int >= ?", (_, _))
        _ = SQLITE_CURSOR.fetchone()
        retval = str(_[0]) if _ else retval
    except ValueError:
        print("[x] invalid IP address '%s'" % address, file=sys.stderr)

    return retval

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("[i] usage: python ipcat.py <address>\t# (e.g. 'python ipcat.py 2.16.1.0')", file=sys.stderr)
    else:
        print("%s" % (lookup(sys.argv[1]) or '-'))
