# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims import bikaMessageFactory as _, api
from bika.lims.browser.worksheet.views import AnalysesView as AV


class AnalysesView(AV):
    """ This renders the table for ManageResultsView.
    """

    def get_slot_header(self, item):
        """
        Generates a slot header (the first cell of the row) for the item
        :param item: the item for which the slot header is requested
        :return: the html contents to be displayed in the first cell of a slot
        """
        obj = item['obj']
        obj = api.get_object(obj)

        # TODO All contents below have to be refactored/cleaned-up!
        # fill the rowspan with a little table
        # parent is either an AR, a Worksheet, or a
        # ReferenceSample (analysis parent).
        parent = api.get_parent(obj)
        pos_text = """<table class='worksheet-position' width='100%%'
            cellpadding='0' cellspacing='0'
            style='padding-bottom:5px;'><tr>
            <td class='pos' rowspan='3'>%s</td>""" % item['Pos']

        if obj.portal_type == 'ReferenceAnalysis':
            pos_text += "<td class='pos_top'>%s</td>" % \
                    obj.getReferenceAnalysesGroupID()
        elif obj.portal_type == 'DuplicateAnalysis' and \
                obj.getAnalysis().portal_type == 'ReferenceAnalysis':
            pos_text += "<td class='pos_top'><a href='%s'>%s</a></td>" % \
                        (obj.aq_parent.absolute_url(), obj.aq_parent.id)
        else:
            pos_text += "<td class='pos_top'>{}</td>".format(
                                                parent.getClientReference())

        pos_text += "<td class='pos_top_icons' rowspan='3'>"
        if obj.portal_type == 'DuplicateAnalysis':
            pos_text += """<img title='%s'
            src='%s/++resource++bika.lims.images/duplicate.png'/>""" % (
                _("Duplicate").encode('utf-8'), self.context.absolute_url())
            pos_text += "<br/>"
        elif obj.portal_type == 'ReferenceAnalysis' \
                and obj.ReferenceType == 'b':
            pos_text += """<a href='%s'>
                <img title='%s'
                src='++resource++bika.lims.images/blank.png'></a>""" % (
                    parent.absolute_url(), parent.Title())
            pos_text += "<br/>"
        elif obj.portal_type == 'ReferenceAnalysis' \
                and obj.ReferenceType == 'c':
            pos_text += """<a href='%s'>
                <img title='%s'
                src='++resource++bika.lims.images/control.png'></a>""" % (
                    parent.absolute_url(), parent.Title())
            pos_text += "<br/>"
        if parent.portal_type == 'AnalysisRequest':
            sample = parent.getSample()
            pos_text += """<a href='%s'>
                <img title='%s'
                src='++resource++bika.lims.images/sample.png'></a>""" % (
                    sample.absolute_url(), sample.Title())
        pos_text += "</td></tr>"

        pos_text += "<tr><td>"
        if parent.portal_type == 'AnalysisRequest':
            pos_text += "<a href='%s'>%s</a>" % (
                parent.absolute_url(), parent.Title())
        elif parent.portal_type == 'ReferenceSample':
            pos_text += "<a href='%s'>%s</a>" % (
                parent.absolute_url(), parent.Title())
        elif obj.portal_type == 'DuplicateAnalysis':
            pos_text += "<a style='white-space:nowrap' href='%s'>%s</a>" % (
                obj.getAnalysis().aq_parent.absolute_url(),
                obj.getReferenceAnalysesGroupID())
        elif parent.portal_type == 'Worksheet':
            parent = obj.getAnalysis().aq_parent
            pos_text += "<a href='%s'>(%s)</a>" % (
                parent.absolute_url(), parent.Title())
        pos_text += "</td></tr>"

        # sampletype
        pos_text += "<tr><td>"
        if obj.portal_type == 'Analysis':
            pos_text += obj.aq_parent.getSample().getSampleType().Title()
        elif obj.portal_type == 'ReferenceAnalysis' or \
                (obj.portal_type == 'DuplicateAnalysis' and
                    obj.getAnalysis().portal_type == 'ReferenceAnalysis'):
            pos_text += ""  # obj.aq_parent.getReferenceDefinition().Title()
        elif obj.portal_type == 'DuplicateAnalysis':
            pos_text += \
                obj.getAnalysis().aq_parent.getSample().getSampleType().Title()
        pos_text += "</td></tr>"

        # samplingdeviation
        if obj.portal_type == 'Analysis':
            deviation = obj.aq_parent.getSample().getSamplingDeviation()
            if deviation:
                pos_text += "<tr><td>&nbsp;</td>"
                pos_text += "<td colspan='2'>"
                pos_text += deviation.Title()
                pos_text += "</td></tr>"

                # #            # barcode
                # #            barcode = parent.id.replace("-", "")
                # #            if obj.portal_type == 'DuplicateAnalysis':
                # #                barcode += "D"
                # #            pos_text += """<tr>
                # <td class='barcode' colspan='3'>
                # <div id='barcode_%s'></div>""" % barcode +
                # #                """<script type='text/javascript'>
                # $('#barcode_%s').barcode('%s',
                # 'code128',
                # {'barHeight':15, addQuietZone:false, showHRI: false })
                # </script>" % (barcode, barcode)""" + \
                # #                "</td></tr>"

        pos_text += "</table>"
        return pos_text
