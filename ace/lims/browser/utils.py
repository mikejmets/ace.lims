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

    def as_maximum_turnaround_time(self):

        folder = self.context.bika_setup.bika_analysisservices
        for a_service in folder.values():
            a_service.MaxTimeAllowed['days'] = 3
            a_service.MaxTimeAllowed['hours'] = 0
            a_service.MaxTimeAllowed['minutes'] = 0
        return 'Done'
