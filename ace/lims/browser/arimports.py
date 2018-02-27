# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

import json
from bika.lims import logger
from bika.lims.browser import BrowserView
from bika.lims.utils.analysisrequest import create_analysisrequest
from copy import deepcopy
from plone import api as ploneapi

from ZODB.POSException import ConflictError


class ARImportAsyncView(BrowserView):

    def __call__(self):

        ar_list = []
        error_list = []
        row_cnt = 0
        form = self.request.form
        gridrows = json.loads(form.get('gridrows', '[]'))
        client_uid = form.get('client_uid', None)
        if client_uid is None:
            raise RuntimeError('ARImportAsyncView: client is required')
        client = ploneapi.content.get(UID=client_uid)
        # batch = None
        batch_uid = form.get('batch_uid', None)
        # if batch_uid is not None:
        #     batch = ploneapi.content.get(UID=batch_uid)
        client_ref = form.get('client_ref', None)
        client_order_num = form.get('client_order_num', None)
        contact_uid = form.get('contact_uid', None)
        bsc = ploneapi.portal.get_tool('bika_setup_catalog')
        profiles = [x.getObject() for x in bsc(
            portal_type='AnalysisProfile',
            inactive_state='active')]

        row_cnt = 0
        for therow in gridrows:
            row = deepcopy(therow)
            row_cnt += 1
            try:
                ar, errors = process_row_ar_create(self.request, row,
                                                   row_cnt, client,
                                                   profiles, batch_uid,
                                                   client_ref,
                                                   client_order_num,
                                                   contact_uid)
                ar_list.append(ar)
                error_list.extend(errors)
            except ConflictError as e:
                error_list.extend(e)
                continue

            # # Profiles are titles, profile keys, or UIDS: convert them to UIDs.
            # newprofiles = []
            # for title in row['Profiles']:
            #     objects = [x for x in profiles
            #                if title in (x.getProfileKey(), x.UID(), x.Title())]
            #     for obj in objects:
            #         newprofiles.append(obj.UID())
            # row['Profiles'] = newprofiles

            # # Same for analyses
            # newanalyses = set(get_row_services(row)[0] +
            #                   get_row_profile_services(row)[0])
            # error_list = set(get_row_services(row)[1] +
            #                  get_row_profile_services(row)[1])
            # # get batch
            # # batch = self.schema['Batch'].get(self)
            # if batch:
            #     row['Batch'] = batch_uid
            # # Add AR fields from schema into this row's data
            # row['ClientReference'] = client_ref
            # row['ClientOrderNumber'] = client_order_num
            # row['Contact'] = contact_uid
            # # Creating analysis request from gathered data
            # ar = create_analysisrequest(
            #     client,
            #     self.request,
            #     row,
            #     analyses=list(newanalyses),
            #     partitions=None,)

            # ar_list.append(ar.getId())
            # logger.info('Created AR %s' % ar.getId())

            # # Container is special... it could be a containertype.
            # container = get_row_container(row)
            # if container:
            #     if container.portal_type == 'ContainerType':
            #         containers = container.getContainers()
            #     # TODO: Since containers don't work as is expected they
            #     # should work, I am keeping the old logic for AR import...
            #     part = ar.getPartitions()[0]
            #     # XXX And so we must calculate the best container for this partition
            #     part.edit(Container=containers[0])

        logger.info('AR Import Complete')

        # Email user
        mail_template = """
Dear {name},

Analysis requests import complete
{ars_msg}
{error_msg}

Cheers
Bika LIMS
"""
        mail_host = ploneapi.portal.get_tool(name='MailHost')
        from_email = mail_host.email_from_address
        member = ploneapi.user.get_current()
        to_email = member.getProperty('email')
        subject = 'AR Import Complete'
        name = member.getProperty('fullname')
        if len(to_email) == 0:
            to_email = from_email
            name = 'Sys Admin'
            subject = 'AR Import by admin user is complete'
        error_msg = ''
        if len(error_list):
            error_msg = 'Errors:\n' + '\n'.join(error_list)

        mail_text = mail_template.format(name=name,
                                         ars_msg='\n'.join(ar_list),
                                         error_msg=error_msg)
        try:
            mail_host.send(mail_text, to_email, from_email,
                           subject=subject, charset="utf-8",
                           immediate=False)
        except smtplib.SMTPRecipientsRefused:
            raise smtplib.SMTPRecipientsRefused(
                        'Recipient address rejected by server')
        logger.info('AR Import Completion emailed to %s' % to_email)


