# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

import json
from bika.lims import api
from bika.lims.browser.analyses import AnalysesView
from bika.lims.permissions import AddAnalysis
from bika.lims.permissions import EditFieldResults
from bika.lims.permissions import EditResults


def folderitems(self):
    # Patch folderitems to hide columns Method, Instrument and Uncertainty
    # Changes made on lines 146 - 150

    # Check if mtool has been initialized
    self.mtool = self.mtool if self.mtool \
        else api.get_tool('portal_membership')
    # Getting the current user
    self.member = self.member if self.member \
        else self.mtool.getAuthenticatedMember()
    # Getting analysis categories
    analysis_categories = self.bsc(
        portal_type="AnalysisCategory",
        sort_on="sortable_title")
    # Sorting analysis categories
    self.analysis_categories_order = dict([
        (b.Title, "{:04}".format(a)) for a, b in
        enumerate(analysis_categories)])
    # Can the user edit?
    if not self.allow_edit:
        can_edit_analyses = False
    else:
        checkPermission = self.mtool.checkPermission
        if self.contentFilter.get('getPointOfCapture', '') == 'field':
            can_edit_analyses = checkPermission(
                EditFieldResults, self.context)
        else:
            can_edit_analyses = checkPermission(EditResults, self.context)
        self.allow_edit = can_edit_analyses
    self.show_select_column = self.allow_edit

    # Users that can Add Analyses to an Analysis Request must be able to
    # set the visibility of the analysis in results report, also if the
    # current state of the Analysis Request (e.g. verified) does not allow
    # the edition of other fields. Note that an analyst has no privileges
    # by default to edit this value, cause this "visibility" field is
    # related with results reporting and/or visibility from the client side.
    # This behavior only applies to routine analyses, the visibility of QC
    # analyses is managed in publish and are not visible to clients.
    if not self.mtool.checkPermission(AddAnalysis, self.context):
        self.remove_column('Hidden')

    self.categories = []
    # Getting the multi-verification type of bika_setup
    self.mv_type = self.context.bika_setup.getTypeOfmultiVerification()
    self.show_methodinstr_columns = False
    self.dmk = self.context.bika_setup.getResultsDecimalMark()
    self.scinot = self.context.bika_setup.getScientificNotationResults()
    # Gettin all the items
    items = super(AnalysesView, self).folderitems(classic=False)

    # the TAL requires values for all interim fields on all
    # items, so we set blank values in unused cells
    for item in items:
        for field in self.interim_columns:
            if field not in item:
                item[field] = ''

    # XXX order the list of interim columns
    interim_keys = self.interim_columns.keys()
    interim_keys.reverse()

    # add InterimFields keys to columns
    for col_id in interim_keys:
        if col_id not in self.columns:
            self.columns[col_id] = {'title': self.interim_columns[col_id],
                                    'input_width': '6',
                                    'input_class': 'ajax_calculate numeric',
                                    'sortable': False}

    if can_edit_analyses:
        new_states = []
        for state in self.review_states:
            # InterimFields are displayed in review_state
            # They are anyway available through View.columns though.
            # In case of hidden fields, the calcs.py should check
            # calcs/services
            # for additional InterimFields!!
            pos = 'Result' in state['columns'] and \
                  state['columns'].index('Result') or len(state['columns'])
            for col_id in interim_keys:
                if col_id not in state['columns']:
                    state['columns'].insert(pos, col_id)
            # retested column is added after Result.
            pos = 'Result' in state['columns'] and \
                  state['columns'].index('Uncertainty') + 1 or len(
                state['columns'])
            state['columns'].insert(pos, 'retested')
            new_states.append(state)
        self.review_states = new_states
        # Allow selecting individual analyses
        self.show_select_column = True

    # Dry Matter.
    # The Dry Matter column is never enabled for reference sample contexts
    # and refers to getReportDryMatter in ARs.
    if items and \
            (hasattr(self.context, 'getReportDryMatter') and
             self.context.getReportDryMatter()):

        # look through all items
        # if the item's Service supports ReportDryMatter, add getResultDM().
        for item in items:
            full_object = item['obj'].getObject()
            if full_object.getReportDryMatter():
                dry_matter = full_object.getResultDM()
                item['ResultDM'] = dry_matter
            else:
                item['ResultDM'] = ''
            if item['ResultDM']:
                item['after']['ResultDM'] = "<em class='discreet'>%</em>"

        # modify the review_states list to include the ResultDM column
        new_states = []
        for state in self.review_states:
            pos = 'Result' in state['columns'] and \
                  state['columns'].index('Uncertainty') + 1 or len(
                state['columns'])
            state['columns'].insert(pos, 'ResultDM')
            new_states.append(state)
        self.review_states = new_states

    if self.show_categories:
        self.categories = map(lambda x: x[0],
                              sorted(self.categories, key=lambda x: x[1]))
    else:
        self.categories.sort()

    # self.json_specs = json.dumps(self.specs)
    self.json_interim_fields = json.dumps(self.interim_fields)
    self.items = items

    # Hide columns Method, Instrument and Uncertainty
    self.columns['Method']['toggle'] = False
    self.columns['Instrument']['toggle'] = False
    self.columns['Uncertainty']['toggle'] = False
    return items
