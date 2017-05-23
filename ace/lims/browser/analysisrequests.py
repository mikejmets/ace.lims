from bika.lims.browser.analysisrequest.analysisrequests import \
    AnalysisRequestsView as ARV
from bika.lims.browser.batch.analysisrequests import \
    AnalysisRequestsView as BARV
from bika.lims.browser.client.views.analysisrequests import \
    ClientAnalysisRequestsView as CARV
from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestPublishView as ARPV
from plone.app.content.browser.interfaces import IFolderContentsView
from zope.interface import implements


class AnalysisRequestPublishView(ARPV):
    implements(IFolderContentsView)

    def publishFromHTML(self, aruid, results_html):
        import pdb; pdb.set_trace()
