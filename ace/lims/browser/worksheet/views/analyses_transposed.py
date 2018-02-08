# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims.browser.worksheet.views.analyses_transposed import \
        AnalysesTransposedTable as ATB
from ace.lims.browser.worksheet.views.analyses import AnalysesView


class AnalysesTransposedView(AnalysesView):
    """ The view for displaying the table of manage_results transposed.
        Analysis Requests are displayed in columns and analyses in rows.
        Uses most of the logic provided by BikaListingView through
        bika.lims.worksheet.views.AnalysesView to generate the items,
        but renders its own template, which is highly specific for
        display analysis results. Because of this, some generic
        BikaListing functionalities, such as sorting, pagination,
        contextual menus for columns, etc. will not work in this view.
    """

    def contents_table(self, table_only=True):
        """ Overrides contents_table method from the parent class
            BikaListingView, using the transposed template instead
            of the classic template.
        """
        table = ATB(bika_listing=self, table_only=True)
        return table.render(self)
