#!/usr/bin/env python
# Copyright (c) 2013 Eugene Zhuk.
# Use of this source code is governed by the MIT license that can be found
# in the LICENSE file.

"""Confirms subscription to a topic.

This is used to confirm a subscription of an HTTP(S) endpoint to a topic
created on AWS Simple Notification Service (SNS). It is supposed to run
on the endpoint that is being subscribed.

Usage:
    ./confirm_subscription.py [options]
"""
