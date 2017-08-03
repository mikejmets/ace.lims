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

class Vocabulary_ClientStateLicenseID(object):
    implements(IVocabulary)

    def getDisplayList(self, context):
        """ returns an object of class DisplayList as defined in
            Products.Archetypes.utils.

            The instance of the content is given as parameter.
        """

        portal = api.portal.get()
        bsc = getToolByName(portal, 'portal_catalog')
        licenses = [['', ''], ]
        client = context.getClient()
        for license in client.getLicenses():
            license_types = bsc(
                                portal_type='ClientType',
                                UID=license['LicenseType'])
            if len(license_types) == 1:
                license_type = license_types[0].Title
                longstring ='{},{LicenseID},{LicenseNumber},{Authority}'
                id_value = longstring.format(license_type, **license)
                value = license_type
                licenses.append([id_value, value])

        return DisplayList(licenses)

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
        if "Strain" not in temp_var:
            temp_var.append("Strain")
        if "Lot" not in temp_var:
            temp_var.append("Lot")
        if "CultivationBatch" not in temp_var:
            temp_var.append("CultivationBatch")
        if "ClientStateLicenseID" not in temp_var:
            temp_var.append("ClientStateLicenseID")


        dgf.columns = tuple(temp_var)
        strain_vocab = Vocabulary_Strain()
        dgf.widget.columns["Strain"] = SelectColumn(
                                                'Strain',
                                                vocabulary=strain_vocab)
        dgf.widget.columns["Lot"] = Column('Lot')
        dgf.widget.columns["CultivationBatch"] = Column('Cultivation Batch')
        cslid_vocab = Vocabulary_ClientStateLicenseID()
        dgf.widget.columns["ClientStateLicenseID"] = SelectColumn(
                                                "Client's State License ID",
                                                vocabulary=cslid_vocab)

        return schema


