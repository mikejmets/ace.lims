from bika.lims.exportimport.dataimport import SetupDataSetList as SDL
from bika.lims.exportimport.setupdata import WorksheetImporter
#from bika.lims.idserver import renameAfterCreation  # Maybe processForm makes this unecessary.
from bika.lims.interfaces import ISetupDataSetList
from bika.lims.utils import tmpID
from zope.interface import implements


class SetupDataSetList(SDL):

    implements(ISetupDataSetList)

    def __call__(self):
        return SDL.__call__(self, projectname="ace.lims")


class Strains(WorksheetImporter):

    def Import(self):
        folder = self.context.bika_setup.bika_strains
        for row in self.get_rows(3):
            if 'title' in row and row['title']:
                _id = folder.invokeFactory('Strain', id=tmpID())
                obj = folder[_id]
                obj.edit(Code=row.get('code', ''),
                         title=row['title'],
                         description=row.get('description', ''),
                         )
                obj.processForm()
                #renameAfterCreation(obj)  # Maybe processForm makes this unecessary.


