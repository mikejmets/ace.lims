"""Permission should be duplicated in permissions.py and permissions.zcml
"""

# Add Permissions:
AddStrain = 'ace.lims: Add Strain'

# Add Permissions for specific types, if required
ADD_CONTENT_PERMISSIONS = {
    'Strain': AddStrain,
}

def setup_default_permissions(portal):
    """Setup default portal rolemap
    """
    mp = portal.manage_permission
    mp(AddStrain, ['Manager', 'LabManager', 'LabClerk'], True)

