from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from ace.lims import aceMessageFactory as _
from bika.lims.config import ManageBika
from bika.lims.fields import ExtStringField
from bika.lims.content.laboratory import Laboratory
from Products.Archetypes.public import *
from zope.component import adapts
from zope.interface import implements


class LaboratorySchemaExtender(object):
    adapts(Laboratory)
    implements(IOrderableSchemaExtender)

    fields = [

        ExtStringField(
            'LaboratoryLicenceID',
            write_permission=ManageBika,
            widget=StringWidget(
                label=_("Laboratory Licence ID"),
                description=_("The Laboratory's Licence ID issued by the state"),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getOrder(self, schematas):
        return schematas

    def getFields(self):
        return self.fields


class LaboratorySchemaModifier(object):
    adapts(Laboratory)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        return schema
