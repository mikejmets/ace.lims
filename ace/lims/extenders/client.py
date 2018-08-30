from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from ace.lims import aceMessageFactory as _
# from bika.lims.fields import ExtReferenceField, ExtStringField
# from bika.lims.browser.widgets import ReferenceWidget as bikaReferenceWidget
from bika.lims.fields import ExtensionField
from bika.lims.interfaces import IClient
from bika.lims.vocabularies import CatalogVocabulary
from Products.Archetypes.public import *
from Products.Archetypes.interfaces.vocabulary import IVocabulary
from Products.DataGridField import Column
from Products.DataGridField import DataGridField
from Products.DataGridField import DataGridWidget
from Products.DataGridField import SelectColumn
# from Products.CMFCore import permissions
from zope.component import adapts
from zope.interface import implements


class ExtDataGridField(ExtensionField, DataGridField):

    "Field extender"


class Vocabulary_LicenceType(object):
    implements(IVocabulary)

    def getDisplayList(self, context):
        """ returns an object of class DisplayList as defined in
            Products.Archetypes.utils.

            The instance of the content is given as parameter.
        """

        vocabulary = CatalogVocabulary(self)
        vocabulary.catalog = 'portal_catalog'
        return vocabulary(allow_blank=True, portal_type='ClientLicenceType')


class ClientSchemaExtender(object):
    adapts(IClient)
    implements(IOrderableSchemaExtender)

    fields = [

        ExtDataGridField(
            'Licences',
            schemata="Licences",
            allow_insert=True,
            allow_delete=True,
            allow_reorder=True,
            allow_empty_rows=False,
            columns=('LicenceType',
                     'LicenceID',
                     'LicenceNumber',
                     'Authority'),
            default=[{'LicenceType': '',
                      'LicenceID': '',
                      'LicenceNumber': '',
                      'Authority': ''
                      }],
            widget=DataGridWidget(
                description=_("Details of client licences that authorise them to operate, sometimes to be included on documentation."),
                columns={
                    'LicenceType': SelectColumn(
                        'Licence Type',
                        vocabulary='Vocabulary_LicenceType'),
                    'LicenceID': Column('Licence ID'),
                    'LicenceNumber': Column('Registation Number'),
                    'Authority': Column('Issuing Authority')
                }
            )
        ),


    ]

    def __init__(self, context):
        self.context = context

    def getOrder(self, schematas):
        return schematas

    def getFields(self):
        return self.fields


class ClientSchemaModifier(object):
    adapts(IClient)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        dgf = schema['Licences']
        cslid_vocab = Vocabulary_LicenceType()
        dgf.widget.columns["LicenceType"] = SelectColumn("Licence Type",
                                                         vocabulary=cslid_vocab)
        return schema
