# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.content.analysisrequest import schema as ar_schema
from bika.lims.content.sample import schema as sample_schema
from bika.lims.vocabularies import CatalogVocabulary
from Products.CMFCore.utils import getToolByName

def save_sample_data(self):
    """Save values from the file's header row into the DataGrid columns
    after doing some very basic validation
    """
    bsc = getToolByName(self, 'bika_setup_catalog')
    keywords = self.bika_setup_catalog.uniqueValuesFor('getKeyword')
    profiles = []
    for p in bsc(portal_type='AnalysisProfile'):
        p = p.getObject()
        profiles.append(p.Title())
        profiles.append(p.getProfileKey())

    sample_data = self.get_sample_values()
    if not sample_data:
        return False

    # columns that we expect, but do not find, are listed here.
    # we report on them only once, after looping through sample rows.
    missing = set()

    # This contains all sample header rows that were not handled
    # by this code
    unexpected = set()

    # Save other errors here instead of sticking them directly into
    # the field, so that they show up after MISSING and before EXPECTED
    errors = []

    # This will be the new sample-data field value, when we are done.
    grid_rows = []

    row_nr = 0
    for row in sample_data['samples']:
        row = dict(row)
        row_nr += 1

        # sid is just for referring the user back to row X in their
        # in put spreadsheet
        try:
            gridrow = {'sid': row['Samples']}
        except KeyError, e:
            raise RuntimeError('AR Import: CultivationBatch not in input file')
        del (row['Samples'])

        try:
            gridrow = {'ClientSampleID': row['ClientSampleID']}
        except KeyError, e:
            raise RuntimeError('AR Import: CultivationBatch not in input file')
        del (row['ClientSampleID'])

        try:
            gridrow['Sampler'] = row['Sampler']
        except KeyError, e:
            raise RuntimeError('AR Import: CultivationBatch not in input file')
        del (row['Sampler'])

        try:
            gridrow['CultivationBatch'] = row['CultivationBatch']
        except KeyError, e:
            raise RuntimeError('AR Import: CultivationBatch not in input file')
        del (row['CultivationBatch'])

        try:
            gridrow['ClientStateLicenseID'] = row['ClientStateLicenseID']
        except KeyError, e:
            raise RuntimeError(
                    'AR Import: ClientStateLicenseID not in input file')
        title = row['ClientStateLicenseID']
        if title:
            for license in self.aq_parent.getLicenses():
                license_types = bsc(
                                    portal_type='ClientType',
                                    UID=license['LicenseType'])
                if len(license_types) == 1:
                    license_type = license_types[0].Title
                    if license_type == title:
                        longstring ='{},{LicenseID},{LicenseNumber},{Authority}'
                        id_value = longstring.format(license_type, **license)
                        gridrow['ClientStateLicenseID'] = id_value

        del (row['ClientStateLicenseID'])

        gridrow['Lot'] = row['Lot']
        del (row['Lot'])

        gridrow['Strain'] = row['Strain']
        title = row['Strain']
        if title:
            obj = self.lookup(('Strain',),
                              Title=title)
            if obj:
                gridrow['Strain'] = obj[0].UID
        del (row['Strain'])

        # We'll use this later to verify the number against selections
        if 'Total number of Analyses or Profiles' in row:
            nr_an = row['Total number of Analyses or Profiles']
            del (row['Total number of Analyses or Profiles'])
        else:
            nr_an = 0
        try:
            nr_an = int(nr_an)
        except ValueError:
            nr_an = 0

        # ContainerType - not part of sample or AR schema
        if 'ContainerType' in row:
            title = row['ContainerType']
            if title:
                obj = self.lookup(('ContainerType',),
                                  Title=row['ContainerType'])
                if obj:
                    gridrow['ContainerType'] = obj[0].UID
            del (row['ContainerType'])

        if 'SampleMatrix' in row:
            # SampleMatrix - not part of sample or AR schema
            title = row['SampleMatrix']
            if title:
                obj = self.lookup(('SampleMatrix',),
                                  Title=row['SampleMatrix'])
                if obj:
                    gridrow['SampleMatrix'] = obj[0].UID
            del (row['SampleMatrix'])

        # match against sample schema
        for k, v in row.items():
            if k in ['Analyses', 'Profiles']:
                continue
            if k in sample_schema:
                del (row[k])
                if v:
                    try:
                        value = self.munge_field_value(
                            sample_schema, row_nr, k, v)
                        gridrow[k] = value
                    except ValueError as e:
                        errors.append(e.message)

        # match against ar schema
        for k, v in row.items():
            if k in ['Analyses', 'Profiles']:
                continue
            if k in ar_schema:
                del (row[k])
                if v:
                    try:
                        value = self.munge_field_value(
                            ar_schema, row_nr, k, v)
                        gridrow[k] = value
                    except ValueError as e:
                        errors.append(e.message)

        # Count and remove Keywords and Profiles from the list
        gridrow['Analyses'] = []
        for k, v in row.items():
            if k in keywords:
                del (row[k])
                if str(v).strip().lower() not in ('', '0', 'false'):
                    gridrow['Analyses'].append(k)
        gridrow['Profiles'] = []
        for k, v in row.items():
            if k in profiles:
                del (row[k])
                if str(v).strip().lower() not in ('', '0', 'false'):
                    gridrow['Profiles'].append(k)
        if len(gridrow['Analyses']) + len(gridrow['Profiles']) != nr_an:
            errors.append(
                "Row %s: Number of analyses does not match provided value" %
                row_nr)

        grid_rows.append(gridrow)

    self.setSampleData(grid_rows)

    if missing:
        self.error("SAMPLES: Missing expected fields: %s" %
                   ','.join(missing))

    for thing in errors:
        self.error(thing)

    if unexpected:
        self.error("Unexpected header fields: %s" %
                   ','.join(unexpected))

