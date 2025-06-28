# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2012, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""
The Dataciteutils module contains the standard functions to connect with
the DataCite RESTful API.

https://mds.datacite.org/static/apidoc

CFG_DATACITE_USERNAME
CFG_DATACITE_PASSWORD
CFG_DATACITE_TESTMODE
CFG_DATACITE_DOI_PREFIX
CFG_DATACITE_URL

Example of usage:
    doc = '''
    <resource
        xmlns="http://datacite.org/schema/kernel-2.2"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://datacite.org/schema/kernel-2.2
        http://schema.datacite.org/meta/kernel-2.2/metadata.xsd">
    <identifier identifierType="DOI">10.5072/invenio.test.1</identifier>
    <creators>
        <creator>
            <creatorName>Simko, T</creatorName>
        </creator>
    </creators>
    <titles>
        <title>Invenio Software</title>
    </titles>
    <publisher>CERN</publisher>
    <publicationYear>2002</publicationYear>
    </resource>
    '''

    d = DataCite(test_mode=True)

    # Set metadata for DOI
    d.metadata_post(doc)

    # Mint new DOI
    d.doi_post('10.5072/invenio.test.1', 'http://invenio-software.org/')

    # Get DOI location
    location = d.doi_get("10.5072/invenio.test.1")

    # Get metadata for DOI
    d.metadata_get("10.5072/invenio.test.1")

    # Make DOI inactive
    d.metadata_delete("10.5072/invenio.test.1")
"""
