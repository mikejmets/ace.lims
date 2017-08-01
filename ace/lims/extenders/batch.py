from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims.interfaces import IBatch
from zope.component import adapts
from zope.interface import implements

class BatchSchemaModifier(object):
    adapts(IBatch)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        """
        """

        hide_fields = (
            )
        for fn in hide_fields:
            if fn in schema:
                schema[fn].widget.visible = {
                'add': 'invisible',
                'edit': 'invisible',
                'view': 'invisible'}
                schema[fn].required = False

        schema['Client'].required = True

        return schema


