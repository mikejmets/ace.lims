import sys
from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.widgets import SelectionWidget as BikaSelectionWidget
from bika.lims.browser.widgets import ReferenceWidget as BikaReferenceWidget
from bika.lims.browser.fields import ProxyField
from bika.lims.fields import ExtReferenceField, ExtStringField
from bika.lims.interfaces import IARImport
from bika.lims.permissions import EditARContact
from bika.lims.permissions import SampleSample
from Products.Archetypes.atapi import StringField
from Products.Archetypes.public import *
from Products.Archetypes.references import HoldingReference
from Products.CMFCore import permissions
from zope.component import adapts
from zope.interface import implements

from Products.DataGridField import CheckboxColumn
from Products.DataGridField import Column
from Products.DataGridField import DataGridField
from Products.DataGridField import DataGridWidget
from Products.DataGridField import DateColumn
from Products.DataGridField import DatetimeColumn
from Products.DataGridField import LinesColumn
from Products.DataGridField import SelectColumn
from Products.DataGridField import TimeColumn

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
        dgf.columns = tuple(temp_var)
        dgf.widget.columns["Strain"] = SelectColumn(
                                    'Strain', vocabulary='Vocabulary_Strain')

        return schema

