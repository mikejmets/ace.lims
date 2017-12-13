# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.browser.analysisrequest.analysisrequests import AnalysisRequestsView


def folderitems(self, full_objects=False):
    items = super(AnalysisRequestsView, self).folderitems()
    if not self.request.get('analysisrequests_sort_on') or \
       self.request.analysisrequests_sort_on in (
                'created', 'getRequestID', 'getSample'):
        #Sort on AR ID sequence number
        reverse = False
        if self.request.get('analysisrequests_sort_on') and \
           self.request.analysisrequests_sort_on != 'created' and \
           self.request.analysisrequests_sort_order == 'descending':
            reverse = True
        items = sorted(
                items, 
                lambda x, y: cmp( x['id'].split('-')[3], y['id'].split('-')[3]),
                reverse=reverse)
    return items


