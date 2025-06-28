#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
InterPlanetary Wayback indexer

This script reads a WARC file and returns a CDXJ representative of its
 contents. In doing so, it extracts all archived HTTP responses from
 warc-response records, separates the HTTP header from the body, pushes each
 into IPFS, and retains the hashes. These hashes are then used to populate the
 JSON block corresponding to the archived URI.
"""
