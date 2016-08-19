#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Copyright (c) 2014 Mozilla Corporation
#
# Contributors:
# Jeff Bryner jbryner@mozilla.com

from lib.alerttask import AlertTask
from query_models import SearchQuery, TermMatch, QueryFilter, MatchQuery, WildcardQuery


class AlertAccountCreations(AlertTask):
    def main(self):
        search_query = SearchQuery(minutes=10)

        search_query.add_must([
            TermMatch('_type', 'event'),
            TermMatch('tags', 'firefoxaccounts'),
            QueryFilter(MatchQuery('details.path','/v1/account/create','phrase'))

        ])

        #ignore test accounts and attempts to create accounts that already exist.
        search_query.add_must_not([
            QueryFilter(WildcardQuery(field='details.email',value='*restmail.net')),
            TermMatch('details.code','429')
        ])

        self.filtersManual(search_query)

        # Search aggregations on field 'sourceipv4address', keep X samples of events at most
        self.searchEventsAggregated('details.sourceipv4address', samplesLimit=10)
        # alert when >= X matching events in an aggregation
        self.walkAggregations(threshold=10)

    # Set alert properties
    def onAggregation(self, aggreg):
        # aggreg['count']: number of items in the aggregation, ex: number of failed login attempts
        # aggreg['value']: value of the aggregation field, ex: toto@example.com
        # aggreg['events']: list of events in the aggregation
        category = 'fxa'
        tags = ['fxa']
        severity = 'INFO'

        summary = ('{0} fxa account creation attempts by {1}'.format(aggreg['count'], aggreg['value']))
        emails = self.mostCommon(aggreg['allevents'],'_source.details.email')
        #did they try to create more than one email account?
        #or just retry an existing one
        if len(emails) > 1:
            for i in emails[:5]:
                summary += ' {0} ({1} hits)'.format(i[0], i[1])

            # Create the alert object based on these properties
            return self.createAlertDict(summary, category, tags, aggreg['events'], severity)
