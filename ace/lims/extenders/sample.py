from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from ace.lims import aceMessageFactory as _
from bika.lims.fields import ExtReferenceField, ExtStringField
from bika.lims.browser.widgets import ReferenceWidget as bikaReferenceWidget
from bika.lims.interfaces import ISample
from Products.Archetypes.public import *
from Products.CMFCore import permissions
from zope.component import adapts
from zope.interface import implements
from Products.Archetypes.references import HoldingReference


class SampleSchemaExtender(object):
    adapts(ISample)
    implements(IOrderableSchemaExtender)

    fields = [
        ExtReferenceField(
            'Strain',
            required=True,
            allowed_types=('Strain'),
            relationship='SampleStrain',
            # format='select',
            referenceClass=HoldingReference,
            widget=bikaReferenceWidget(
                label="Strain",
                render_own_label=True,
                size=20,
                catalog_name='bika_setup_catalog',
                base_query={'inactive_state': 'active'},
                showOn=True,
                visible={'edit': 'visible',
                         'view': 'visible',
                         'header_table': 'visible',
                         'sample_registered': {'view': 'visible',
                                               'edit': 'visible',
                                               'add': 'edit'},
                         'to_be_sampled': {'view': 'visible',
                                           'edit': 'visible'},
                         'sampled': {'view': 'visible',
                                     'edit': 'visible'},
                         'to_be_preserved': {'view': 'visible',
                                             'edit': 'visible'},
                         'sample_due': {'view': 'visible',
                                        'edit': 'visible'},
                         'sample_received': {'view': 'visible',
                                             'edit': 'visible'},
                         'published': {'view': 'visible',
                                       'edit': 'invisible'},
                         'invalid': {'view': 'visible',
                                     'edit': 'invisible'},
                         },
            ),
        ),
        ExtStringField(
            'Lot',
            mode="rw",
            read_permission=permissions.View,
            write_permission=permissions.ModifyPortalContent,
            widget=StringWidget(
                label=_("Lot"),
                description="",
                visible={'view': 'visible',
                         'edit': 'visible',
                         'header_table': 'visible',
                         'add': 'edit'},
                render_own_label=True,
                size=20
            )
        ),
        ExtStringField(
            'CultivationBatch',
            mode="rw",
            read_permission=permissions.View,
            write_permission=permissions.ModifyPortalContent,
            widget=StringWidget(
                label=_("Cultivation Batch"),
                description="",
                visible={'view': 'visible',
                         'edit': 'visible',
                         'header_table': 'visible',
                         'add': 'edit'},
                render_own_label=True,
                size=20
            )
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getOrder(self, schematas):
        default = schematas['default']
        default.append('Strain')
        default.append('Lot')
        default.append('CultivationBatch')
        return schematas

    def getFields(self):
        return self.fields


class SampleSchemaModifier(object):
    adapts(ISample)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        return schema
