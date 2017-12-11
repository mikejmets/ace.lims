# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.browser.analysisrequest.analysisrequests import AnalysisRequestsView


def folderitems(self, full_objects=False):
    items = super(AnalysisRequestsView, self).folderitems()
    #Sort on AR ID sequence number
    items.sort(lambda x, y: cmp(
        y['id'].split('-')[3],
        x['id'].split('-')[3]))
    ids = [r['id'].split('-')[3] for r in items]
    return items


