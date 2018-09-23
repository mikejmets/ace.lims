from ace.lims.utils import attachCSV, createPdf, isOutOfRange
from ace.lims.vocabularies import getACEARReportTemplates
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims import logger
from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestPublishView as ARPV
from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestDigester as ARD
from bika.lims.browser import BrowserView, ulocalized_time
from bika.lims.idserver import renameAfterCreation
# from bika.lims.idserver import generateUniqueId
# from bika.lims.interfaces import IResultOutOfRange
from bika.lims.utils import to_utf8, encode_header, attachPdf
# from bika.lims.utils import convert_unit
from bika.lims.utils import dicts_to_dict
from bika.lims.workflow import wasTransitionPerformed
from DateTime import DateTime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formataddr
# from plone import api as ploneapi
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.resource.utils import queryResourceDirectory
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.utils import getToolByName
# from Products.CMFPlone.utils import safe_unicode, _createObjectByType
from Products.CMFPlone.utils import _createObjectByType
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from smtplib import SMTPServerDisconnected, SMTPRecipientsRefused
from zope.interface import implements
# from zope.component import getAdapters


import App
import StringIO
import csv
import os
import traceback
import tempfile


class AnalysisRequestPublishView(ARPV):
    implements(IFolderContentsView)
    template = ViewPageTemplateFile("templates/analysisrequest_publish.pt")

    def __init__(self, context, request, publish=False):
        BrowserView.__init__(self, context, request)
        self.context = context
        self.request = request
        self._publish = publish
        self._ars = [self.context]
        self._digester = AnalysisRequestDigester()

    def __call__(self):
        if self.context.portal_type == 'AnalysisRequest':
            self._ars = [self.context]
        elif self.context.portal_type in ('AnalysisRequestsFolder', 'Client') \
                and self.request.get('items', ''):
            uids = self.request.get('items').split(',')
            uc = getToolByName(self.context, 'uid_catalog')
            self._ars = [obj.getObject() for obj in uc(UID=uids)]
        else:
            # Do nothing
            self.destination_url = self.request.get_header(
                "referer", self.context.absolute_url())

        # Group ARs by client
        groups = {}
        for ar in self._ars:
            idclient = ar.aq_parent.id
            if idclient not in groups:
                groups[idclient] = [ar]
            else:
                groups[idclient].append(ar)
        self._arsbyclient = [group for group in groups.values()]

        # Report may want to print current date
        self.current_date = self.ulocalized_time(DateTime(), long_format=True)

        # Do publish?
        if self.request.form.get('publish', '0') == '1':
            self.publishFromPOST()
        else:
            return self.template()

    def getReportTemplate(self):
        """Returns the html template for the current ar and moves to
        the next ar to be processed. Uses the selected template
        specified in the request ('template' parameter)
        """
        embedt = ""
        try:
            embedt, reptemplate = self._renderTemplate()
        except:
            tbex = traceback.format_exc()
            arid = self._ars[self._current_ar_index].id
            reptemplate = \
                "<div class='error-report'>%s - %s '%s':<pre>%s</pre></div>" \
                % (arid, _("Unable to load the template"), embedt, tbex)
        self._nextAnalysisRequest()
        return reptemplate

    def getReportStyle(self):
        """Returns the css style to be used for the current template.
        If the selected template is 'default.pt', this method will
        return the content from 'default.css'. If no css file found
        for the current template, returns empty string
        """
        template = self.request.form.get('template', self._DEFAULT_TEMPLATE)
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
        """Returns the html template to be rendered in accordance with the
        template specified in the request ('template' parameter)
        """
        templates_dir = 'templates/reports'
        embedt = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        if embedt.find(':') >= 0:
            prefix, template = embedt.split(':')
            templates_dir = queryResourceDirectory('reports', prefix).directory
            embedt = template
        embed = ViewPageTemplateFile(os.path.join(templates_dir, embedt))
        return embedt, embed(self)

    def getAvailableFormats(self):
        """ Returns the available formats found in templates/reports
        """
        return getACEARReportTemplates()

    def getAnalysisRequest(self, analysisrequest=None):
        """Returns the dict for the Analysis Request specified. If no AR set,
        returns the current analysis request
        """
        if analysisrequest:
            return self._digester(analysisrequest)
        else:
            return self._digester(self._ars[self._current_ar_index])

    def format_address(self, address):
        if address:
            _keys = ['address', 'city', 'district', 'state', 'zip', 'country']
            _list = ["<span>%s </span>" % address.get(v) for v in _keys
                     if address.get(v)]
            return ''.join(_list)
        return ''

    def sorted_by_sort_key(self, category_keys):
        """ Sort categories via catalog lookup on title. """
        bsc = getToolByName(self.context, "bika_setup_catalog")
        analysis_categories = bsc(portal_type="AnalysisCategory", sort_on="sortable_title")
        sort_keys = dict([(b.Title, "{:04}".format(a)) for a, b in enumerate(analysis_categories)])
        return sorted(category_keys, key=lambda title, sk=sort_keys: sk.get(title))

    def publishFromHTML(self, aruid, results_html):
        # The AR can be published only and only if allowed
        uc = getToolByName(self.context, 'uid_catalog')
        ars = [p.getObject() for p in uc(UID=aruid)]
        if not ars or len(ars) != 1:
            return []

        ar = ars[0]
        wf = getToolByName(ar, 'portal_workflow')
        allowed_states = ['verified', 'published']
        # Publish/Republish allowed?
        if wf.getInfoFor(ar, 'review_state') not in allowed_states:
            # Pre-publish allowed?
            if not ar.getAnalyses(review_state=allowed_states):
                return []

        # HTML written to debug file
        debug_mode = App.config.getConfiguration().debug_mode
        if debug_mode:
            tmp_fn = tempfile.mktemp(suffix=".html")
            logger.debug("Writing HTML for %s to %s" % (ar.Title(), tmp_fn))
            open(tmp_fn, "wb").write(results_html)

        # Create the pdf report (will always be attached to the AR)
        # we must supply the file ourself so that createPdf leaves it alone.
        pdf_fn = tempfile.mktemp(suffix=".pdf")

        # PDF written to debug file
        if debug_mode:
            logger.debug("Writing PDF for %s to %s" % (ar.Title(), pdf_fn))
        else:
            if os.path.exists(pdf_fn):
                os.remove(pdf_fn)

        recipients = []
        contact = ar.getContact()
        lab = ar.bika_setup.laboratory

        # BIKA Cannabis hack.  Create the CSV they desire here now
        # csvdata = self.create_cannabis_csv(ars)
        csvdata = self.create_metrc_csv(ars)
        if contact:
            recipients = [{
                'UID': contact.UID(),
                'Username': to_utf8(contact.getUsername()),
                'Fullname': to_utf8(contact.getFullname()),
                'EmailAddress': to_utf8(contact.getEmailAddress()),
                'PublicationModes': contact.getPublicationPreference()
            }]
        reportid = ar.generateUniqueId('ARReport')
        report = _createObjectByType("ARReport", ar, reportid)
        report.edit(
            AnalysisRequest=ar.UID(),
        )
        report.unmarkCreationFlag()
        renameAfterCreation(report)
        fn = report.getId()
        reports_link = "<a href='{}'>{}</a>".format(ar.absolute_url(), fn)
        coa_nr_text = 'COA ID is generated on publication'
        results_html = results_html.replace(coa_nr_text, reports_link)
        # Create the pdf report for the supplied HTML.
        pdf_report = createPdf(results_html, False)
        report.edit(
            Pdf=pdf_report,
            Recipients=recipients,
            CSV=csvdata,
            Html=results_html,
        )
        fld = report.getField('Pdf')
        fld.get(report).setFilename(fn + ".pdf")
        fld.get(report).setContentType('application/pdf')
        fld = report.getField('CSV')
        fld.get(report).setFilename(fn + ".csv")
        fld.get(report).setContentType('text/csv')

        # Set status to prepublished/published/republished
        status = wf.getInfoFor(ar, 'review_state')
        transitions = {'verified': 'publish',
                       'published': 'republish'}
        transition = transitions.get(status, 'prepublish')
        try:
            wf.doActionFor(ar, transition)
        except WorkflowException:
            pass

        # compose and send email.
        # The managers of the departments for which the current AR has
        # at least one AS must receive always the pdf report by email.
        # https://github.com/bikalabs/Bika-LIMS/issues/1028
        mime_msg = MIMEMultipart('related')
        mime_msg['Subject'] = self.get_mail_subject(ar)[0]
        mime_msg['From'] = formataddr(
            (encode_header(lab.getName()), lab.getEmailAddress()))
        mime_msg.preamble = 'This is a multi-part MIME message.'
        msg_txt = MIMEText(results_html, _subtype='html')
        mime_msg.attach(msg_txt)

        # Send report to recipients
        recips = self.get_recipients(ar)
        for recip in recips:
            if 'email' not in recip.get('pubpref', []) \
                    or not recip.get('email', ''):
                continue

            title = encode_header(recip.get('title', ''))
            email = recip.get('email')
            formatted = formataddr((title, email))

            # Create the new mime_msg object, cause the previous one
            # has the pdf already attached
            mime_msg = MIMEMultipart('related')
            mime_msg['Subject'] = self.get_mail_subject(ar)[0]
            mime_msg['From'] = formataddr(
                (encode_header(lab.getName()), lab.getEmailAddress()))
            mime_msg.preamble = 'This is a multi-part MIME message.'
            msg_txt = MIMEText(results_html, _subtype='html')
            mime_msg.attach(msg_txt)
            mime_msg['To'] = formatted

            # Attach the pdf to the email if requested
            if pdf_report and 'pdf' in recip.get('pubpref'):
                attachPdf(mime_msg, pdf_report, pdf_fn)
                # BIKA Cannabis hack.  Create the CSV they desire here now
                fn = pdf_fn
                attachCSV(mime_msg, csvdata, fn)

            # For now, I will simply ignore mail send under test.
            if hasattr(self.portal, 'robotframework'):
                continue

            msg_string = mime_msg.as_string()

            # content of outgoing email written to debug file
            if debug_mode:
                tmp_fn = tempfile.mktemp(suffix=".email")
                logger.debug("Writing MIME message for %s to %s" % (ar.Title(), tmp_fn))
                open(tmp_fn, "wb").write(msg_string)

            try:
                host = getToolByName(ar, 'MailHost')
                host.send(msg_string, immediate=True)
            except SMTPServerDisconnected as msg:
                logger.warn("SMTPServerDisconnected: %s." % msg)
            except SMTPRecipientsRefused as msg:
                raise WorkflowException(str(msg))

        return [ar]

    def create_cannabis_csv(self, ars):
        analyses = []
        output = StringIO.StringIO()
        for ar in ars:
            sample = ar.getSample()
            date_rec = ar.getDateReceived()
            if date_rec:
                date_rec = date_rec.strftime('%m-%d-%y')
            sampling_date = ar.getSamplingDate()
            if sampling_date:
                sampling_date = sampling_date.strftime('%m-%d-%y')
            writer = csv.writer(output)
            writer.writerow(["Sample Type", sample.getSampleType().Title()])
            writer.writerow(["Client's Ref", ar.getClientReference()])
            writer.writerow(["Client's Sample ID", sample.getClientSampleID()])
            writer.writerow(["Lab Sample ID", sample.id])
            writer.writerow(["Date Received", date_rec])
            writer.writerow(["Sampling Date", sampling_date])
            writer.writerow([])
            analyses = ar.getAnalyses(full_objects=True)
            group_cats = {}
            for analysis in analyses:
                analysis_info = {'title': analysis.Title(),
                                 'result': analysis.getFormattedResult(html=False),
                                 'unit': analysis.getService().getUnit()}
                if analysis.getCategoryTitle() not in group_cats.keys():
                    group_cats[analysis.getCategoryTitle()] = []
                group_cats[analysis.getCategoryTitle()].append(analysis_info)

            for g_cat in sorted(group_cats.keys()):
                writer.writerow([g_cat])
                writer.writerow(["Analysis", "Result", "Unit"])
                for a_info in group_cats[g_cat]:
                    writer.writerow([a_info['title'], a_info['result'], a_info['unit']])

        return output.getvalue()

    def create_metrc_csv(self, ars):
        analyses = []
        output = StringIO.StringIO()
        writer = csv.writer(output)
        for ar in ars:
            ar_id = ar.id
            date_published = ar.getDatePublished()
            if date_published:
                date_published = ulocalized_time(date_published,
                                                 long_format=False,
                                                 context=self.context)
            else:
                date_published = ulocalized_time(DateTime(),
                                                 long_format=False,
                                                 context=self.context)

            client_sampleid = to_utf8(ar.getClientSampleID())
            # as_keyword = ''
            result = ''
            is_in_range = 'True'
            unit_and_ar_id = ''
            # sample_type_uid = ar.getSampleType().UID()
            # bsc = getToolByName(self, 'bika_setup_catalog')
            # analysis_specs = bsc(portal_type='AnalysisSpec',
            #              getSampleTypeUID=sample_type_uid)
            # dmk = ar.bika_setup.getResultsDecimalMark()

            lines = []
            analyses = ar.getAnalyses(full_objects=True)
            for analysis in analyses:
                service = analysis.getAnalysisService()
                if service.getHidden():
                    continue
                specification = analysis.getResultsRange()
                result = analysis.getFormattedResult(html=False)
                if not specification:
                    rr = dicts_to_dict(analysis.aq_parent.getResultsRange(), 'keyword')
                    specification = rr.get(analysis.getKeyword(), None)
                    # No specs available, assume in range:
                    if not specification:
                        is_in_range = True
                else:
                    minimum = specification.get('min', '')
                    maximum = specification.get('max', '')
                    error = specification.get('error', '')
                    if minimum == '' and maximum == '' and error == '':
                        is_in_range = True
                    else:
                        outofrange, acceptable = \
                            isOutOfRange(result, minimum, maximum, error)
                        if outofrange is False:
                            is_in_range = True
                        elif outofrange is True:
                            is_in_range = False

                unit = service.getUnit()
                unit = '({})-'.format(unit) if unit else ''
                unit_and_ar_id = '{}{}'.format(unit, ar_id)

                # #Check unit conversion
                # if sample_type_uid:
                #     i = 0
                #     new_text = []
                #     hide_original = False
                #     an_dict = {'converted_units': []}
                #     # for unit_conversion in service.getUnitConversions():
                #     #     if unit_conversion.get('SampleType') and \
                #     #        unit_conversion.get('Unit') and \
                #     #        unit_conversion.get('SampleType') == sample_type_uid:
                #     #         i += 1
                #     #         new = dict({})
                #     #         conv = ploneapi.content.get(
                #     #                             UID=unit_conversion['Unit'])
                #     #         unit_and_ar_id = '({})-{}'.format(
                #     #                                 conv.converted_unit, ar_id)
                #     #         result = convert_unit(
                #     #                         analysis.getResult(),
                #     #                         conv.formula,
                #     #                         analysis.getPrecision())
                #     #         break

                line = {'date_published': date_published,
                        'client_sampleid': client_sampleid,
                        'as_keyword': service.getShortTitle(),
                        'result': result,
                        'is_in_range': is_in_range,
                        'unit_and_ar_id': unit_and_ar_id,
                        }
                lines.append(line)

            for l in lines:
                writer.writerow([l['date_published'], l['client_sampleid'],
                                 l['as_keyword'], l['result'],
                                 l['is_in_range'], l['unit_and_ar_id'],
                                 ])

        return output.getvalue()


