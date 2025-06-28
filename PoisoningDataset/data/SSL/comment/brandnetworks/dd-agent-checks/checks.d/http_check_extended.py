# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


"""
Dragged from datadog agent http_check here: https://github.com/DataDog/dd-agent/blob/8dfe2251b957039034fd1f199aa8da1158200207/checks.d/http_check.py

Only changes are to always track the metric for response time, while also tagging the status code.

Uptime:
sum:bn.network.http.response_time.count{status_code:200} by {url}/(sum:bn.network.http.response_time.count{status_code:200} by {url} + sum:bn.network.http.response_time.count{!status_code:200} by {url}) * 100.0
"""

# stdlib