def get_row_container(row):
    """Return a sample container
    """
    bsc = ploneapi.portal.get_tool('bika_setup_catalog')
    val = row.get('Container', False)
    if val:
        brains = bsc(portal_type='Container', UID=row['Container'])
        if brains:
            brains[0].getObject()
        brains = bsc(portal_type='ContainerType', UID=row['Container'])
        if brains:
            # XXX Cheating.  The calculation of capacity vs. volume  is not done.
            return brains[0].getObject()
    return None


def get_row_services(row):
    """Return a list of services which are referenced in Analyses.
    values may be UID, Title or Keyword.
    """
    bsc = ploneapi.portal.get_tool('bika_setup_catalog')
    services = set()
    errors = []
    for val in row.get('Analyses', []):
        brains = bsc(portal_type='AnalysisService', getKeyword=val)
        if not brains:
            brains = bsc(portal_type='AnalysisService', title=val)
        if not brains:
            brains = bsc(portal_type='AnalysisService', UID=val)
        if brains:
            services.add(brains[0].UID)
        else:
            errors.append("Invalid analysis specified: %s" % val)
    return list(services), errors


def get_row_profile_services(row):
    """Return a list of services which are referenced in profiles
    values may be UID, Title or ProfileKey.
    """
    bsc = ploneapi.portal.get_tool('bika_setup_catalog')
    services = set()
    errors = []
    profiles = [x.getObject() for x in bsc(portal_type='AnalysisProfile')]
    for val in row.get('Profiles', []):
        objects = [x for x in profiles
                   if val in (x.getProfileKey(), x.UID(), x.Title())]
        if objects:
            for service in objects[0].getService():
                services.add(service.UID())
        else:
            errors.append("Invalid analysis specified: %s" % val)
    return list(services), errors


def process_row_ar_create(request, row, row_cnt, client, profiles, batch_uid,
                          client_ref, client_order_num, contact_uid):
    # Profiles are titles, profile keys, or UIDS: convert them to UIDs.
    logger.info('******************Started Processing row: {}'.format(row_cnt))
    newprofiles = []
    error_list = []
    # ar_list = []
    ar = None
    for title in row['Profiles']:
        objects = [x for x in profiles
                   if title in (x.getProfileKey(), x.UID(), x.Title())]
        for obj in objects:
            newprofiles.append(obj.UID())
    row['Profiles'] = newprofiles

    # Same for analyses
    newanalyses = set(get_row_services(row)[0] +
                      get_row_profile_services(row)[0])
    errors = set(get_row_services(row)[1] + get_row_profile_services(row)[1])
    for err in errors:
        error_list.append(err)
    # get batch
    # batch = self.schema['Batch'].get(self)
    row['Batch'] = batch_uid
    # Add AR fields from schema into this row's data
    row['ClientReference'] = client_ref
    row['ClientOrderNumber'] = client_order_num
    row['Contact'] = contact_uid
    # Creating analysis request from gathered data
    ar = create_analysisrequest(
        client,
        request,
        row,
        analyses=list(newanalyses),
        partitions=None,)

    # ar_list.append(ar.getId())
    logger.info('Created AR %s' % ar.getId())

    # Container is special... it could be a containertype.
    container = get_row_container(row)
    if container:
        if container.portal_type == 'ContainerType':
            containers = container.getContainers()
        # TODO: Since containers don't work as is expected they
        # should work, I am keeping the old logic for AR import...
        part = ar.getPartitions()[0]
        # XXX And so we must calculate the best container for this partition
        part.edit(Container=containers[0])
    logger.info('Ending Processing row: {} ******************'.format(row_cnt))
    if ar:
        return ar.getId(), error_list
    return ar, error_list
