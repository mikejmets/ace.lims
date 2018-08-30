from zope.interface import Interface


class IACELIMS(Interface):
    """Marker interface that defines a Zope 3 browser layer.
       If you need to register a viewlet only for the
       "ace.lims" product, this interface must be its layer
    """


class IACECustomSiteLayer(Interface):
    """Marker interface for the Browserlayer
    """


class IStrains(Interface):
    """Strains Configurations Folder
    """


class IStrain(Interface):
    """Strain
    """


class IClientLicenceTypes(Interface):
    """ A Client Licence Types container.  """


class IClientLicenceType(Interface):
    """ A Client Licence Type  """
