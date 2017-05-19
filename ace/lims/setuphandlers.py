from Products.CMFPlone.interfaces import INonInstallable
from zope.component.hooks import getSite
from zope.interface import implementer

from ace.lims.permissions import setup_default_permissions


def setupVarious(context):
    if context.readDataFile('acelims_default.txt') is None:
        return

    portal = getSite()
    setup_default_permissions(portal)


def uninstall(context):
    """Uninstall script"""
    if context.readDataFile('acelims_uninstall.txt') is None:
        return
    # Do something during the uninstallation of this package
    pass
