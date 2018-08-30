from archetypes.schemaextender.interfaces import IOrderableSchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.widgets import ReferenceWidget as BikaReferenceWidget
from bika.lims.browser.widgets import SelectionWidget as BikaSelectionWidget
from bika.lims.fields import ExtReferenceField, ExtStringField
from bika.lims.interfaces import IAnalysisRequest
from Products.Archetypes.public import *
from Products.Archetypes.interfaces.vocabulary import IVocabulary
from Products.Archetypes.utils import DisplayList
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from zope.component import adapts
from zope.interface import implements


class StrainField(ExtReferenceField):
    """A computed field which sets and gets a value from Sample
    """
    required = True

    def get(self, instance):
        sample = instance.getSample()
        if sample:
            return sample.Schema()['Strain'].get(sample)

    def set(self, instance, value):
        sample = instance.getSample()
        if sample and value:
            sample.Schema()['Strain'].set(sample, value)


class LotField(ExtStringField):
    """A computed field which sets and gets a value from Sample
    """

    def get(self, instance):
        sample = instance.getSample()
        value = False
        if sample:
            value = sample.Schema()['Lot'].get(sample)
        if not value:
            value = self.getDefault(instance)
        return value

    def set(self, instance, value):
        sample = instance.getSample()
        if sample and value:
            return sample.Schema()['Lot'].set(sample, value)


class CultivationBatchField(ExtStringField):
    """A computed field which sets and gets a value from Sample
    """

    def get(self, instance):
        sample = instance.getSample()
        value = False
        if sample:
            value = sample.Schema()['CultivationBatch'].get(sample)
        if not value:
            value = self.getDefault(instance)
        return value

    def set(self, instance, value):
        sample = instance.getSample()
        if sample and value:
            return sample.Schema()['CultivationBatch'].set(sample, value)


class Vocabulary_LicenceType(object):
    implements(IVocabulary)

    def getDisplayList(self, context):
        """ returns an object of class DisplayList as defined in
            Products.Archetypes.utils.

            The instance of the content is given as parameter.
            Return a list of Client Licence Types
        """
        bsc = getToolByName(context, 'portal_catalog')
        licences = [['', ''], ]
        # NOTE: Can only be be added within a client, gives error if an AR
        # is added outside a client. Maybe we should take that code out
        # Business rule Client Licences: Client Licences reside with a client
        client = context.getClient()
        for licence in client.Licences:
            licence_types = bsc(
                    portal_type='ClientLicenceType',
                    UID=licence['LicenceType'])
            if len(licence_types) == 1:
                licence_type = licence_types[0].Title
                id_value = '{},{LicenceID},{LicenceNumber},{Authority}'.format(licence_type, **licence)
                value = licence_type
                licences.append([id_value, value])
        return DisplayList(licences)


