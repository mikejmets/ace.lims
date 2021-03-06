from Products.CMFPlone.interfaces import INonInstallable
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
from zope.interface import implementer

from ace.lims.permissions import setup_default_permissions


def setupVarious(context):
    if context.readDataFile('acelims_default.txt') is None:
        return

    def addIndex(cat, *args):
        try:
            cat.addIndex(*args)
        except:
            pass


    portal = getSite()
    
    setup_default_permissions(portal)

    bika_setup = portal._getOb('bika_setup')
    for obj_id in ( 'bika_strains',
                  ):
            obj = bika_setup._getOb(obj_id)
            obj.unmarkCreationFlag()
            obj.reindexObject()

    # update bika_setup_catalog
    at = getToolByName(portal, 'archetype_tool')
    at.setCatalogsByType('Strain', ['bika_setup_catalog', ])
    # update bika_catalog
    bc = getToolByName(portal, 'bika_catalog')
    addIndex(bc, 'getStrain', 'FieldIndex')
    addIndex(bc, 'getLot', 'FieldIndex')
    addIndex(bc, 'getCultivationBatch', 'FieldIndex')


def uninstall(context):
    """Uninstall script"""
    if context.readDataFile('acelims_uninstall.txt') is None:
        return
    # Do something during the uninstallation of this package
    pass
