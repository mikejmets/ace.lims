# -*- coding:utf-8 -*-

# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from Acquisition import aq_get
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims.interfaces import IDisplayListVocabulary, ICustomPubPref
from bika.lims.utils import to_utf8
from Products.Archetypes.public import DisplayList
from Products.CMFCore.utils import getToolByName
from zope.interface import implements
from pkg_resources import resource_filename
from plone.resource.utils import iterDirectoriesOfType
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.component import getAdapters
from zope.site.hooks import getSite

import os
import glob

def getTemplates(bikalims_path, restype):
    """ Returns an array with the Templates available in the Bika LIMS path
        specified plus the templates from the resources directory specified and
        available on each additional product (restype).

        Each array item is a dictionary with the following structure:
            {'id': <template_id>,
             'title': <template_title>}

        If the template lives outside the bika.lims add-on, both the template_id
        and template_title include a prefix that matches with the add-on
        identifier. template_title is the same name as the id, but with
        whitespaces and without extension.

        As an example, for a template from the my.product add-on located in
        <restype> resource dir, and with a filename "My_cool_report.pt", the
        dictionary will look like:
            {'id': 'my.product:My_cool_report.pt',
             'title': 'my.product: My cool report'}
    """
    # Retrieve the templates from bika.lims add-on
    #templates_dir = resource_filename("bika.lims", bikalims_path)
    templates_dir = resource_filename("ace.lims", bikalims_path)
    tempath = os.path.join(templates_dir, '*.pt')
    templates = [os.path.split(x)[-1] for x in glob.glob(tempath)]

    # Retrieve the templates from other add-ons
    for templates_resource in iterDirectoriesOfType(restype):
        prefix = templates_resource.__name__
        if prefix == 'bika.lims':
            continue
        dirlist = templates_resource.listDirectory()
        exts = ['{0}:{1}'.format(prefix, tpl) for tpl in dirlist if
                tpl.endswith('.pt')]
        templates.extend(exts)

    out = []
    templates.sort()
    for template in templates:
        title = template[:-3]
        title = title.replace('_', ' ')
        title = title.replace(':', ': ')
        out.append({'id': template,
                    'title': title})

    return out

def getACEARReportTemplates():
    """ Returns an array with the AR Templates available in Bika LIMS  plus the
        templates from the 'reports' resources directory type from each
        additional product.

        Each array item is a dictionary with the following structure:
            {'id': <template_id>,
             'title': <template_title>}

        If the template lives outside the bika.lims add-on, both the template_id
        and template_title include a prefix that matches with the add-on
        identifier. template_title is the same name as the id, but with
        whitespaces and without extension.

        As an example, for a template from the my.product add-on located in
        templates/reports dir, and with a filename "My_cool_report.pt", the
        dictionary will look like:
            {'id': 'my.product:My_cool_report.pt',
             'title': 'my.product: My cool report'}
    """
    resdirname = 'reports'
    p = os.path.join("browser", "analysisrequest", "templates", resdirname)
    return getTemplates(p, resdirname)