class AnalysisRequestSchemaExtender(object):
    adapts(IAnalysisRequest)
    implements(IOrderableSchemaExtender)

    fields = [
        StrainField(
            'Strain',
            required=True,
            allowed_types=['Strain'],
            relationship='SampleTypeStrain',
            format='select',
            widget=BikaReferenceWidget(
                label="Strain",
                render_own_label=True,
                size=20,
                catalog_name='bika_setup_catalog',
                base_query={'inactive_state': 'active'},
                showOn=True,
                search_fields=('Title', 'description', 'Code'),
                colModel=[
                    {'columnName': 'Code',
                     'width': '20', 'label': _('Code'),
                     'align': 'left'},
                    {'columnName': 'Title',
                     'width': '25', 'label': _('Title'),
                     'align': 'left'},
                    {'columnName': 'Description',
                     'width': '55',
                     'label': _('Description'),
                     'align': 'left'},
                    # UID is required in colModel
                    {'columnName': 'UID', 'hidden': True},
                ],
                visible={
                    'edit': 'visible',
                    'view': 'visible',
                    'add': 'edit',
                    'secondary': 'disabled',
                    'header_table': 'visible',
                    'sample_registered': {
                        'view': 'visible',
                        'edit': 'visible',
                        'add': 'edit'},
                    'to_be_sampled': {'view': 'visible',
                                      'edit': 'invisible'},
                    'sampled': {'view': 'visible',
                                'edit': 'invisible'},
                    'to_be_preserved': {'view': 'visible',
                                        'edit': 'invisible'},
                    'sample_due': {'view': 'visible',
                                   'edit': 'invisible'},
                    'sample_received': {'view': 'visible',
                                        'edit': 'invisible'},
                    'attachment_due': {'view': 'visible',
                                       'edit': 'invisible'},
                    'to_be_verified': {'view': 'visible',
                                       'edit': 'invisible'},
                    'verified': {'view': 'visible',
                                 'edit': 'invisible'},
                    'published': {'view': 'visible',
                                  'edit': 'invisible'},
                    'invalid': {'view': 'visible',
                                'edit': 'invisible'},
                },
            ),
        ),
        LotField(
            'Lot',
            searchable=True,
            mode="rw",
            read_permission=permissions.View,
            write_permission=permissions.ModifyPortalContent,
            widget=StringWidget(
                label=_("Lot"),
                size=20,
                render_own_label=True,
                visible={
                    'edit': 'visible',
                    'view': 'visible',
                    'add': 'edit',
                    'secondary': 'disabled',
                    'header_table': 'visible',
                    'sample_registered':
                        {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                    'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                    'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                    'sampled': {'view': 'visible', 'edit': 'visible'},
                    'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                    'sample_due': {'view': 'visible', 'edit': 'visible'},
                    'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                    'sample_received': {'view': 'visible', 'edit': 'visible'},
                    'attachment_due': {'view': 'visible', 'edit': 'visible'},
                    'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                    'verified': {'view': 'visible', 'edit': 'visible'},
                    'published': {'view': 'visible', 'edit': 'invisible'},
                    'invalid': {'view': 'visible', 'edit': 'invisible'},
                    'rejected': {'view': 'visible', 'edit': 'invisible'},
                },
            ),
        ),
        CultivationBatchField(
            'CultivationBatch',
            proxy="context.getSample()",
            searchable=True,
            mode="rw",
            read_permission=permissions.View,
            write_permission=permissions.ModifyPortalContent,
            widget=StringWidget(
                label=_("Cultivation Batch"),
                size=20,
                render_own_label=True,
                visible={
                    'edit': 'visible',
                    'view': 'visible',
                    'add': 'edit',
                    'secondary': 'disabled',
                    'header_table': 'visible',
                    'sample_registered':
                        {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                    'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                    'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                    'sampled': {'view': 'visible', 'edit': 'visible'},
                    'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                    'sample_due': {'view': 'visible', 'edit': 'visible'},
                    'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                    'sample_received': {'view': 'visible', 'edit': 'visible'},
                    'attachment_due': {'view': 'visible', 'edit': 'visible'},
                    'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                    'verified': {'view': 'visible', 'edit': 'visible'},
                    'published': {'view': 'visible', 'edit': 'invisible'},
                    'invalid': {'view': 'visible', 'edit': 'invisible'},
                    'rejected': {'view': 'visible', 'edit': 'invisible'},
                },
            ),
        ),

        ExtStringField(
            'ClientLicenceID',
            mode="rw",
            read_permission=permissions.View,
            write_permission=permissions.ModifyPortalContent,
            vocabulary='Vocabulary_LicenceType',
            acquire=True,
            widget=BikaSelectionWidget(
                format="select",
                label=_("Client's Licence"),
                description=_("Client's Licence appropriate to this AR"),
                visible={
                    'edit': 'visible',
                    'view': 'visible',
                    'add': 'edit',
                    'header_table': 'visible',
                    'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                    'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                    'sampled': {'view': 'visible', 'edit': 'visible'},
                    'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                    'sample_due': {'view': 'visible', 'edit': 'visible'},
                    'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                    'sample_received': {'view': 'visible', 'edit': 'invisible'},
                    'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                    'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                    'verified': {'view': 'visible', 'edit': 'invisible'},
                    'published': {'view': 'visible', 'edit': 'invisible'},
                    'invalid': {'view': 'visible', 'edit': 'invisible'},
                },
                render_own_label=True,
            ),
        ),

    ]

    def __init__(self, context):
        self.context = context

    def getOrder(self, schematas):
        schematas["default"].append("Strain")
        schematas["default"].append("Lot")
        schematas["default"].append("CultivationBatch")
        return schematas

    def getFields(self):
        return self.fields


class AnalysisRequestSchemaModifier(object):
    adapts(IAnalysisRequest)
    implements(ISchemaModifier)

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        """
        """
        csid = schema['ClientLicenceID']
        csid.vocabulary = Vocabulary_LicenceType()

        hide_fields = ('SubGroup',
                       'SamplingRound',
                       # 'Specification',
                       # 'ClientOrderNumber',
                       'AdHoc',
                       'InvoiceExclude',
                       'EnvironmentalConditions',
                       'SampleCondition')

        for fn in hide_fields:
            if fn in schema:
                schema[fn].widget.visible = {
                    'add': 'invisible',
                    'edit': 'invisible',
                    'view': 'invisible'}
                schema[fn].required = False

        schema['ClientLicenceID'].required = True

        sampler_fields = ('Sampler',
                          'DateSampled',
                          'SampleType',)
        states = ['sample_registered',
                  'to_be_sampled',
                  'sample_due',
                  'sample_received',
                  'to_be_verified', ]

        for fn in sampler_fields:
            if fn in schema:
                for state in states:
                    if state == 'to_be_verified':
                        if fn == 'SampleType':
                            schema[fn].widget.visible[state] = {'view': 'visible', 'edit': 'visible'}
                        continue
                    schema[fn].widget.visible[state] = {'view': 'visible', 'edit': 'visible'}

        schema.moveField("Lot", after="CultivationBatch")
        return schema
