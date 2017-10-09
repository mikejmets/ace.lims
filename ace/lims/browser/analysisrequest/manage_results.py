from DateTime import DateTime
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode, _createObjectByType
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from ace.lims.utils import attachCSV, createPdf
from ace.lims.vocabularies import  getACEARReportTemplates
from bika.lims.browser.analysisrequest.manage_results import \
    AnalysisRequestManageResultsView as ARMRV
from bika.lims.idserver import renameAfterCreation
from bika.lims import bikaMessageFactory as _, t
from bika.lims import logger
from bika.lims.idserver import generateUniqueId
from bika.lims.utils import to_utf8, encode_header, attachPdf
from bika.lims.utils import convert_unit
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formataddr
from smtplib import SMTPServerDisconnected, SMTPRecipientsRefused
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.resource.utils import  queryResourceDirectory
from zope.interface import implements

from plone import api as ploneapi

import App
import StringIO
import csv
import os, traceback
import tempfile
import time

from plone.app.layout.globals.interfaces import IViewView

class AnalysisRequestManageResultsView(ARMRV):
    implements(IViewView)
    template = ViewPageTemplateFile("templates/analysisrequest_manage_results.pt")
