::

              __       __    __
    .--.--.--|__.-----|  |--|  |--.-----.-----.-----.
    |  |  |  |  |__ --|     |  _  |  _  |     |  -__|
    |________|__|_____|__|__|_____|_____|__|__|_____|
                                       version 2.3.2

    Build composable event pipeline servers with minimal effort.



    ===================
    wishbone.flow.match
    ===================

    Version: 1.2.2

    Pattern matching on a key/value document stream.
    ------------------------------------------------


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
