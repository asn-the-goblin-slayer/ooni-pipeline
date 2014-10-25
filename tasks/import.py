#!/usr/bin/env python
import os
from pymongo import MongoClient
from os.path import join, basename
from os import renames, walk
import re
import yaml

# You must set these environment variables:
# OONI_RAW_DIR
# OONI_SANITISED_DIR
# OONI_PUBLIC_DIR
# OONI_DB_IP
# OONI_DB_PORT

raw_directory = os.environ['OONI_RAW_DIR']
sanitized_dir = os.environ['OONI_SANITISED_DIR']
public_dir = os.environ['OONI_PUBLIC_DIR']

db_host, db_port = os.environ['OONI_DB_IP'], os.environ['OONI_DB_PORT']
client = MongoClient(db_host, db_port)
db = client.ooni

def list_report_files(directory):
    for dirpath, dirname, filenames in walk(directory):
        for filename in filenames:
            if filename.endswith(".yamloo"):
                yield join(dirpath, filename)

class ReportInserter(object):
    def __init__(self, report_file):
        try:
            # Insert the report into the database
            self.fh = open(report_file)
            self._report = yaml.safe_load_all(self.fh)
            self.header = self._report.next()
            cc = self.header['probe_cc']
            assert re.match("[a-zA-Z]{2}",cc)

            public_file = join(public_dir, cc, basename(report_file))
            self.header['report_file'] = public_file
            self.rid = db.reports.insert(self.header)

            # Insert each measurement into the database
            for entry in self:
                entry['report_id'] = self.rid
                db.measurements.insert(entry)

            # Move the report into the public directory
            renames(report_file, public_file)
        except Exception, e:
            print e

    def __iter__(self):
        return self

    def next(self):
        try:
            entry = self._report.next()
        except StopIteration:
            self.fh.close()
            raise StopIteration
        if not entry:
            entry = self.next()
        return entry

for report_file in list_report_files(sanitized_dir):
    ReportInserter(report_file)
