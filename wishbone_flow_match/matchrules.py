#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  matchrules.py
#
#  Copyright 2016 Jelle Smet <development@smetj.net>
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

import re


class MatchRules():

    '''
    Executes different forms of matching.

    re:     Regex matching
    !re:    Negative regex matching
    ==:     Equal to (string)
    !==:    Not equal to (string)
    >:      Bigger than
    >=:     Bigger or equal than
    <:      Smaller than
    <=:     Smaller or equal than
    =:      Equal to (numerals only)
    !=:     Not equal to (numeral only)
    in:     Check whether element is in list
    !in:    Check whether element is not in list
    '''

    def __init__(self):
        self.methods = {"re": self.regex,
                        "!re": self.negRegex,
                        "==": self.equalString,
                        "!==": self.notEqualString,
                        ">": self.more,
                        ">=": self.moreOrEqual,
                        "<": self.less,
                        "<=": self.lessOrEqual,
                        "=": self.equal,
                        "!=": self.notEqual,
                        "in": self.hasMember,
                        "!in": self.hasNotMember
                        }

    def __validateCondition(self, condition):

        s = condition.split(':')
        if len(s) == 1:
            raise Exception("Condition '%s' is not valid." % (condition))

        if s[0] not in self.methods:
            raise Exception("Condition '%s' has in invalid prefix '%s'" % (condition, s[0]))
        else:
            return s[0], ":".join(s[1:])


    def do(self, condition, data):

        method, value = self.__validateCondition(condition)
        try:
            return self.methods[method](value, data)
        except Exception as err:
            raise Exception("There was an error processing condition '%' on value '%s'" % (condition, data))

    def regex(self, value, data):
        return bool(re.search(value, str(data)))

    def negRegex(self, value, data):
        return not bool(re.search(value, str(data)))

    def equalString(self, value, data):
        return str(value) == str(data)

    def notEqualString(self, value, data):
        return not(str(value) == str(data))

    def more(self, value, data):
        return float(data) > float(value)

    def moreOrEqual(self, value, data):
        return float(data) >= float(value)

    def less(self, value, data):
        return float(data) < float(value)

    def lessOrEqual(self, value, data):
        return float(data) <= float(value)

    def equal(self, value, data):
        return float(data) == float(value)

    def notEqual(self, value, data):
        return float(data) != float(value)

    def hasMember(self, value, data):
        if isinstance(data, list):
            return str(value) in data
        else:
            return False

    def hasNotMember(self, value, data):
        if isinstance(data, list):
            return str(value) not in data
        else:
            return False
