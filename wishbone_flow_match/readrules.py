#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  readrulesdisk.py
#
#  Copyright 2014 Jelle Smet <development@smetj.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

from gevent import spawn
from gevent import sleep
from gevent import event
from glob import glob
import os
import yaml
from yaml.parser import ParserError
from deepdiff import DeepDiff


class ReadRulesDisk():

    '''
    Loads PySeps rules from a directory and monitors the directory for
    changes.

    Parameters:

        directory(string):   The directory to load rules from.
                            default: rules/

    '''

    def __init__(self, logger, directory="rules/"):
        self.logging = logger
        self.directory = directory

        self.__createDir(directory)

        if not os.access(self.directory, os.R_OK):
            raise Exception("Directory '%s' is not readable. Please verify." % (self.directory))

        self.current_files = self.__readFileList(self.directory)
        self.config = self.__parseFiles(self.current_files)

        spawn(self.__monitorChanges)
        self.__changes = event.Event()
        self.__changes.clear()

    def __createDir(self, location):

        if os.path.exists(location):
            if not os.path.isdir(location):
                raise Exception("%s exists but is not a directory" % (location))
            else:
                self.logging.info("Directory %s exists so I'm using it." % (location))
        else:
            self.logging.info("Directory %s does not exist so I'm creating it." % (location))
            os.makedirs(location)

    def getRules(self, block=True):

        return self.__parseFiles(self.current_files)

    def getRulesWait(self):

        self.__changes.wait()
        self.__changes.clear()
        return self.__parseFiles(self.current_files)

    def __monitorChanges(self):

        previous_files = self.__readFileList(self.directory)

        while True:
            current_files = self.__readFileList(self.directory)
            if DeepDiff(previous_files, current_files, ignore_order=True) != {}:
                previous_files = current_files
                self.current_files = current_files
                self.__changes.set()
            else:
                sleep(1)

    def __readFileList(self, directory):

        dir_content = []
        for f in glob("%s/*.yaml" % (directory)):
            dir_content.append({"filename": f, "mtime": os.path.getmtime(f)})
        return dir_content

    def __parseFiles(self, current_files):
        '''Reads the content of the given directory and creates a dict
        containing the rules.'''

        rules = {}
        for entry in current_files:
            try:
                with open(entry["filename"], 'r') as f:
                    key_name = os.path.abspath(entry["filename"])
                    rule = yaml.load("".join(f.readlines()))
                    try:
                        self.ruleCompliant(rule)
                    except Exception as err:
                        self.logging.warning("Rule %s not valid. Skipped. Reason: %s" % (entry["filename"], err))
                    else:
                        rules[key_name] = rule
            except ParserError as err:
                self.logging.warning("Failed to parse file %s.  Please validate the YAML syntax in a parser." % (entry["filename"]))
            except IOError as err:
                self.logging.warning("Failed to read %s.  Reason: %s" % (entry["filename"], err))
            except Exception as err:
                self.logging.warning("Unknown error parsing file %s.  Skipped.  Reason: %s." % (entry["filename"], err))

        return rules

    def ruleCompliant(self, rule):

        '''Does basic rule validation'''

        assert isinstance(rule["condition"], list), "Condition needs to be of type list."
        for c in rule["condition"]:
            assert isinstance(c, dict), "An individual condition needs to be of type dict."
        assert isinstance(rule["queue"], list), "Queue needs to be of type list."
