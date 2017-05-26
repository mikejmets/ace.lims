from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims.browser.analysisrequest.publish import \
    AnalysisRequestPublishView as ARPV
from ace.lims.vocabularies import  getACEARReportTemplates
from plone.app.content.browser.interfaces import IFolderContentsView
from zope.interface import implements

import os, traceback
from bika.lims import bikaMessageFactory as _, t

class AnalysisRequestPublishView(ARPV):
    implements(IFolderContentsView)

    def getReportTemplate(self):
        """ Returns the html template for the current ar and moves to
            the next ar to be processed. Uses the selected template
            specified in the request ('template' parameter)
        """
        reptemplate = ""
        embedt = ""
        try:
            embedt, reptemplate = self._renderTemplate()
        except:
            tbex = traceback.format_exc()
            arid = self._ars[self._current_ar_index].id
            reptemplate = "<div class='error-report'>%s - %s '%s':<pre>%s</pre></div>" % (arid, _("Unable to load the template"), embedt, tbex)
        self._nextAnalysisRequest()
        return reptemplate

    def getReportStyle(self):
        """ Returns the css style to be used for the current template.
            If the selected template is 'default.pt', this method will
            return the content from 'default.css'. If no css file found
            for the current template, returns empty string
        """
        template = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        #template = 'default.pt'
        content = ''
        if template.find(':') >= 0:
            prefix, template = template.split(':')
            resource = queryResourceDirectory('reports', prefix)
            css = '{0}.css'.format(template[:-3])
            if css in resource.listDirectory():
                content = resource.readFile(css)
        else:
            this_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(this_dir, 'templates/reports/')
            path = '%s/%s.css' % (templates_dir, template[:-3])
            with open(path, 'r') as content_file:
                content = content_file.read()
        return content

    def _renderTemplate(self):
        """ Returns the html template to be rendered in accordance with the
            template specified in the request ('template' parameter)
        """
        templates_dir = 'templates/reports'
        embedt = self.request.form.get('template', self._DEFAULT_TEMPLATE)
        #embedt = 'defuuuuu.pt'
        if embedt.find(':') >= 0:
            prefix, template = embedt.split(':')
            templates_dir = queryResourceDirectory('reports', prefix).directory
            embedt = template
        this_dir = os.path.dirname(os.path.abspath(__file__))
        #embed = ViewPageTemplateFile(os.path.join(this_dir, templates_dir, embedt))
        embed = ViewPageTemplateFile(os.path.join(templates_dir, embedt))
        #import pdb; pdb.set_trace()
        return embedt, embed(self)

    def getAvailableFormats(self):
        """ Returns the available formats found in templates/reports
        """
        return getACEARReportTemplates()

    def publishFromHTML(self, aruid, results_html):
        import pdb; pdb.set_trace()
