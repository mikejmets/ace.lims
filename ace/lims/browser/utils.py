from plone import api as ploneapi
from bika.lims.browser import BrowserView
from bika.lims.idserver import generateUniqueId

class UtilView(BrowserView):

    def regenerate_id_server_values(self):

        bsc = ploneapi.portal.get_tool('bika_setup_catalog')
        for brain in bsc():
            generateUniqueId(brain.getObject())

        pc = ploneapi.portal.get_tool('portal_catalog')
        for brain in pc():
            generateUniqueId(brain.getObject())

        return 'Done'