class AnalysisRequestDigester(ARD):

    def __call__(self, ar, overwrite=False):
        # cheating
        self.context = ar
        self.request = ar.REQUEST
        # self._cache = {}

        # if AR was previously digested, use existing data (if exists)
        verified = wasTransitionPerformed(ar, 'verify')
        if not overwrite and verified:
            # Prevent any error related with digest
            data = ar.getDigest() if hasattr(ar, 'getDigest') else {}
            if False:  # data:
                # Check if the department managers have changed since
                # verification:
                saved_managers = data.get('managers', {})
                saved_managers_ids = set(saved_managers.get('ids', []))
                current_managers = self.context.getManagers()
                current_managers_ids = set([man.getId() for man in
                                            current_managers])
                # The symmetric difference of two sets A and B is the set of
                # elements which are in either of the sets A or B but not
                # in both.
                are_different = saved_managers_ids.symmetric_difference(
                    current_managers_ids)
                if len(are_different) == 0:
                    # Seems that sometimes the 'obj' is wrong in the saved
                    # data.
                    data['obj'] = ar
                    # Always set results interpretation
                    self._set_results_interpretation(ar, data)
                    return data

        logger.info("=========== creating new data for %s" % ar)

        # Set data to the AR schema field, and return it.
        data = self._ar_data(ar)
        if hasattr(ar, 'setDigest'):
            ar.setDigest(data)
        logger.info("=========== new data for %s created." % ar)
        return data

    def _ar_data(self, ar, excludearuids=None):
        """ Creates an ar dict, accessible from the view and from each
            specific template.
        """
        if not excludearuids:
            excludearuids = []
        bs = ar.bika_setup
        bsc = getToolByName(self.context, 'bika_setup_catalog')
        strain = ''
        strains = bsc(UID=ar.getSample()['Strain'])
        if strains:
            strain = strains[0].Title

        client_lic_type = client_lic_id = lic_number = issuing_auth = ''
        # client_licence_id = ar.getClientLicenceID().split(',')
        client_licence_id = ar.ClientLicenceID.split(',')
        if len(client_licence_id) == 4:
            client_lic_type = client_licence_id[0]  # LicenceType
            client_lic_id = client_licence_id[1]  # LicenceID
            lic_number = client_licence_id[2]  # LicenceNumber
            issuing_auth = client_licence_id[3]  # Issuing Authority
        data = {'obj': ar,
                'id': ar.getId(),
                'client_order_num': ar.getClientOrderNumber(),
                'client_reference': ar.getClientReference(),
                'client_sampleid': ar.getClientSampleID(),
                'adhoc': ar.getAdHoc(),
                'composite': ar.getComposite(),
                'invoice_exclude': ar.getInvoiceExclude(),
                'sampling_date': ulocalized_time(ar.getSamplingDate(),
                                                 long_format=1,
                                                 context=self.context),
                'date_received': ulocalized_time(ar.getDateReceived(),
                                                 long_format=1),
                'member_discount': ar.getMemberDiscount(),
                'date_sampled': ulocalized_time(
                    ar.getDateSampled(), long_format=1),
                'date_published': ulocalized_time(DateTime(), long_format=1),
                'invoiced': ar.getInvoiced(),
                'late': ar.getLate(),
                'subtotal': ar.getSubtotal(),
                'vat_amount': ar.getVATAmount(),
                'totalprice': ar.getTotalPrice(),
                'invalid': ar.isInvalid(),
                'url': ar.absolute_url(),
                'remarks': to_utf8(ar.getRemarks()),
                'footer': to_utf8(bs.getResultFooter()),
                'prepublish': False,
                # 'child_analysisrequest': None,
                # 'parent_analysisrequest': None,
                # 'resultsinterpretation': ar.getResultsInterpretation(),
                'ar_attachments': self._get_ar_attachments(ar),
                'an_attachments': self._get_an_attachments(ar),
                'lot': ar['Lot'],  # To be fixed
                'strain': strain,  # To be fixed
                'cultivation_batch': ar['CultivationBatch'],
                'issuing_auth': issuing_auth,
                'client_lic_type': client_lic_type,
                'client_lic_id': client_lic_id,
                'lic_number': lic_number,
                'published': False,
                }

        # Sub-objects
        # excludearuids.append(ar.UID())
        # puid = ar.getRawParentAnalysisRequest()
        # if puid and puid not in excludearuids:
        #     data['parent_analysisrequest'] = self._ar_data(
        #         ar.getParentAnalysisRequest(), excludearuids)
        # cuid = ar.getRawChildAnalysisRequest()
        # if cuid and cuid not in excludearuids:
        #     data['child_analysisrequest'] = self._ar_data(
        #         ar.getChildAnalysisRequest(), excludearuids)

        wf = ar.portal_workflow
        allowed_states = ['verified', 'published']
        data['prepublish'] = wf.getInfoFor(ar,
                                           'review_state') not in allowed_states

        data['contact'] = self._contact_data(ar)
        data['client'] = self._client_data(ar)
        data['sample'] = self._sample_data(ar)
        data['batch'] = self._batch_data(ar)
        data['specifications'] = self._specs_data(ar)
        data['analyses'] = self._analyses_data(ar, ['verified', 'published'])
        data['hasinterimfields'] = len(
            [an['interims'] for an in data['analyses'] if
             len(an['interims']) > 0]) > 0
        data['qcanalyses'] = self._qcanalyses_data(ar,
                                                   ['verified', 'published'])
        data['points_of_capture'] = sorted(
            set([an['point_of_capture'] for an in data['analyses']]))
        data['categories'] = sorted(
            set([an['category'] for an in data['analyses']]))
        data['haspreviousresults'] = len(
            [an['previous_results'] for an in data['analyses'] if
             an['previous_results']]) > 0
        data['hasblanks'] = len([an['reftype'] for an in data['qcanalyses'] if
                                 an['reftype'] == 'b']) > 0
        data['hascontrols'] = len([an['reftype'] for an in data['qcanalyses'] if
                                   an['reftype'] == 'c']) > 0
        data['hasduplicates'] = len(
            [an['reftype'] for an in data['qcanalyses'] if
             an['reftype'] == 'd']) > 0

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
            dept = anobj.getDepartment()
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
        data['product'] = self._sample_type(ar).get('title', '')

        wf = getToolByName(ar, 'portal_workflow')
        allowed_states = ['verified', 'published']
        data['prepublish'] = wf.getInfoFor(ar, 'review_state') not in allowed_states
        if wf.getInfoFor(ar, 'review_state') == 'published':
            data['published'] = True

        # results interpretation
        data = self._set_results_interpretation(ar, data)

        return data

    def _lab_data(self):
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        bsc = getToolByName(self.context, "bika_setup_catalog")
        lab = self.context.bika_setup.laboratory
        sv = lab.getSupervisor()
        labcontacts = bsc(portal_type="LabContact", id=sv)
        signature = None
        lab_manager = ''
        if len(labcontacts) == 1:
            labcontact = api.get_object(labcontacts[0])
            lab_manager_name = to_utf8(self.user_fullname(labcontact.getUsername()))
            lab_manager_job_title = to_utf8(labcontact.getJobTitle())
            lab_manager = '{} {}'.format(lab_manager_name, lab_manager_job_title)

            if labcontact.getSignature():
                signature_url = labcontact.getSignature().absolute_url()
                signature = '{}/Signature'.format(signature_url)

        lab = self.context.bika_setup.laboratory
        sv = lab.getSupervisor()
        sv_fullname = sv.getFullname() if sv else ""
        sv_email = sv.getEmailAddress() if sv else ""
        sv_mphone = sv.getMobilePhone() if sv else ""
        return {'obj': lab,
                'title': to_utf8(lab.Title()),
                'url': to_utf8(lab.getLabURL()),
                'phone': to_utf8(lab.getPhone()),
                'email': to_utf8(lab.getEmailAddress()),
                'lab_licence_id': to_utf8(lab.LaboratoryLicenceID),
                'supervisor': to_utf8(sv_fullname),
                'supervisor_email': to_utf8(sv_email),
                'supervisor_mphone': to_utf8(sv_mphone),
                'address': to_utf8(self._lab_address(lab)),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url(),
                'lab_manager': to_utf8(lab_manager),
                'signature': signature,
                'today': ulocalized_time(DateTime(),
                                         long_format=0,
                                         context=self.context),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url()}

    def _contact_data(self, ar):
        data = {}
        contact = ar.getContact()
        if contact:
            data = {'obj': contact,
                    'fullname': to_utf8(contact.getFullname()),
                    'email': to_utf8(contact.getEmailAddress()),
                    'mobile_phone': to_utf8(contact.getMobilePhone()) if contact else '',
                    'pubpref': contact.getPublicationPreference()}
        return data

    def _managers_data(self, ar):
        managers = {'ids': [], 'dict': {}}
        departments = {}
        ar_mngrs = ar.getResponsible()
        for id in ar_mngrs['ids']:
            new_depts = ar_mngrs['dict'][id]['departments'].split(',')
            if id in managers['ids']:
                for dept in new_depts:
                    if dept not in departments[id]:
                        departments[id].append(dept)
            else:
                departments[id] = new_depts
                managers['ids'].append(id)
                managers['dict'][id] = ar_mngrs['dict'][id]

        mngrs = departments.keys()
        for mngr in mngrs:
            final_depts = ''
            for dept in departments[mngr]:
                if final_depts:
                    final_depts += ', '
                final_depts += to_utf8(dept)
            managers['dict'][mngr]['departments'] = final_depts

        return managers
