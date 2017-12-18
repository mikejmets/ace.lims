from DateTime import DateTime
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode, _createObjectByType
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from ace.lims.utils import attachCSV, createPdf, isOutOfRange
from ace.lims.vocabularies import  getACEARReportTemplates
from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestPublishView as ARPV
from bika.lims.idserver import renameAfterCreation
from bika.lims import bikaMessageFactory as _, t
from bika.lims import logger
from bika.lims.idserver import generateUniqueId
from bika.lims.utils import to_utf8, encode_header, attachPdf
from bika.lims.utils import convert_unit
from bika.lims.utils import dicts_to_dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formataddr
from smtplib import SMTPServerDisconnected, SMTPRecipientsRefused
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.resource.utils import  queryResourceDirectory
from zope.interface import implements
from zope.component import getAdapters
from bika.lims.interfaces import IResultOutOfRange

from plone import api as ploneapi

import App
import StringIO
import csv
import os, traceback
import tempfile
import time

class AnalysisRequestPublishView(ARPV):
    implements(IFolderContentsView)
    template = ViewPageTemplateFile("templates/analysisrequest_publish.pt")

    def __call__(self):
        if self.context.portal_type == 'AnalysisRequest':
            self._ars = [self.context]
        elif self.context.portal_type == 'AnalysisRequestsFolder' \
            and self.request.get('items',''):
            uids = self.request.get('items').split(',')
            uc = getToolByName(self.context, 'uid_catalog')
            self._ars = [obj.getObject() for obj in uc(UID=uids)]
        else:
            #Do nothing
            self.destination_url = self.request.get_header("referer",
                                   self.context.absolute_url())

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
        if embedt.find(':') >= 0:
            prefix, template = embedt.split(':')
            templates_dir = queryResourceDirectory('reports', prefix).directory
            embedt = template
        this_dir = os.path.dirname(os.path.abspath(__file__))
        embed = ViewPageTemplateFile(os.path.join(templates_dir, embedt))
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
        #Not sure why the following 2 lines are need, doing ar.getStrain or ar.getSample().getStrain does not work
        strain = ''
        bsc =  self.bika_setup_catalog
        strains = bsc(UID=ar.getSample()['Strain'])
        if strains:
             strain = strains[0].Title

        mme_id = state_id = ''
        client_state_lincense_id = ar.getClientStateLicenseID().split(',')
        if len(client_state_lincense_id) == 4:
            mme_id = client_state_lincense_id[1] #LicenseID
            state_id = client_state_lincense_id[2] #LicenseNumber
        data = {'obj': ar,
                'id': ar.getRequestID(),
                #'client_order_num': ar.getClientOrderNumber(),
                'client_reference': ar.getClientReference(),
                'client_sampleid': ar.getClientSampleID(),
                #'adhoc': ar.getAdHoc(),
                #'composite': ar.getComposite(),
                #'report_drymatter': ar.getReportDryMatter(),
                #'invoice_exclude': ar.getInvoiceExclude(),
                'sampling_date': self.ulocalized_time(
                    ar.getSamplingDate(), long_format=1),
                'date_received': self.ulocalized_time(
                    ar.getDateReceived(), long_format=1),
                #'member_discount': ar.getMemberDiscount(),
                'date_sampled': self.ulocalized_time(
                    ar.getDateSampled(), long_format=1),
                'date_published': self.ulocalized_time(DateTime(), long_format=1),
                #'invoiced': ar.getInvoiced(),
                #'late': ar.getLate(),
                #'subtotal': ar.getSubtotal(),
                #'vat_amount': ar.getVATAmount(),
                #'totalprice': ar.getTotalPrice(),
                'invalid': ar.isInvalid(),
                'url': ar.absolute_url(),
                'remarks': to_utf8(ar.getRemarks().replace('\n', '').replace("===", "<br/>")),
                'footer': to_utf8(self.context.bika_setup.getResultFooter()),
                'prepublish': False,
                'published': False,
                #'child_analysisrequest': None,
                #'parent_analysisrequest': None,
                #'resultsinterpretation':ar.getResultsInterpretation(),
                'lot': ar['Lot'],#To be fixed
                'strain': strain, # To be fixed
                'cultivation_batch': ar['CultivationBatch'],
                #'resultsinterpretation':ar.getResultsInterpretation(),
                'ar_attachments': self._get_ar_attachments(ar),
                'an_attachments': self._get_an_attachments(ar),
                'attachment_src': None,
                'attachment_width': None,
                'attachment_height': None,
                'mme_id': mme_id,
                'state_id': state_id,}

        # Sub-objects
        #excludearuids.append(ar.UID())
        #puid = ar.getRawParentAnalysisRequest()
        #if puid and puid not in excludearuids:
        #    data['parent_analysisrequest'] = self._ar_data(ar.getParentAnalysisRequest(), excludearuids)
        #cuid = ar.getRawChildAnalysisRequest()
        #if cuid and cuid not in excludearuids:
        #    data['child_analysisrequest'] = self._ar_data(ar.getChildAnalysisRequest(), excludearuids)

        wf = getToolByName(ar, 'portal_workflow')
        allowed_states = ['verified', 'published']
        data['prepublish'] = wf.getInfoFor(ar, 'review_state') not in allowed_states
        if wf.getInfoFor(ar, 'review_state') == 'published':
            data['published'] = True

        data['contact'] = self._contact_data(ar)
        data['client'] = self._client_data(ar)
        #data['sample'] = self._sample_data(ar)
        data['product'] = self._sample_type(ar).get('title', '')
        #data['batch'] = self._batch_data(ar)
        #data['specifications'] = self._specs_data(ar)
        #data['analyses'] = self._analyses_data(ar, ['verified', 'published'])
        #data['qcanalyses'] = self._qcanalyses_data(ar, ['verified', 'published'])
        #data['points_of_capture'] = sorted(set([an['point_of_capture'] for an in data['analyses']]))
        #data['categories'] = sorted(set([an['category'] for an in data['analyses']]))
        #data['hasblanks'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'b']) > 0
        #data['hascontrols'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'c']) > 0
        #data['hasduplicates'] = len([an['reftype'] for an in data['qcanalyses'] if an['reftype'] == 'd']) > 0
        # Attachment src/link
        attachments = ar.getAttachment()
        for attachment in attachments:
            if attachment.getReportOption() != 'r':
                continue
            filename = attachment.getAttachmentFile().filename 
            extension = filename.split('.')[-1]
            if extension in ['png', 'jpg', 'jpeg']: #Check other image extensions
                file_url =  attachment.absolute_url()
                data['attachment_src'] = '{}/at_download/AttachmentFile'.format(file_url)
                [width, height] = attachment.getAttachmentFile().getSize()
                maxwidth = 248 # 80% of 310px
                maxheight = 100
                resize_ratio = min(maxwidth/float(width), maxheight/float(height))
                data['attachment_width'] = width*resize_ratio
                data['attachment_height'] = height*resize_ratio
                break

        # Categorize analyses
        #data['categorized_analyses'] = {}
        data['department_analyses'] = {}
        #for an in data['analyses']:
        #    poc = an['point_of_capture']
        #    cat = an['category']
        #    pocdict = data['categorized_analyses'].get(poc, {})
        #    catlist = pocdict.get(cat, [])
        #    catlist.append(an)
        #    pocdict[cat] = catlist
        #    data['categorized_analyses'][poc] = pocdict

        #    # Group by department too
        #    anobj = an['obj']
        #    dept = anobj.getService().getDepartment() if anobj.getService() else None
        #    if dept:
        #        dept = dept.UID()
        #        dep = data['department_analyses'].get(dept, {})
        #        dep_pocdict = dep.get(poc, {})
        #        dep_catlist = dep_pocdict.get(cat, [])
        #        dep_catlist.append(an)
        #        dep_pocdict[cat] = dep_catlist
        #        dep[poc] = dep_pocdict
        #        data['department_analyses'][dept] = dep

        # Categorize qcanalyses
        #data['categorized_qcanalyses'] = {}
        #for an in data['qcanalyses']:
        #    qct = an['reftype']
        #    poc = an['point_of_capture']
        #    cat = an['category']
        #    qcdict = data['categorized_qcanalyses'].get(qct, {})
        #    pocdict = qcdict.get(poc, {})
        #    catlist = pocdict.get(cat, [])
        #    catlist.append(an)
        #    pocdict[cat] = catlist
        #    qcdict[poc] = pocdict
        #    data['categorized_qcanalyses'][qct] = qcdict

        #data['reporter'] = self._reporter_data(ar)
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
        supervisor = lab.getLaboratorySupervisor()
        bsc = getToolByName(self.context, "bika_setup_catalog")
        labcontact = bsc(portal_type="LabContact", id=supervisor)
        signature = None
        lab_manager = ''
        if len(labcontact) == 1:
            labcontact = labcontact[0].getObject()
            lab_manager_name = to_utf8(self.user_fullname(labcontact.getUsername()))
            lab_manager_job_title = to_utf8(labcontact.getJobTitle())
            lab_manager = '{} {}'.format(lab_manager_name, lab_manager_job_title)

            if labcontact.getSignature():
                signature_url = labcontact.getSignature().absolute_url()
                signature = '{}/Signature'.format(signature_url)


        return {'obj': lab,
                'title': to_utf8(lab.Title()),
                'lab_license_id': to_utf8(lab.getLaboratoryLicenseID()),
                'url': to_utf8(lab.getLabURL()),
                'phone': to_utf8(lab.getPhone()),
                'address': to_utf8(self._lab_address(lab)),
                'email': to_utf8(lab.getEmailAddress()),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url(),
                'lab_manager': to_utf8(lab_manager),
                'signature': signature,
                'today':self.ulocalized_time(DateTime(), long_format=0),}

    def sorted_by_sort_key(self, category_keys):
        """ Sort categories via catalog lookup on title. """
        bsc = getToolByName(self.context, "bika_setup_catalog")
        analysis_categories = bsc(portal_type="AnalysisCategory", sort_on="sortable_title")
        sort_keys = dict([(b.Title, "{:04}".format(a)) for a, b in enumerate(analysis_categories)])
        return sorted(category_keys, key=lambda title, sk=sort_keys: sk.get(title))

    def getARAnayses(self, ar):
        """ Returns a dict with the following structure:
            [ {'headers': ['cat1_title', 'unit1', 'unit2'],
               'rows': [ ['AS 1 title', val1, val2],
                         ['AS 2 title', val1, val2]],
                       ],
               'footnotes': ['note 1 ', 'Note2']
              },
            ]
            {'category_1_name':
                {'service_1_title':
                    {'service_1_uid':
                        {'service': <AnalysisService-1>,
                         'ars': {'ar1_id': [<Analysis (for as-1)>,
                                           <Analysis (for as-1)>],
                                 'ar2_id': [<Analysis (for as-1)>]
                                },
                        },
                    },
                {'_data':
                    {'footnotes': service.getCategory().Comments()',
                     'unit': service.getUnit}
                },
                {'service_2_title':
                     {'service_2_uid':
                        {'service': <AnalysisService-2>,
                         'ars': {'ar1_id': [<Analysis (for as-2)>,
                                           <Analysis (for as-2)>],
                                 'ar2_id': [<Analysis (for as-2)>]
                                },
                        },
                    },
                ...
                },
            }
        """
        def get_sample_type_uid(analysis):
            if getattr(analysis.aq_parent, 'getSample'):
                return analysis.aq_parent.getSample().getSampleType().UID()

        analyses = {}
        count = 0
        dmk = ar.bika_setup.getResultsDecimalMark()
        ans = [an.getObject() for an in ar.getAnalyses()]
        sample_type_uid = ar.getSampleType().UID()
        bsc = getToolByName(self, 'bika_setup_catalog')
        analysis_specs = bsc(portal_type='AnalysisSpec',
                      getSampleTypeUID=sample_type_uid)
        analysis_spec = None
        if len(analysis_specs) > 0:
            analysis_spec = analysis_specs[0].getObject()
        for an in ans:
            service = an.getService()
            if service.getHidden():
                continue
            cat = service.getCategoryTitle()
            if cat not in analyses:
                analyses[cat] = {}
            cat_dict = analyses[cat]
            if service.title not in cat_dict:
                cat_dict[service.title] = {}

            an_dict = cat_dict[service.title]
            an_dict['ars'] = an.getFormattedResult()
            an_dict['accredited'] = service.getAccredited()
            an_dict['service'] = service
            an_dict['unit'] = service.getUnit()
            an_dict['include_original'] = True
            an_dict['converted_units'] = []
            an_dict['limits_units'] = []
            # add unit conversion information
            if sample_type_uid:
                i = 0
                new_text = []
                hide_original = False
                for unit_conversion in service.getUnitConversions():
                    if unit_conversion.get('SampleType') and \
                       unit_conversion.get('Unit') and \
                       unit_conversion.get('SampleType') == sample_type_uid:
                        i += 1
                        new = dict({})
                        conv = ploneapi.content.get(
                                            UID=unit_conversion['Unit'])
                        new['unit'] = conv.converted_unit
                        new['ars'] = convert_unit(
                                        an.getResult(),
                                        conv.formula,
                                        dmk,
                                        an.getPrecision())
                        an_dict['converted_units'].append(new)
                        if service.title in cat_dict.keys() and \
                           unit_conversion.get('HideOriginalUnit') == '1':
                               an_dict['include_original'] = False

                if analysis_spec:
                    keyword = service.getKeyword()
                    if keyword:
                        spec_string = analysis_spec.getAnalysisSpecsStr(keyword)
                        if spec_string:
                            new = dict({})
                            new['unit'] = 'Limits'
                            new['ars'] = spec_string.split(' ')[-1]
                            an_dict['limits_units'].append(new)

            if '_data' not in cat_dict:
                cat_dict['_data'] = {}
            cat_dict['_data']['footnotes'] = service.getCategory().Comments()
            if 'unit' not in cat_dict['_data']:
                cat_dict['_data']['unit'] = []
            unit = to_utf8(service.getUnit())
            if unit not in cat_dict['_data']['unit']:
                cat_dict['_data']['unit'].append(unit)
        #Transpose analyses into a table like structure for the page template
        result = []
        cats = self.sorted_by_sort_key(analyses.keys())
        for cat_title in cats:
            cat_dict_out = {'headers': [cat_title,], 'rows': [], 'notes': []}
            cat_dict_in = analyses[cat_title]
            keys = sorted(cat_dict_in.keys())
            #Get headers
            headers = cat_dict_out['headers']
            limits = []
            for key in keys:
                if key == '_data':
                    notes = cat_dict_in[key].get('footnotes', '')
                    if len(notes):
                        cat_dict_out['notes'].append(notes)
                    continue
                row_dict = cat_dict_in[key] 
                if len(row_dict.get('converted_units', [])) > 0:
                    for unit in row_dict['converted_units']:
                        if unit['unit'] not in headers:
                            headers.append(unit['unit'])
                if row_dict['include_original']:
                    unit = row_dict['unit']
                    if unit is None or len(unit) == 0:
                        unit = 'Result'
                    if unit not in headers:
                        headers.append(unit)
                if len(row_dict.get('limits_units', [])) > 0:
                    for unit in row_dict['limits_units']:
                        if unit['unit'] not in limits:
                            limits.append(unit['unit'])
            for limit in limits:
                if limit not in headers:
                    headers.append(limit)

            #Contruct rows with in header constraints
            rows = cat_dict_out['rows']
            for key in keys:
                if key == '_data':
                    continue
                row = [key,]
                for h in headers[:-1]:
                    row.append('')
                row_dict = cat_dict_in[key] 
                if len(row_dict.get('converted_units', [])) > 0:
                    for unit in row_dict['converted_units']:
                        idx = headers.index(unit['unit'])
                        row[idx] = unit['ars']
                if row_dict['include_original']:
                    unit = row_dict['unit']
                    if unit is None or len(unit) == 0:
                        unit = 'Result'
                    idx = headers.index(unit)
                    row[idx] = row_dict['ars']
                if len(row_dict.get('limits_units', [])) > 0:
                    for unit in row_dict['limits_units']:
                        idx = headers.index(unit['unit'])
                        row[idx] = unit['ars']
                rows.append(row)

            for idx in range(len(headers)):
                if idx == 0:
                    continue
                elif headers[idx] == 'Result':
                    continue
                elif headers[idx] == 'Limits':
                    continue
                headers[idx] = 'Results (%s)' % headers[idx]
            result.append(cat_dict_out)
        #print str(result)
        return result

    def getAnaysisBasedTransposedMatrix(self, ars):
        """ Returns a dict with the following structure:
            {'category_1_name':
                {'service_1_title':
                    {'service_1_uid':
                        {'service': <AnalysisService-1>,
                         'ars': {'ar1_id': [<Analysis (for as-1)>,
                                           <Analysis (for as-1)>],
                                 'ar2_id': [<Analysis (for as-1)>]
                                },
                        },
                    },
                {'_data':
                    {'footnotes': service.getCategory().Comments()',
                     'unit': service.getUnit}
                },
                {'service_2_title':
                     {'service_2_uid':
                        {'service': <AnalysisService-2>,
                         'ars': {'ar1_id': [<Analysis (for as-2)>,
                                           <Analysis (for as-2)>],
                                 'ar2_id': [<Analysis (for as-2)>]
                                },
                        },
                    },
                ...
                },
            }
        """
        analyses = {}
        count = 0
        for ar in ars:
            ans = [an.getObject() for an in ar.getAnalyses()]
            for an in ans:
                service = an.getService()
                cat = service.getCategoryTitle()
                if cat not in analyses:
                    analyses[cat] = {}
                if service.title not in analyses[cat]:
                    analyses[cat][service.title] = {}

                d = analyses[cat][service.title]
                d['ars'] = {ar.id: an.getFormattedResult()}
                d['accredited'] = service.getAccredited()
                d['service'] = service
                analyses[cat][service.title] = d
                if '_data' not in analyses[cat]:
                    analyses[cat]['_data'] = {}
                analyses[cat]['_data']['footnotes'] = service.getCategory().Comments()
                if 'unit' not in analyses[cat]['_data']:
                    analyses[cat]['_data']['unit'] = []
                unit = to_utf8(service.getUnit())
                if unit not in analyses[cat]['_data']['unit']:
                    analyses[cat]['_data']['unit'].append(unit)
        return analyses

    def current_certificate_number(self):
        """Return the last written ID from the registry
        """
        key = 'bika.lims.current_coa_number'
        val = ploneapi.portal.get_registry_record(key)
        year = str(time.localtime(time.time())[0])[-2:]
        return "COA%s-%05d"%(year, int(val))

    def publishFromHTML(self, aruid, results_html):
        # The AR can be published only and only if allowed
        uc = getToolByName(self.context, 'uid_catalog')
        #ars = uc(UID=aruid)
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
        pdf_report = createPdf(htmlreport=results_html, outfile=pdf_fn)

        # PDF written to debug file
        if debug_mode:
            logger.debug("Writing PDF for %s to %s" % (ar.Title(), pdf_fn))
        else:
            os.remove(pdf_fn)

        recipients = []
        contact = ar.getContact()
        lab = ar.bika_setup.laboratory

        # BIKA Cannabis hack.  Create the CSV they desire here now
        #csvdata = self.create_cannabis_csv(ars)
        csvdata = self.create_metrc_csv(ars)
        pdf_fn = to_utf8(ar.getRequestID())
        if pdf_report:
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
                Pdf=pdf_report,
                CSV=csvdata,
                Html=results_html,
                Recipients=recipients
            )
            report.unmarkCreationFlag()
            renameAfterCreation(report)
            # Set blob properties for fields containing file data
            fld = report.getField('Pdf')
            fld.get(report).setFilename(pdf_fn+ ".pdf")
            fld.get(report).setContentType('application/pdf')
            fld = report.getField('CSV')
            fld.get(report).setFilename(pdf_fn + ".csv")
            fld.get(report).setContentType('text/csv')

            # Set status to prepublished/published/republished
            status = wf.getInfoFor(ar, 'review_state')
            transitions = {'verified': 'publish',
                           'published' : 'republish'}
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

            to = []
            #mngrs = ar.getResponsible()
            #for mngrid in mngrs['ids']:
            #    name = mngrs['dict'][mngrid].get('name', '')
            #    email = mngrs['dict'][mngrid].get('email', '')
            #    if (email != ''):
            #        to.append(formataddr((encode_header(name), email)))

            #if len(to) > 0:
            #    # Send the email to the managers
            #    mime_msg['To'] = ','.join(to)
            #    attachPdf(mime_msg, pdf_report, pdf_fn)

            #    # BIKA Cannabis hack.  Create the CSV they desire here now
            #    fn = pdf_fn
            #    attachCSV(mime_msg,csvdata,fn)

            #    try:
            #        host = getToolByName(ar, 'MailHost')
            #        host.send(mime_msg.as_string(), immediate=True)
            #    except SMTPServerDisconnected as msg:
            #        logger.warn("SMTPServerDisconnected: %s." % msg)
            #    except SMTPRecipientsRefused as msg:
            #        raise WorkflowException(str(msg))

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

        # Save file on the filesystem
        folder = os.environ.get('COAs_FOLDER', '')
        if len(folder) != 0:
            client_path = '{}/{}/'.format(folder, ar.getClientID())
            if not os.path.exists(client_path):
                os.makedirs(client_path)

            today = self.ulocalized_time(DateTime(), long_format=0)
            today_path = '{}{}/'.format(client_path, today)
            if not os.path.exists(today_path):
                os.makedirs(today_path)

            fname = '{}{}.pdf'.format(today_path, pdf_fn)
            f = open(fname, 'w')
            f.write(pdf_report)
            f.close()

            csvname = '{}{}.csv'.format(today_path, pdf_fn)
            fcsv = open(csvname, 'w')
            fcsv.write(csvdata)
            fcsv.close()

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
                date_published = date_published.split(' ')[0]
            else:
                date_published = self.ulocalized_time(DateTime(), long_format=0)

            client_sampleid = to_utf8(ar.getClientSampleID())
            as_keyword = ''
            result = ''
            is_in_range = 'True'
            unit_and_ar_id = ''
            sample_type_uid = ar.getSampleType().UID()
            bsc = getToolByName(self, 'bika_setup_catalog')
            analysis_specs = bsc(portal_type='AnalysisSpec',
                          getSampleTypeUID=sample_type_uid)
            dmk = ar.bika_setup.getResultsDecimalMark()

            lines = []
            analyses = ar.getAnalyses(full_objects=True)
            for analysis in analyses:
                service = analysis.getService()
                if service.getHidden():
                    continue
                specification =  analysis.getResultsRange()
                result =  analysis.getFormattedResult(html=False)
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
                        if outofrange == False:
                            is_in_range = True
                        elif outofrange == True:
                            is_in_range = False

                unit = service.getUnit()
                unit = '({})-'.format(unit) if unit else ''
                unit_and_ar_id = '{}{}'.format(unit, ar_id)

                #Check unit conversion
                if sample_type_uid:
                    i = 0
                    new_text = []
                    hide_original = False
                    an_dict = {'converted_units': []}
                    for unit_conversion in service.getUnitConversions():
                        if unit_conversion.get('SampleType') and \
                           unit_conversion.get('Unit') and \
                           unit_conversion.get('SampleType') == sample_type_uid:
                            i += 1
                            new = dict({})
                            conv = ploneapi.content.get(
                                                UID=unit_conversion['Unit'])
                            unit_and_ar_id = '({})-{}'.format(
                                                    conv.converted_unit, ar_id)
                            result = convert_unit(
                                            analysis.getResult(),
                                            conv.formula,
                                            dmk,
                                            analysis.getPrecision())
                            break

                line = {'date_published': date_published,
                        'client_sampleid': client_sampleid,
                        'as_keyword': service.getShortTitle(),
                        'result': result,
                        'is_in_range': is_in_range,
                        'unit_and_ar_id' : unit_and_ar_id,
                        }
                lines.append(line)

            for l in lines:
                writer.writerow([l['date_published'], l['client_sampleid'],
                                l['as_keyword'], l['result'],
                                l['is_in_range'], l['unit_and_ar_id'],
                                ])

        return output.getvalue()
