from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestPublishView as ARPV
from ace.lims.vocabularies import  getACEARReportTemplates
from bika.lims import bikaMessageFactory as _, t
from bika.lims.utils import to_utf8, getUsers
from plone.app.content.browser.interfaces import IFolderContentsView
from zope.interface import implements

import os, traceback

class AnalysisRequestPublishView(ARPV):
    implements(IFolderContentsView)
    template = ViewPageTemplateFile("templates/analysisrequest_publish.pt")

    def getReportTemplate(self):
        """ Returns the html template for the current ar and moves to
            the next ar to be processed. Uses the selected template
            specified in the request ('template' parameter)
        """
        reptemplate = ""
        embedt = ""
        try:
            embedt, reptemplate = self._renderTemplate()
        except:
            tbex = traceback.format_exc()
            arid = self._ars[self._current_ar_index].id
            reptemplate = "<div class='error-report'>%s - %s '%s':<pre>%s</pre></div>" % (arid, _("Unable to load the template"), embedt, tbex)
        self._nextAnalysisRequest()
        return reptemplate

    def getReportStyle(self):
        """ Returns the css style to be used for the current template.
            If the selected template is 'default.pt', this method will
            return the content from 'default.css'. If no css file found
            for the current template, returns empty string
        """
        template = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        #template = 'default.pt'
        content = ''
        if template.find(':') >= 0:
            prefix, template = template.split(':')
            resource = queryResourceDirectory('reports', prefix)
            css = '{0}.css'.format(template[:-3])
            if css in resource.listDirectory():
                content = resource.readFile(css)
        else:
            this_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(this_dir, 'templates/reports/')
            path = '%s/%s.css' % (templates_dir, template[:-3])
            with open(path, 'r') as content_file:
                content = content_file.read()
        return content

    def _renderTemplate(self):
        """ Returns the html template to be rendered in accordance with the
            template specified in the request ('template' parameter)
        """
        templates_dir = 'templates/reports'
        embedt = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        #embedt = 'defuuuuu.pt'
        if embedt.find(':') >= 0:
            prefix, template = embedt.split(':')
            templates_dir = queryResourceDirectory('reports', prefix).directory
            embedt = template
        this_dir = os.path.dirname(os.path.abspath(__file__))
        #embed = ViewPageTemplateFile(os.path.join(this_dir, templates_dir, embedt))
        embed = ViewPageTemplateFile(os.path.join(templates_dir, embedt))
        #import pdb; pdb.set_trace()
        return embedt, embed(self)

    def getAvailableFormats(self):
        """ Returns the available formats found in templates/reports
        """
        return getACEARReportTemplates()

    def getAnalysisRequest(self, analysisrequest=None):
        """ Returns the dict for the Analysis Request specified. If no AR set,
            returns the current analysis request
        """
        return self._ar_data(analysisrequest) if analysisrequest \
                else self._ar_data(self._ars[self._current_ar_index])

    def _ar_data(self, ar, excludearuids=[]):
        """ Creates an ar dict, accessible from the view and from each
            specific template.
        """
        if ar.UID() in self._cache['_ar_data']:
            return self._cache['_ar_data'][ar.UID()]
        data = {'obj': ar,
                'id': ar.getRequestID(),
                'client_order_num': ar.getClientOrderNumber(),
                'client_reference': ar.getClientReference(),
                'client_sampleid': ar.getClientSampleID(),
                'adhoc': ar.getAdHoc(),
                'composite': ar.getComposite(),
                'report_drymatter': ar.getReportDryMatter(),
                'invoice_exclude': ar.getInvoiceExclude(),
                'date_received': self.ulocalized_time(ar.getDateReceived(), long_format=1),
                'member_discount': ar.getMemberDiscount(),
                'date_sampled': self.ulocalized_time(
                    ar.getDateSampled(), long_format=1),
                'date_published': self.ulocalized_time(DateTime(), long_format=1),
                'invoiced': ar.getInvoiced(),
                'late': ar.getLate(),
                'subtotal': ar.getSubtotal(),
                'vat_amount': ar.getVATAmount(),
                'totalprice': ar.getTotalPrice(),
                'invalid': ar.isInvalid(),
                'url': ar.absolute_url(),
                'remarks': to_utf8(ar.getRemarks()),
                'footer': to_utf8(self.context.bika_setup.getResultFooter()),
                'prepublish': False,
                'child_analysisrequest': None,
                'parent_analysisrequest': None,
                'resultsinterpretation':ar.getResultsInterpretation(),
                'lot': ar.Lot,
                'strain': '',
                'attachment_src': None,}

        # Sub-objects
        excludearuids.append(ar.UID())
        puid = ar.getRawParentAnalysisRequest()
        if puid and puid not in excludearuids:
            data['parent_analysisrequest'] = self._ar_data(ar.getParentAnalysisRequest(), excludearuids)
        cuid = ar.getRawChildAnalysisRequest()
        if cuid and cuid not in excludearuids:
            data['child_analysisrequest'] = self._ar_data(ar.getChildAnalysisRequest(), excludearuids)

        wf = getToolByName(ar, 'portal_workflow')
        allowed_states = ['verified', 'published']
        data['prepublish'] = wf.getInfoFor(ar, 'review_state') not in allowed_states

        data['contact'] = self._contact_data(ar)
        data['client'] = self._client_data(ar)
        data['sample'] = self._sample_data(ar)
        data['batch'] = self._batch_data(ar)
        data['specifications'] = self._specs_data(ar)
        data['analyses'] = self._analyses_data(ar, ['verified', 'published'])
        data['qcanalyses'] = self._qcanalyses_data(ar, ['verified', 'published'])
        data['points_of_capture'] = sorted(set([an['point_of_capture'] for an in data['analyses']]))
        data['categories'] = sorted(set([an['category'] for an in data['analyses']]))
        data['haspreviousresults'] = len([an['previous_results'] for an in data['analyses'] if an['previous_results']]) > 0
        data['hasblanks'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'b']) > 0
        data['hascontrols'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'c']) > 0
        data['hasduplicates'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'd']) > 0
        # Attachment src/link
        attachments = ar.getAttachment()
        for attachment in attachments:
            filename = attachment.getAttachmentFile().filename 
            extension = filename.split('.')[-1]
            if extension in ['png', 'jpg']: #Check other image extensions
                file_url =  attachment.getAttachmentFile().absolute_url()
                data['attachment_src'] = '{}/{}'.format(file_url, filename)

        # Categorize analyses
        data['categorized_analyses'] = {}
        data['department_analyses'] = {}
        for an in data['analyses']:
            poc = an['point_of_capture']
            cat = an['category']
            pocdict = data['categorized_analyses'].get(poc, {})
            catlist = pocdict.get(cat, [])
            catlist.append(an)
            pocdict[cat] = catlist
            data['categorized_analyses'][poc] = pocdict

            # Group by department too
            anobj = an['obj']
            dept = anobj.getService().getDepartment() if anobj.getService() else None
            if dept:
                dept = dept.UID()
                dep = data['department_analyses'].get(dept, {})
                dep_pocdict = dep.get(poc, {})
                dep_catlist = dep_pocdict.get(cat, [])
                dep_catlist.append(an)
                dep_pocdict[cat] = dep_catlist
                dep[poc] = dep_pocdict
                data['department_analyses'][dept] = dep

        # Categorize qcanalyses
        data['categorized_qcanalyses'] = {}
        for an in data['qcanalyses']:
            qct = an['reftype']
            poc = an['point_of_capture']
            cat = an['category']
            qcdict = data['categorized_qcanalyses'].get(qct, {})
            pocdict = qcdict.get(poc, {})
            catlist = pocdict.get(cat, [])
            catlist.append(an)
            pocdict[cat] = catlist
            qcdict[poc] = pocdict
            data['categorized_qcanalyses'][qct] = qcdict

        data['reporter'] = self._reporter_data(ar)
        data['managers'] = self._managers_data(ar)

        portal = self.context.portal_url.getPortalObject()
        data['portal'] = {'obj': portal,
                          'url': portal.absolute_url()}
        data['laboratory'] = self._lab_data()

        #results interpretation
        ri = {}
        if (ar.getResultsInterpretationByDepartment(None)):
            ri[''] = ar.getResultsInterpretationByDepartment(None)
        depts = ar.getDepartments()
        for dept in depts:
            ri[dept.Title()] = ar.getResultsInterpretationByDepartment(dept)
        data['resultsinterpretationdepts'] = ri

        self._cache['_ar_data'][ar.UID()] = data
        return data

    def format_address(self, address):
        if address:
            _keys = ['address', 'city', 'district', 'state', 'zip', 'country']
            _list = ["<span>%s </span>" % address.get(v) for v in _keys
                     if address.get(v)]
            return ''.join(_list)
        return ''

    def _lab_data(self):
        portal = self.context.portal_url.getPortalObject()
        lab = self.context.bika_setup.laboratory
        mtool = getToolByName(self, 'portal_membership')
        users = mtool.searchForMembers(roles=['LabManager'])
        lab_manager = ''
        for user in users:
            uid = user.getId()
            lab_manager = user.getProperty('fullname')
            break


        return {'obj': lab,
                'title': to_utf8(lab.Title()),
                'url': to_utf8(lab.getLabURL()),
                'address': to_utf8(self._lab_address(lab)),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url(),
                'lab_manager': to_utf8(lab_manager),
                'today':self.ulocalized_time(DateTime(), long_format=0),}

    def publishFromHTML(self, aruid, results_html):
        import pdb; pdb.set_trace()
