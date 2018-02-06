# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims.browser.worksheet.views import \
    ManageResultsView as MRV

from bika.lims import bikaMessageFactory as _

from bika.lims.browser.worksheet.tools import (checkUserAccess,
                                               showRejectionMessage)
from bika.lims.browser.worksheet.views import AnalysesTransposedView
from ace.lims.browser.worksheet.views.analyses import AnalysesView
from bika.lims.config import WORKSHEET_LAYOUT_OPTIONS


class ManageResultsView(MRV):

    def __call__(self):

        # Deny access to foreign analysts
        if checkUserAccess(self.context, self.request) is False:
            return []

        showRejectionMessage(self.context)

        self.icon = "/++resource++bika.lims.images/worksheet_big.png"
        self.icon = '{}{}'.format(self.portal_url, self.icon)

        # Save the results layout
        rlayout = self.request.get('resultslayout', '')
        if rlayout and rlayout in WORKSHEET_LAYOUT_OPTIONS.keys() \
           and rlayout != self.context.getResultsLayout():
            self.context.setResultsLayout(rlayout)
            message = _("Changes saved.")
            self.context.plone_utils.addPortalMessage(message, 'info')

        # Here we create an instance of WorksheetAnalysesView
        if self.context.getResultsLayout() == '2':
            # Transposed view
            self.Analyses = AnalysesTransposedView(self.context, self.request)
        else:
            # Classic view
            self.Analyses = AnalysesView(self.context, self.request)

        self.analystname = self.context.getAnalystName()
        self.instrumenttitle = self.context.getInstrument() \
            and self.context.getInstrument().Title() or ''

        # Check if the instruments used are valid
        self.checkInstrumentsValidity()

        return self.template()
