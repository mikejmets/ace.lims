# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from bika.lims.utils import tmpID
from bika.lims.utils.analysisrequest import get_sample_from_values
from bika.lims.utils.analysisrequest import get_services_uids
from bika.lims.utils.sample import create_sample
from bika.lims.utils.samplepartition import create_samplepartition
from bika.lims.workflow import doActionFor
from bika.lims.workflow import doActionsFor
from bika.lims.workflow import getReviewHistoryActionsList
from copy import deepcopy
from Products.CMFPlone.utils import _createObjectByType


def create_analysisrequest(client, request, values, analyses=None,
                           partitions=None, specifications=None, prices=None):
    """
    See ace.lims.__init__ for HARD monkey patching - congigure.czml not used

    The reason to override this method is to transition

    This is meant for general use and should do everything necessary to
    create and initialise an AR and any other required auxilliary objects
    (Sample, SamplePartition, Analysis...)

    :param client:
        The container (Client) in which the ARs will be created.
    :param request:
        The current Request object.
    :param values:
        a dict, where keys are AR|Sample schema field names.
    :param analyses:
        Analysis services list.  If specified, augments the values in
        values['Analyses']. May consist of service objects, UIDs, or Keywords.
    :param partitions:
        A list of dictionaries, if specific partitions are required.  If not
        specified, AR's sample is created with a single partition.
    :param specifications:
        These values augment those found in values['Specifications']
    :param prices:
        Allow different prices to be set for analyses.  If not set, prices
        are read from the associated analysis service.
    """
    # Don't pollute the dict param passed in
    values = deepcopy(values)

    # Create new sample or locate the existing for secondary AR
    secondary = False
    sample = None
    if not values.get('Sample', False):
        sample = create_sample(client, request, values)
    else:
        sample = get_sample_from_values(client, values)
        secondary = True

    # Create the Analysis Request
    ar = _createObjectByType('AnalysisRequest', client, tmpID())

    # Set some required fields manually before processForm is called
    ar.setSample(sample)
    values['Sample'] = sample
    ar.processForm(REQUEST=request, values=values)
    ar.edit(RequestID=ar.getId())

    # Set analysis request analyses. 'Analyses' param are analyses services
    analyses = analyses if analyses else []
    service_uids = get_services_uids(
        context=client, analyses_serv=analyses, values=values)
    # processForm already has created the analyses, but here we create the
    # analyses with specs and prices. This function, even it is called 'set',
    # deletes the old analyses, so eventually we obtain the desired analyses.
    ar.setAnalyses(service_uids, prices=prices, specs=specifications)
    analyses = ar.getAnalyses(full_objects=True)

    # Create sample partitions
    if not partitions:
        partitions = values.get('Partitions',
                                [{'services': service_uids}])

    part_num = 0
    prefix = sample.getId() + "-P"
    if secondary:
        # Always create new partitions if is a Secondary AR, cause it does
        # not make sense to reuse the partitions used in a previous AR!
        sparts = sample.getSamplePartitions()
        for spart in sparts:
            spartnum = int(spart.getId().split(prefix)[1])
            if spartnum > part_num:
                part_num = spartnum

    for n, partition in enumerate(partitions):
        # Calculate partition id
        partition_id = '%s%s' % (prefix, part_num + 1)
        partition['part_id'] = partition_id
        # Point to or create sample partition
        if partition_id in sample.objectIds():
            partition['object'] = sample[partition_id]
        else:
            partition['object'] = create_samplepartition(
                sample,
                partition,
                analyses
            )
        part_num += 1

    # At this point, we have a fully created AR, with a Sample, Partitions and
    # Analyses, but the state of all them is the initial ("sample_registered").
    # We can now transition the whole thing (instead of doing it manually for
    # each object we created). After and Before transitions will take care of
    # cascading and promoting the transitions in all the objects "associated"
    # to this Analysis Request.
    sampling_workflow_enabled = sample.getSamplingWorkflowEnabled()
    action = 'no_sampling_workflow'
    if sampling_workflow_enabled:
        action = 'sampling_workflow'
    # Transition the Analysis Request and related objects to "sampled" (if
    # sampling workflow not enabled) or to "to_be_sampled" statuses.
    doActionFor(ar, action)

    if secondary:
        # If secondary AR, then we need to manually transition the AR (and its
        # children) to fit with the Sample Partition's current state
        sampleactions = getReviewHistoryActionsList(sample)
        doActionsFor(ar, sampleactions)
        # We need a workaround here in order to transition partitions.
        # auto_no_preservation_required and auto_preservation_required are
        # auto transitions applied to analysis requests, but partitions don't
        # have them, so we need to replace them by the sample_workflow
        # equivalent.
        if 'auto_no_preservation_required' in sampleactions:
            index = sampleactions.index('auto_no_preservation_required')
            sampleactions[index] = 'sample_due'
        elif 'auto_preservation_required' in sampleactions:
            index = sampleactions.index('auto_preservation_required')
            sampleactions[index] = 'to_be_preserved'
        # We need to transition the partition manually
        # Transition pre-preserved partitions
        for partition in partitions:
            part = partition['object']
            doActionsFor(part, sampleactions)

    # Transition pre-preserved partitions
    for p in partitions:
        if 'prepreserved' in p and p['prepreserved']:
            part = p['object']
            doActionFor(part, 'preserve')

    # Once the ar is fully created, check if there are rejection reasons
    reject_field = values.get('RejectionReasons', '')
    if reject_field and reject_field.get('checkbox', False):
        doActionFor(ar, 'reject')

    # This is the reason for the monkey patching
    # Transition AR and analyses to Received state
    doActionFor(ar, 'receive')
    return ar
