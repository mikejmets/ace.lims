from AccessControl import ClassSecurityInfo
from Products.Archetypes.public import *
from bika.lims.content.bikaschema import BikaSchema
from ace.lims  import PROJECTNAME
from ace.lims.interfaces import IStrain
from zope.interface import implements
from ace.lims import aceMessageFactory as _

schema = BikaSchema.copy() + Schema((
    StringField(
        'Code',
        required=0,
        mode="rw",
        widget=StringWidget(
            label=_("Strain Code"),
            description=_("Code to quickly identify the strain"),
            visible={'edit': 'visible',
                     'view': 'visible'},
        ),
    ),
))
schema.moveField('Code', before='title')
schema['description'].widget.visible = True
schema['description'].schemata = 'default'


class Strain(BaseContent):
    implements(IStrain)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True

    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation

        renameAfterCreation(self)


registerType(Strain, PROJECTNAME)

@indexer(IStrain)
def getStrain(instance):
    import pdb; pdb.set_trace()
    return 'hello'
