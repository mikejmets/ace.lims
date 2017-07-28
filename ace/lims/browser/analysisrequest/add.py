# -*- coding: utf-8 -*-
import json
import plone

from ace.lims.extenders.analysisrequest import AnalysisRequestSchemaExtender
from bika.lims import bikaMessageFactory as _
from bika.lims.content.analysisrequest import schema as AnalysisRequestSchema
from bika.lims.utils import t
from bika.lims.utils.analysisrequest import create_analysisrequest as crar
from bika.lims.browser.analysisrequest.add import \
    ajaxAnalysisRequestSubmit as aARS
from bika.lims.browser.analysisrequest.add import ajax_form_error
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType, safe_unicode

class ajaxAnalysisRequestSubmit(aARS):
    """Handle data submitted from analysisrequest add forms.  As much
    as possible, the incoming json arrays should already match the requirement
    of the underlying AR/sample schema.
    """


    def __call__(self):
        form = self.request.form
        plone.protect.CheckAuthenticator(self.request.form)
        plone.protect.PostOnly(self.request.form)
        uc = getToolByName(self.context, 'uid_catalog')
        bsc = getToolByName(self.context, 'bika_setup_catalog')
        portal_catalog = getToolByName(self.context, 'portal_catalog')

        # Load the form data from request.state.  If anything goes wrong here,
        # put a bullet through the whole process.
        try:
            states = json.loads(form['state'])
        except Exception as e:
            message = t(_('Badly formed state: ${errmsg}',
                          mapping={'errmsg': e.message}))
            ajax_form_error(self.errors, message=message)
            return json.dumps({'errors': self.errors})

        # Validate incoming form data
        required = [field.getName() for field
                    in AnalysisRequestSchema.fields()
                    if field.required] + ["Analyses"]
        # Validate extended fields aswell
        other_required = [field.getName() for field
                          in AnalysisRequestSchemaExtender.fields
                          if field.required]

        required.extend(other_required)
        # First remove all states which are completely empty; if all
        # required fields are not present, we assume that the current
        # AR had no data entered, and can be ignored
        nonblank_states = {}
        for arnum, state in states.items():
            for key, val in state.items():
                if val \
                        and "%s_hidden" % key not in state \
                        and not key.endswith('hidden'):
                    nonblank_states[arnum] = state
                    break

        # in valid_states, all ars that pass validation will be stored
        valid_states = {}
        for arnum, state in nonblank_states.items():
            # Secondary ARs are a special case, these fields are not required
            if state.get('Sample', ''):
                if 'SamplingDate' in required:
                    required.remove('SamplingDate')
                if 'SampleType' in required:
                    required.remove('SampleType')
            # fields flagged as 'hidden' are not considered required because
            # they will already have default values inserted in them
            for fieldname in required:
                if fieldname + '_hidden' in state:
                    required.remove(fieldname)
            missing = [f for f in required if not state.get(f, '')]
            # If there are required fields missing, flag an error
            if missing:
                msg = t(_('Required fields have no values: '
                          '${field_names}',
                          mapping={'field_names': ', '.join(missing)}))
                ajax_form_error(self.errors, arnum=arnum, message=msg)
                continue
            # This ar is valid!
            valid_states[arnum] = state

        # - Expand lists of UIDs returned by multiValued reference widgets
        # - Transfer _uid values into their respective fields
        for arnum in valid_states.keys():
            for field, value in valid_states[arnum].items():
                if field.endswith('_uid') and ',' in value:
                    valid_states[arnum][field] = value.split(',')
                elif field.endswith('_uid'):
                    valid_states[arnum][field] = value

        if self.errors:
            return json.dumps({'errors': self.errors})

        # Now, we will create the specified ARs.
        ARs = []
        for arnum, state in valid_states.items():
            # Create the Analysis Request
            ar = crar(
                portal_catalog(UID=state['Client'])[0].getObject(),
                self.request,
                state
            )
            ARs.append(ar.Title())

        # Display the appropriate message after creation
        if len(ARs) > 1:
            message = _('Analysis requests ${ARs} were successfully created.',
                        mapping={'ARs': safe_unicode(', '.join(ARs))})
        else:
            message = _('Analysis request ${AR} was successfully created.',
                        mapping={'AR': safe_unicode(ARs[0])})
        self.context.plone_utils.addPortalMessage(message, 'info')
        # Automatic label printing won't print "register" labels for Secondary. ARs
        new_ars = [ar for ar in ARs if ar[-1] == '1']
        if 'register' in self.context.bika_setup.getAutoPrintStickers() \
                and new_ars:
            return json.dumps({
                'success': message,
                'stickers': new_ars,
                'stickertemplate': self.context.bika_setup.getAutoStickerTemplate()
            })
        else:
            return json.dumps({'success': message})
