# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from bika.lims import bikaMessageFactory as _, t
from bika.lims import logger
from bika.lims.browser import BrowserView
from bika.lims.vocabularies import getStickerTemplates
from bika.lims.utils import to_utf8, encode_header, attachPdf
from plone.resource.utils import iterDirectoriesOfType, queryResourceDirectory
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import glob, os, os.path, sys, traceback

import os

class COC(BrowserView):
    """ Invoked via URL on an object or list of objects from the types
        AnalysisRequest, Sample, SamplePartition or ReferenceSample.
        Renders a preview for the objects, a control to allow the user to
        select the stcker template to be invoked and print.
    """
    template = ViewPageTemplateFile("templates/coc_preview.pt")
    item_index = 0
    current_item = None
    lab_data = None
    rendered_items = []

    def __call__(self):
        self.rendered_items = []
        bc = getToolByName(self.context, 'bika_catalog')
        items = self.request.get('items', '')
        if items:
            self.items = [o.getObject() for o in bc(UID=items.split(","))]
        else:
            self.items = [self.context,]

        new_items = []
        for i in self.items:
            outitems = self._populateItems(i)
            new_items.extend(outitems)

        self.items = new_items
        if not self.items:
            logger.warning("Cannot print coc: no items specified in request")
            self.request.response.redirect(self.context.absolute_url())
            return
        
        return self.template()

    def ar_data(self):
        ars = []
        for item in self.items:
            ar = item[0]
            client_state_id_lst = \
                    ar.getClientStateLicenseID().split(',')
            sample = ar.getSample()
            strain = ''
            bsc =  self.bika_setup_catalog
            strains = bsc(UID=ar.getSample()['Strain'])
            if strains:
                 strain = strains[0].Title
            adict = {
                    'lic_id': client_state_id_lst[1],
                    'state_id': client_state_id_lst[2],
                    'title': '{} - {}'.format(sample.Title(), strain),
                    'batch': ar['CultivationBatch'],
                    'lot': ar['Lot'],
                    'sampler': ar.getSampler(),
                    }
            ars.append(adict)
        return ars

    def client_data(self):
        client = self.context
        contacts = client.getContacts()
        contact_name = ''
        contact_email = ''
        if contacts:
            contact = contacts[0]
            contact_name = contact.Title()
            contact_email = contact.getEmailAddress()
        address = client.getPhysicalAddress()
        attest = self.context.bika_setup.getCOCAttestationStatement()
        adict = {'obj': client,
                'name': to_utf8(client.getName()),
                'phone': to_utf8(client.getPhone()),
                'contact_name': to_utf8(contact_name),
                'contact_email': to_utf8(contact_email),
                'street_part': to_utf8(address['address']),
                'city_part': to_utf8('{},{},{}'.format(address['city'],address['state'], address['zip'])),
                'attest': to_utf8(attest),
                }
        return adict

    def lab_data(self):
        portal = self.context.portal_url.getPortalObject()
        lab = self.context.bika_setup.laboratory
        supervisor = lab.getLaboratorySupervisor()
        bsc = getToolByName(self.context, "bika_setup_catalog")
        labcontact = bsc(portal_type="LabContact", id=supervisor)
        signature = None
        lab_manager = ''
        signature = ''
        if len(labcontact) == 1:
            labcontact = labcontact[0].getObject()
            lab_manager = to_utf8(labcontact.getFullname())

        address = lab.getPhysicalAddress()
        address = ', '.join((address['address'],
                address['city'],address['state'], address['zip']))
        adict = {
                'title': to_utf8(lab.Title()),
                'lab_license_id': to_utf8(lab.getLaboratoryLicenseID()),
                'name': to_utf8(lab.getName()),
                'url': to_utf8(lab.getLabURL()),
                'phone': to_utf8(lab.getPhone()),
                'email': to_utf8(lab.getEmailAddress()),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url(),
                'lab_manager': to_utf8(lab_manager),
                'signature': signature,
                'today':self.ulocalized_time(DateTime(), long_format=0),
                'address': to_utf8(address),
                }
        return adict


    def _populateItems(self, item):
        """ Creates an wel-defined array for this item to make the sticker
            template easy to render. Each position of the array has a secondary
            array, one per partition.

            If the item is an object from an AnalysisRequest type, returns an
            array with the following structure:
                [
                 [ar_object, ar_sample, ar_sample_partition-1],
                 [ar_object, ar_sample, ar_sample_partition-2],
                 ...
                 [ar_object, ar_sample, ara_sample_partition-n]
                ]

            If the item is an object from Sample type, returns an arary with the
            following structure:
                [
                 [None, sample, sample_partition-1],
                 [None, sample, sample_partition-2],
                 ...
                ]

            If the item is an object from ReferenceSample type, returns an
            array with the following structure:
                [[None, refsample, None]]
            Note that in this case, the array always have a length=1
        """
        ar = None
        sample = None
        parts = []
        if item.portal_type == 'AnalysisRequest':
            ar = item
            sample = item.getSample()
            parts = sample.objectValues('SamplePartition')
        elif item.portal_type == 'Sample':
            sample = item
            parts = sample.objectValues('SamplePartition')
        elif item.portal_type == 'SamplePartition':
            sample = item.aq_parent
            parts = [item,]
        elif item.portal_type == 'ReferenceSample':
            sample = item

        items = []
        for p in parts:
            items.append([ar, sample, p])
        return items

    def getAvailableTemplates(self):
        """ Returns an array with the templates of coc available. Each
            array item is a dictionary with the following structure:
                {'id': <template_id>,
                 'title': <teamplate_title>,
                 'selected: True/False'}
        """
        templates = []
        templates.append({'selected': True, 'id': 'coc.pt', 'title': 'COC'})
        #for temp in getStickerTemplates():
        #    out = temp
        #    out['selected'] = temp.get('id', '') == seltemplate
        #    templates.append(out)
        return templates

    def getSelectedTemplate(self):
        """ Returns the id of the sticker template selected. If no specific
            template found in the request (parameter template), returns the
            default template set in Bika Setup > Stickers.
            If the template doesn't exist, uses the default bika.lims'
            Code_128_1x48mm.pt template (was sticker_small.pt).
            If no template selected but size param, get the sticker template
            set as default in Bika Setup for the size set.
        """
        return 'coc.pt'
        #bs_template = self.context.bika_setup.getAutoStickerTemplate()
        #size = self.request.get('size', '')
        #if size == 'small':
        #    bs_template = self.context.bika_setup.getSmallStickerTemplate()
        #elif size == 'large':
        #    bs_template = self.context.bika_setup.getLargeStickerTemplate()
        #rq_template = self.request.get('template', bs_template)
        ## Check if the template exists. If not, fallback to default's
        #prefix = ''
        #if rq_template.find(':') >= 0:
        #    prefix, rq_template = rq_template.split(':')
        #    templates_dir = queryResourceDirectory('coc', prefix).directory
        #else:
        #    this_dir = os.path.dirname(os.path.abspath(__file__))
        #    templates_dir = os.path.join(this_dir, 'templates/coc/')
        #if not os.path.isfile(os.path.join(templates_dir, rq_template)):
        #    rq_template = 'coc.pt'
        #return '%s:%s' % (prefix, rq_template) if prefix else rq_template

    def getSelectedTemplateCSS(self):
        """ Looks for the CSS file from the selected template and return its
            contents. If the selected template is default.pt, looks for a
            file named default.css in the coc path and return its contents.
            If no CSS file found, retrns an empty string
        """
        template = self.getSelectedTemplate()
        # Look for the CSS
        content = ''
        if template.find(':') >= 0:
            # A template from another add-on
            prefix, template = template.split(':')
            resource = queryResourceDirectory('coc', prefix)
            css = '{0}.css'.format(template[:-3])
            if css in resource.listDirectory():
                content = resource.readFile(css)
        else:
            this_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(this_dir, 'templates/')
            path = '%s/%s.css' % (templates_dir, template[:-3])
            if os.path.isfile(path):
                with open(path, 'r') as content_file:
                    content = content_file.read()
        return content

    def nextItem(self):
        """ Iterates to the next item in the list and moves one position up the
            item index. If the end of the list of items is reached, returns the
            first item of the list.
        """
        if self.item_index == len(self.items):
            self.item_index = 0
            self.rendered_items = []
        self.current_item = self.items[self.item_index]
        self.rendered_items.append(self.current_item[2].getId())
        self.item_index += 1
        return self.current_item

    def renderItem(self):
        """ Renders the next available sticker.
            Uses the template specified in the request ('template' parameter) by
            default. If no template defined in the request, uses the default
            template set by default in Bika Setup > Stickers.
            If the template specified doesn't exist, uses the default
            bika.lims' Code_128_1x48mm.pt template (was sticker_small.pt).
        """
        curritem = self.nextItem()
        templates_dir = 'templates'
        embedt = self.getSelectedTemplate()
        if embedt.find(':') >= 0:
            prefix, embedt = embedt.split(':')
            templates_dir = queryResourceDirectory('coc', prefix).directory
        fullpath = os.path.join(templates_dir, embedt)
        try:
            embed = ViewPageTemplateFile(fullpath)
            return embed(self)
        except:
            tbex = traceback.format_exc()
            stickerid = curritem[2].id if curritem[2] else curritem[1].id
            return "<div class='error'>%s - %s '%s':<pre>%s</pre></div>" % \
                    (stickerid, _("Unable to load the template"), embedt, tbex)

    def getItemsURL(self):
        req_items = self.request.get('items', '')
        req_items = req_items if req_items else self.context.getId()
        req = '%s?items=%s' % (self.request.URL, req_items)
        return req
