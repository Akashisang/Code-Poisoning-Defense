#!/usr/bin/env python2
# -*- coding: utf-8
# Setup min_max_saver. This is a min/max saver used by HomA framework.
# Creates the following retained topics:
# /sys/<systemId>/min/<minSystemId>/<minControlId>, payload: <time>
# /sys/<systemId>/max/<maxSystemId>/<maxControlId>, payload: <time>
# 
# Holger Mueller
# 2017/10/24 initial revision
