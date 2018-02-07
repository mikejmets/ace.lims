import sys
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims import bikaMessageFactory as _
from bika.lims.interfaces import IARImport
from Products.Archetypes.public import *
from zope.component import adapts
from zope.interface import implements

from Products.Archetypes.interfaces.vocabulary import IVocabulary
from Products.CMFCore.utils import getToolByName
from Products.DataGridField import Column
from Products.DataGridField import SelectColumn

from zope.interface import Interface

from plone import api

from Products.Archetypes.utils import DisplayList
class IVocabulary_Strain(Interface):
    """"""

class Vocabulary_Strain(object):
    implements(IVocabulary)

    #def __call__(self, context):
    def getDisplayList(self, context):
        """ returns an object of class DisplayList as defined in
            Products.Archetypes.utils.

            The instance of the content is given as parameter.
        """

        portal = api.portal.get()
        bsc = getToolByName(portal, 'bika_setup_catalog')
        strains = bsc(
                portal_type='Strain', sort_on = 'sortable_title')
        items = [['', ''], ]
        for strain in strains:
            items.append([strain.UID, strain.Title])
        return DisplayList(items)

class Vocabulary_ClientLicenceID(object):
    implements(IVocabulary)

    def getDisplayList(self, context):
        """ returns an object of class DisplayList as defined in
            Products.Archetypes.utils.

            The instance of the content is given as parameter.
        """

        portal = api.portal.get()
        bsc = getToolByName(portal, 'portal_catalog')
        licences = [['', ''], ]
        client = context.aq_parent
        for licence in client.getLicences():
            licence_types = bsc(
                                portal_type='ClientType',
                                UID=licence['LicenceType'])
            if len(licence_types) == 1:
                licence_type = licence_types[0].Title
                longstring ='{},{LicenceID},{LicenceNumber},{Authority}'
                id_value = longstring.format(licence_type, **licence)
                value = licence_type
                licences.append([id_value, value])

        return DisplayList(licences)

class ARImportSchemaModifier(object):
    adapts(IARImport)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        """
        """

        dgf = schema['SampleData']
        temp_var = [i for i in dgf.columns]
        if "ClientReference" not in temp_var:
            temp_var.append("ClientReference")
        if "Strain" not in temp_var:
            temp_var.append("Strain")
        if "Lot" not in temp_var:
            temp_var.append("Lot")
        if "CultivationBatch" not in temp_var:
            temp_var.append("CultivationBatch")
        if "ClientLicenceID" not in temp_var:
            temp_var.append("ClientLicenceID")
        if "SamplePoint" in temp_var:
            temp_var.remove("SamplePoint")
        if "SampleMatrix" in temp_var:
            temp_var.remove("SampleMatrix")
        if "ContainerType" in temp_var:
            temp_var.remove("ContainerType")
        if "ReportDryMatter" in temp_var:
            temp_var.remove("ReportDryMatter")
        if "SamplingDate" in temp_var:
            temp_var.remove("SamplingDate")


        dgf.columns = tuple(temp_var)
        strain_vocab = Vocabulary_Strain()
        dgf.widget.columns["ClientReference"] = Column('ClientReference')
        dgf.widget.columns["Strain"] = SelectColumn(
                                                'Strain',
                                                vocabulary=strain_vocab)
        dgf.widget.columns["Lot"] = Column('Lot')
        dgf.widget.columns["CultivationBatch"] = Column('Cultivation Batch')
        cslid_vocab = Vocabulary_ClientLicenceID()
        dgf.widget.columns["ClientLicenceID"] = SelectColumn(
                                                "Client's Licence ID",
                                                vocabulary=cslid_vocab)
        if "SamplePoint" in dgf.widget.columns.keys():
            del dgf.widget.columns["SamplePoint"]
        if "SampleMatrix" in dgf.widget.columns.keys():
            del dgf.widget.columns["SampleMatrix"]
        if "ContainerType" in dgf.widget.columns.keys():
            del dgf.widget.columns["ContainerType"]
        if "ReportDryMatter" in dgf.widget.columns.keys():
            del dgf.widget.columns["ReportDryMatter"]

        return schema


