#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  match.py
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


from wishbone import Actor
from gevent import sleep
from .matchrules import MatchRules
from .readrules import ReadRulesDisk
from gevent.lock import Semaphore


class Match(Actor):

    '''**Pattern matching on a key/value document stream.**

    This module routes messages to a queue associated to the matching rule
    set.  The '@data' payload has to be of <type 'dict'>.  Typically,
    the source data is JSON converted to a Python dictionary.

    The match rules can be either stored on disk or directly defined into the
    bootstrap file.

    A match rule is written in YAML syntax and consists out of 2 parts:

    - condition:

        A list of dictionaries holding with the individual conditions which
        ALL have to match for the complete rule to match.

    ::

        re:     Regex matching
        !re:    Negative regex matching
        >:      Bigger than
        >=:     Bigger or equal than
        <:      Smaller than
        <=:     Smaller or equal than
        =:      Equal than (numeric only)
        in:     Evaluate list membership
        !in:    Evaluate negative list membership


    - queue:

        The queue section contains a list of dictionaries/maps each containing
        1 key with another dictionary/map as a value.  These key/value pairs
        are added to the *header section* of the event and stored under the
        queue name key.
        If you are not interested in adding any information to the header you
        can leave the dictionary empty.  So this would be valid:

    All rules will be evaluated sequentially in no particular order.  When a
    rule matches, evaluation the other rules will continue untill all rules
    are processed.

    *Examples*

    This example would route the events - with field "greeting" containing
    the value "hello" - to the outbox queue without adding any information
    to the header of the event itself.

    ::

        condition:
            - greeting: re:^hello$

        queue:
            - outbox:



    This example combines multiple conditions and stores 4 variables under
    @tmp.<self.name> while submitting the event to the modules'
    **email** queue.

    ::

        condition:
            - check_command: re:check:host.alive
            - hostproblemid: re:\d*
            - hostgroupnames: in:tag:development

        queue:
            - email:
                from: monitoring@yourdomain.com
                to:
                    - oncall@yourdomain.com
                subject: UMI - Host  {{ hostname }} is  {{ hoststate }}.
                template: host_email_alert



    Parameters:

        - name(str)
           |  The name of the module.

        - size(int)
           |  The default max length of each queue.

        - frequency(int)
           |  The frequency in seconds to generate metrics.

        - location(str)("")
           |  The directory containing rules.
           |  If empty, no rules are read from disk.

        - rules(dict)({})
           |  A dict of rules in the above described format.
           |  For example:
           |  {"omg": {"condition": [{"greeting": "re:^hello$"}], "queue": [{"outbox": {"one": 1}}]}}

        - ignore_missing_fields(bool)(False)
           |  When a doc is missing a field which is evaluated in the
           |  condition this will simply be ignored and therefor can still yield a match.
           |  When set to False(default) a missing field will automatically result in a non-match.


    Queues:

        - inbox
           |  Incoming events

        - <queue_name>
           |  The queue which matches a rule

        - nomatch
           |  The queue receiving event without matches

    '''

    def __init__(self, actor_config, location="", rules={}, ignore_missing_fields=False):
        Actor.__init__(self, actor_config)

        self.pool.createQueue("inbox")
        self.pool.createQueue("nomatch")
        self.registerConsumer(self.consume, "inbox")

        self.__active_rules = {}
        self.match = MatchRules()
        self.rule_lock = Semaphore()

    def preHook(self):
        if self.kwargs.location == "":
            self.__active_rules.update(self.uplook.dump()["rules"])
            self.logging.info("No rules directory defined, not reading rules from disk.")
        else:
            self.read_rules_disk = ReadRulesDisk(self.logging, self.kwargs.location)
            disk_rules = self.read_rules_disk.getRules()
            self.activateNewRules(disk_rules)
            self.sendToBackground(self.monitorRuleDirectory)

    def activateNewRules(self, rules):

        self.rule_lock.acquire()
        self.__active_rules={}
        self.__active_rules.update(rules)
        self.__active_rules.update(self.kwargs.rules)
        self.logging.info("Read %s rules from disk and %s defined in config." % (len(rules), len(self.kwargs.rules)))
        self.rule_lock.release()

    def monitorRuleDirectory(self):

        '''
        Loads new rules when changes happen.
        '''

        self.logging.info("Monitoring rules directory '%s' for changes" % (self.kwargs.location))

        while self.loop():
            try:
                new_rules = self.read_rules_disk.getRulesWait()
                self.activateNewRules(new_rules)
            except Exception as err:
                self.logging.warning("Problem reading rules directory.  Reason: %s" % (err))
                sleep(0.5)

    def consume(self, event):
        '''Submits matching documents to the defined queue along with
        the defined header.'''

        if isinstance(event.get(), dict):
            self.rule_lock.acquire()
            for rule in self.__active_rules:
                e = event.clone()
                if self.evaluateCondition(self.__active_rules[rule]["condition"], e.get()):
                    e.set(rule, '@tmp.%s.rule' % (self.name))
                    for queue in self.__active_rules[rule]["queue"]:
                        event_copy = e.clone()
                        for name in queue:
                            if queue[name] is not None:
                                for key, value in queue[name].items():
                                    event_copy.set(value, '@tmp.%s.%s' % (self.name, key))
                            self.submit(event_copy, self.pool.getQueue(name))
                else:
                    e.set(rule, "@tmp.%s.rule" % (self.name))
                    self.submit(e, self.pool.queue.nomatch)
                    self.logging.debug("No match for rule '%s'." % (rule))
            self.rule_lock.release()
        else:
            raise Exception("Incoming data is not of type dict, dropped.")

    def evaluateCondition(self, conditions, fields):
        for condition in conditions:
            for field in condition:
                if field in fields:
                    try:
                        match_result = self.match.do(condition[field], fields[field])
                    except Exception as err:
                        self.logging.error("Invalid condition '%s'. Skipped.  Reason: '%s'" % (condition[field], err))
                        return False
                    else:
                        if not match_result:
                            self.logging.debug("field '%s' with condition '%s' DOES NOT MATCH value '%s'" % (field, condition[field], fields[field]))
                            return False
                else:
                    if not self.kwargs.ignore_missing_fields:
                        return False
        return True
