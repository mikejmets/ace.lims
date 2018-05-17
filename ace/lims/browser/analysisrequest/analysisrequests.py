# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

import collections

from bika.lims import bikaMessageFactory as _
from bika.lims.browser.analysisrequest.analysisrequests import \
    AnalysisRequestsView as ARV
from bika.lims.catalog import CATALOG_ANALYSIS_REQUEST_LISTING
from bika.lims.utils import t
from Products.Archetypes import PloneMessageFactory as PMF


from bika.lims.permissions import SampleSample
from bika.lims.config import PRIORITIES
from bika.lims.permissions import Verify as VerifyPermission
from bika.lims.utils import getUsers
from plone.api import user

from DateTime import DateTime
from Products.CMFCore.utils import getToolByName


class AnalysisRequestsView(ARV):
    """Listing View for all Analysis Requests in the System
    """

    def __init__(self, context, request):
        super(AnalysisRequestsView, self).__init__(context, request)

        # hide the right column
        request.set("disable_plone.rightcolumn", 1)

        # hide the editable border
        if self.context.portal_type == "AnalysisRequestsFolder":
            self.request.set("disable_border", 1)

        # catalog used for the query
        self.catalog = CATALOG_ANALYSIS_REQUEST_LISTING

        # see: https://docs.plone.org/develop/plone/searching_and_indexing/query.html#searching-for-content-within-a-folder
        self.contentFilter = {
            "sort_on": "created",
            "sort_order": "descending",
            "cancellation_state": "active",
        }

        # Filter by Department
        if self.context.bika_setup.getAllowDepartmentFiltering():
            deps = self.request.get('filter_by_department_info', '')
            dep_uids = deps.split(",")
            dep_query = {"query": dep_uids, "operator": "or"}
            self.contentFilter['getDepartmentUIDs'] = dep_query

        self.context_actions = {}

        if self.view_url.find("analysisrequests") == -1:
            self.view_url = self.view_url + "/analysisrequests"

        self.allow_edit = True
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.form_id = "analysisrequests"

        ar_image_path = "/++resource++bika.lims.images/analysisrequest_big.png"
        self.icon = "{}{}".format(self.portal_url, ar_image_path)
        self.title = self.context.translate(_("Analysis Requests"))
        self.description = ""

        SamplingWorkflowEnabled = \
            self.context.bika_setup.getSamplingWorkflowEnabled()

        # Check if the filter bar functionality is activated or not
        self.filter_bar_enabled =\
            self.context.bika_setup.\
            getDisplayAdvancedFilterBarForAnalysisRequests()

        self.columns = collections.OrderedDict((
            ("Priority", {
                "title": "",
                "index": "getPrioritySortkey",
                "sortable": True, }),
            ("Progress", {
                "title": "Progress",
                "sortable": False,
                "toggle": True,
                "toggle": True}),
            ("getId", {
                "title": _("Request ID"),
                "attr": "getId",
                "replace_url": "getURL",
                "index": "getId",
                "toggle": True}),
            ("getSampleTypeTitle", {
                "title": _("Sample Type"),
                "sortable": True,
                "toggle": True}),
            ("getStrain", {
                "title": _("Strain"),
                "sortable": True,
                "index": "getStrain",
                "toggle": True}),
            ("getClientSampleID", {
                "title": _("Client SID"),
                "toggle": True}),
            ("getClientReference", {
                "title": _("Client Ref"),
                "sortable": True,
                "index": "getClientReference",
                "toggle": True}),
            ("Client", {
                "title": _("Client"),
                "index": "getClientTitle",
                "attr": "getClientTitle",
                "replace_url": "getClientURL",
                "toggle": True}),
            ("getProfilesTitle", {
                "title": _("Profile"),
                "sortable": True,
                "index": "getProfilesTitle",
                "toggle": True}),
            ("getDateSampled", {
                "title": _("Date Sampled"),
                "toggle": True,
                "input_class": "datetimepicker_nofuture",
                "input_width": "10"}),
            ("getDateReceived", {
                "title": _("Date Received"),
                "toggle": False}),
            ("getSampler", {
                "title": _("Sampler"),
                "toggle": True}),
            ("state_title", {
                "title": _("State"),
                "sortable": True,
                "index": "review_state",
                "toggle": True}),
            ("getClientOrderNumber", {
                "title": _("Client Order"),
                "sortable": True,
                "toggle": False}),
            ("Creator", {
                "title": PMF("Creator"),
                "index": "getCreatorFullName",
                "sortable": True,
                "toggle": False}),
            ("Created", {
                "title": PMF("Date Created"),
                "index": "created",
                "toggle": False}),
            ("getSample", {
                "title": _("Sample"),
                "attr": "getSampleID",
                "index": "getSampleID",
                "replace_url": "getSampleURL",
                "toggle": False, }),
            ("BatchID", {
                "title": _("Batch ID"),
                "index": "getBatchID",
                "sortable": True,
                "toggle": False}),
            ("Province", {
                "title": _("Province"),
                "sortable": True,
                "index": "getProvince",
                "attr": "getProvince",
                "toggle": False}),
            ("District", {
                "title": _("District"),
                "sortable": True,
                "index": "getDistrict",
                "attr": "getDistrict",
                "toggle": False}),
            ("ClientContact", {
                "title": _("Contact"),
                "sortable": True,
                "index": "getContactFullName",
                "toggle": False}),
            ("getSamplePointTitle", {
                "title": _("Sample Point"),
                "sortable": True,
                "index": "getSamplePointTitle",
                "toggle": False}),
            ("getStorageLocation", {
                "title": _("Storage Location"),
                "sortable": True,
                "index": "getStorageLocationTitle",
                "toggle": False}),
            ("SamplingDeviation", {
                "title": _("Sampling Deviation"),
                "sortable": True,
                "index": "getSamplingDeviationTitle",
                "toggle": False}),
            ("SamplingDate", {
                "title": _("Expected Sampling Date"),
                "index": "getSamplingDate",
                "toggle": SamplingWorkflowEnabled}),
            ("getDateVerified", {
                "title": _("Date Verified"),
                "input_width": "10"}),
            ("getDatePreserved", {
                "title": _("Date Preserved"),
                "toggle": False,
                "input_class": "datetimepicker_nofuture",
                "input_width": "10",
                "sortable": False}),  # no datesort without index
            ("getPreserver", {
                "title": _("Preserver"),
                "sortable": False,
                "toggle": False}),
            ("getDatePublished", {
                "title": _("Date Published"),
                "toggle": False}),
            ("getAnalysesNum", {
                "title": _("Number of Analyses"),
                "sortable": True,
                "index": "getAnalysesNum",
                "toggle": False}),
            ("getTemplateTitle", {
                "title": _("Template"),
                "sortable": True,
                "index": "getTemplateTitle",
                "toggle": False}),
            ("Printed", {
                "title": _("Printed"),
                "sortable": False,
                "index": "getPrinted",
                "toggle": False}),
        ))

        # custom print transition
        print_stickers = {
            "id": "print_stickers",
            "title": _("Print stickers"),
            "url": "workflow_action?action=print_stickers"
        }

        sample_and_receive = {
            "id": "sample_and_receive",
            "title": _("Sample & Receive"),
            "url": "workflow_action?action=sample_and_receive"}

        self.review_states = [
            {
                "id": "default",
                "title": _("Active"),
                "contentFilter": {
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "sample"},
                    {"id": "preserve"},
                    {"id": "receive"},
                    {"id": "retract"},
                    {"id": "verify"},
                    {"id": "prepublish"},
                    {"id": "publish"},
                    {"id": "republish"},
                    {"id": "cancel"},
                    {"id": "reinstate"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "to_be_sampled",
                "title": _("To Be Sampled"),
                "contentFilter": {
                    "review_state": ("to_be_sampled",),
                    "sort_on": "created",
                    "sort_order": "descending"},
                "transitions": [
                    {"id": "sample"},
                    {"id": "submit"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys()
            }, {
                "id": "to_be_preserved",
                "title": _("To Be Preserved"),
                "contentFilter": {
                    "review_state": ("to_be_preserved",),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "preserve"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "scheduled_sampling",
                "title": _("Scheduled sampling"),
                "contentFilter": {
                    "review_state": ("scheduled_sampling",),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "sample"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "sample_due",
                "title": _("Due"),
                "contentFilter": {
                    "review_state": (
                        "to_be_sampled",
                        "to_be_preserved",
                        "sample_due"),
                    "sort_on": "created",
                    "sort_order": "descending"},
                "transitions": [
                    {"id": "sample"},
                    {"id": "preserve"},
                    {"id": "receive"},
                    {"id": "cancel"},
                    {"id": "reinstate"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "sample_received",
                "title": _("Received"),
                "contentFilter": {
                    "review_state": "sample_received",
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "prepublish"},
                    {"id": "cancel"},
                    {"id": "reinstate"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "to_be_verified",
                "title": _("To be verified"),
                "contentFilter": {
                    "review_state": "to_be_verified",
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "retract"},
                    {"id": "verify"},
                    {"id": "prepublish"},
                    {"id": "cancel"},
                    {"id": "reinstate"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "verified",
                "title": _("Verified"),
                "contentFilter": {
                    "review_state": "verified",
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "publish"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "published",
                "title": _("Published"),
                "contentFilter": {
                    "review_state": ("published", "invalid"),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "republish"},
                ],
                "custom_transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "unpublished",
                "title": _("Unpublished"),
                "contentFilter": {
                    "cancellation_state": "active",
                    "review_state": (
                        "sample_registered",
                        "to_be_sampled",
                        "to_be_preserved",
                        "sample_due",
                        "sample_received",
                        "to_be_verified",
                        "attachment_due",
                        "verified",
                    ),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "sample"},
                    {"id": "preserve"},
                    {"id": "receive"},
                    {"id": "retract"},
                    {"id": "verify"},
                    {"id": "prepublish"},
                    {"id": "publish"},
                    {"id": "republish"},
                    {"id": "cancel"},
                    {"id": "reinstate"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "cancelled",
                "title": _("Cancelled"),
                "contentFilter": {
                    "cancellation_state": "cancelled",
                    "review_state": (
                        "sample_registered",
                        "to_be_sampled",
                        "to_be_preserved",
                        "sample_due",
                        "sample_received",
                        "to_be_verified",
                        "attachment_due",
                        "verified",
                        "published",
                    ),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "reinstate"},
                ],
                "custom_transitions": [],
                "columns": self.columns.keys(),
            }, {
                "id": "invalid",
                "title": _("Invalid"),
                "contentFilter": {
                    "review_state": "invalid",
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "rejected",
                "title": _("Rejected"),
                "contentFilter": {
                    "review_state": "rejected",
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [],
                "custom_transitions": [
                    {
                        "id": "print_stickers",
                        "title": _("Print stickers"),
                        "url": "workflow_action?action=print_stickers"},
                ],
                "columns": self.columns.keys(),
            }, {
                "id": "assigned",
                "title": "<img title='%s' src='%s/++resource++bika.lims.images/assigned.png'/>" % (
                    t(_("Assigned")), self.portal_url),
                "contentFilter": {
                    "assigned_state": "assigned",
                    "cancellation_state": "active",
                    "review_state": ("sample_received",
                                     "attachment_due",),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "receive"},
                    {"id": "retract"},
                    {"id": "prepublish"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            }, {
                "id": "unassigned",
                "title": "<img title='%s' src='%s/++resource++bika.lims.images/unassigned.png'/>" % (
                    t(_("Unassigned")), self.portal_url),
                "contentFilter": {
                    "assigned_state": "unassigned",
                    "cancellation_state": "active",
                    "review_state": (
                        "sample_received",
                        "attachment_due",
                    ),
                    "sort_on": "created",
                    "sort_order": "descending",
                },
                "transitions": [
                    {"id": "receive"},
                    {"id": "retract"},
                    {"id": "prepublish"},
                    {"id": "cancel"},
                ],
                "custom_transitions": [print_stickers, sample_and_receive],
                "columns": self.columns.keys(),
            },
        ]

    def folderitem(self, obj, item, index):
        # Additional info from AnalysisRequest to be added in the item
        # generated by default by bikalisting.
        # Call the folderitem method from the base class
        item = ARV.folderitem(self, obj, item, index)
        if not item:
            return None
        # This variable will contain the full analysis request if there is
        # need to work with the full object instead of the brain
        full_object = None
        item["Creator"] = self.user_fullname(obj.Creator)
        # If we redirect from the folderitems view we should check if the
        # user has permissions to medify the element or not.
        priority_sort_key = obj.getPrioritySortkey
        if not priority_sort_key:
            # Default priority is Medium = 3.
            # The format of PrioritySortKey is <priority>.<created>
            priority_sort_key = "3.%s" % obj.created.ISO8601()
        priority = priority_sort_key.split(".")[0]
        priority_text = PRIORITIES.getValue(priority)
        priority_div = """<div class="priority-ico priority-%s">
                          <span class="notext">%s</span><div>
                       """
        item["replace"]["Priority"] = priority_div % (priority, priority_text)
        item["replace"]["getProfilesTitle"] = obj.getProfilesTitleStr

        analysesnum = obj.getAnalysesNum
        if analysesnum:
            num_verified = str(analysesnum[0])
            num_total = str(analysesnum[1])
            item["getAnalysesNum"] = "{0}/{1}".format(num_verified, num_total)
        else:
            item["getAnalysesNum"] = ""

        import pdb; pdb.set_trace()
        # if item['getStrain'] == '':
        #     bsc = getToolByName(self.context, 'bika_setup_catalog')
        #     strains = bsc(UID=obj.getObject().getSample()['Strain'])
        #     item['getStrain'] = strains[0].Title
        # Progress
        num_verified = 0
        num_submitted = 0
        num_total = 0
        if analysesnum and len(analysesnum) > 1:
            num_verified = analysesnum[0]
            num_total = analysesnum[1]
            num_submitted = num_total - num_verified
            if len(analysesnum) > 2:
                num_wo_results = analysesnum[2]
                num_submitted = num_total - num_verified - num_wo_results
        num_steps_total = num_total * 2
        num_steps = (num_verified * 2) + (num_submitted)
        progress_perc = 0
        if num_steps > 0 and num_steps_total > 0:
            progress_perc = (num_steps * 100) / num_steps_total
        progress = '<div class="progress-bar-container">' + \
                   '<div class="progress-bar" style="width:{0}%"></div>' + \
                   '<div class="progress-perc">{0}%</div></div>'
        item["replace"]["Progress"] = progress.format(progress_perc)

        item["BatchID"] = obj.getBatchID
        if obj.getBatchID:
            item['replace']['BatchID'] = "<a href='%s'>%s</a>" % \
                (obj.getBatchURL, obj.getBatchID)
        # TODO: SubGroup ???
        # val = obj.Schema().getField('SubGroup').get(obj)
        # item['SubGroup'] = val.Title() if val else ''

        date = obj.getSamplingDate
        item["SamplingDate"] = \
            self.ulocalized_time(date, long_format=1) if date else ""
        date = obj.getDateReceived
        item["getDateReceived"] = \
            self.ulocalized_time(date, long_format=1) if date else ""
        date = obj.getDatePublished
        item["getDatePublished"] = \
            self.ulocalized_time(date, long_format=1) if date else ""
        date = obj.getDateVerified
        item["getDateVerified"] = \
            self.ulocalized_time(date, long_format=1) if date else ""

        if self.printwfenabled:
            item["Printed"] = ""
            printed = obj.getPrinted if hasattr(obj, "getPrinted") else "0"
            print_icon = ""
            if printed == "0":
                print_icon = \
                    """<img src='%s/++resource++bika.lims.images/delete.png'
                        title='%s'>
                    """ % (self.portal_url, t(_("Not printed yet")))
            elif printed == "1":
                print_icon = \
                    """<img src='%s/++resource++bika.lims.images/ok.png'
                        title='%s'>
                    """ % (self.portal_url, t(_("Printed")))
            elif printed == "2":
                print_icon = \
                    """<img
                        src='%s/++resource++bika.lims.images/exclamation.png'
                            title='%s'>
                        """ \
                    % (self.portal_url, t(_("Republished after last print")))
            item["after"]["Printed"] = print_icon
        item["SamplingDeviation"] = obj.getSamplingDeviationTitle

        item["getStorageLocation"] = obj.getStorageLocationTitle

        after_icons = ""
        # Getting a dictionary with each workflow id and current state in it
        states_dict = obj.getObjectWorkflowStates
        if obj.assigned_state == 'assigned':
            after_icons += \
                """<img src='%s/++resource++bika.lims.images/worksheet.png'
                    title='%s'/>
                """ % (self.portal_url, t(_("All analyses assigned")))
        if states_dict.get('review_state', '') == 'invalid':
            after_icons += \
                """<img src='%s/++resource++bika.lims.images/delete.png'
                    title='%s'/>
                """ % (self.portal_url, t(_("Results have been withdrawn")))
        if obj.getLate:
            after_icons += \
                """<img src='%s/++resource++bika.lims.images/late.png'
                    title='%s'>
                """ % (self.portal_url, t(_("Late Analyses")))
        if obj.getSamplingDate and obj.getSamplingDate > DateTime():
            after_icons += \
                """<img src='%s/++resource++bika.lims.images/calendar.png'
                    title='%s'>
                """ % (self.portal_url, t(_("Future dated sample")))
        if obj.getInvoiceExclude:
            after_icons += \
                """<img
                    src='%s/++resource++bika.lims.images/invoice_exclude.png'
                    title='%s'>
                """ % (self.portal_url, t(_("Exclude from invoice")))
        if obj.getHazardous:
            after_icons += \
                """<img src='%s/++resource++bika.lims.images/hazardous.png'
                    title='%s'>
                """ % (self.portal_url, t(_("Hazardous")))
        if after_icons:
            item['after']['getId'] = after_icons

        item['Created'] = self.ulocalized_time(obj.created)
        if obj.getContactUID:
            item['ClientContact'] = obj.getContactFullName
            item['replace']['ClientContact'] = "<a href='%s'>%s</a>" % \
                (obj.getContactURL, obj.getContactFullName)
        else:
            item["ClientContact"] = ""
        # TODO-performance: If SamplingWorkflowEnabled, we have to get the
        # full object to check the user permissions, so far this is
        # a performance hit.
        if obj.getSamplingWorkflowEnabled:
            # We don't do anything with Sampling Date.
            # User can modify Sampling date
            # inside AR view. In this listing view,
            # we only let the user to edit Date Sampled
            # and Sampler if he wants to make 'sample' transaction.
            if not obj.getDateSampled:
                datesampled = self.ulocalized_time(
                    DateTime(), long_format=True)
                item["class"]["getDateSampled"] = "provisional"
            else:
                datesampled = self.ulocalized_time(obj.getDateSampled,
                                                   long_format=True)

            sampler = obj.getSampler
            if sampler:
                item["replace"]["getSampler"] = obj.getSamplerFullName
            if "Sampler" in self.roles and not sampler:
                sampler = self.member.id
                item["class"]["getSampler"] = "provisional"
            # sampling workflow - inline edits for Sampler and Date Sampled
            if states_dict.get('review_state', '') == 'to_be_sampled':
                # We need to get the full object in order to check
                # the permissions
                full_object = obj.getObject()
                checkPermission =\
                    self.context.portal_membership.checkPermission
                if checkPermission(SampleSample, full_object):
                    item["required"] = ["getSampler", "getDateSampled"]
                    item["allow_edit"] = ["getSampler", "getDateSampled"]
                    # TODO-performance: hit performance while getting the
                    # sample object...
                    # TODO Can LabManagers be a Sampler?!
                    samplers = getUsers(
                        full_object.getSample(),
                        ["Sampler", ])
                    username = self.member.getUserName()
                    users = [({
                        "ResultValue": u,
                        "ResultText": samplers.getValue(u)}) for u in samplers]
                    item['choices'] = {'getSampler': users}
                    Sampler = sampler and sampler or \
                        (username in samplers.keys() and username) or ''
                    sampler = Sampler
                else:
                    datesampled = self.ulocalized_time(obj.getDateSampled,
                                                       long_format=True)
                    sampler = obj.getSamplerFullName if obj.getSampler else ''
        else:
            datesampled = self.ulocalized_time(obj.getDateSampled,
                                               long_format=True)
            sampler = ""
        item["getDateSampled"] = datesampled
        item["getSampler"] = sampler

        # These don't exist on ARs
        # XXX This should be a list of preservers...
        item["getPreserver"] = ""
        item["getDatePreserved"] = ""
        # TODO-performance: If inline preservation wants to be used, we
        # have to get the full object to check the user permissions, so
        # far this is a performance hit.
        # inline edits for Preserver and Date Preserved
        # if checkPermission(PreserveSample, obj):
        #     item['required'] = ['getPreserver', 'getDatePreserved']
        #     item['allow_edit'] = ['getPreserver', 'getDatePreserved']
        #     preservers = getUsers(obj, ['Preserver',
        #                           'LabManager', 'Manager'])
        #     username = self.member.getUserName()
        #     users = [({'ResultValue': u,
        #                'ResultText': preservers.getValue(u)})
        #              for u in preservers]
        #     item['choices'] = {'getPreserver': users}
        #     preserver = username in preservers.keys() and username or ''
        #     item['getPreserver'] = preserver
        #     item['getDatePreserved'] = self.ulocalized_time(
        #         DateTime(),
        #         long_format=1)
        #     item['class']['getPreserver'] = 'provisional'
        #     item['class']['getDatePreserved'] = 'provisional'

        # Submitting user may not verify results
        # Thee conditions to improve performance, some functions to check
        # the condition need to get the full analysis request.
        if states_dict.get("review_state", "") == "to_be_verified":
            allowed = user.has_permission(
                VerifyPermission,
                username=self.member.getUserName())
            # TODO-performance: isUserAllowedToVerify getts all analysis
            # objects inside the analysis request.
            if allowed:
                # Gettin the full object if not get before
                full_object = full_object if full_object else obj.getObject()
                if not full_object.isUserAllowedToVerify(self.member):
                    item["after"]["state_title"] = \
                        """<img src='++resource++bika.lims.images/submitted-by-current-user.png'
                            title='%s'/>
                        """ % t(_("Cannot verify: Submitted by current user"))
        return item
