# Copyright 2021-present ScyllaDB
#
# SPDX-License-Identifier: LicenseRef-ScyllaDB-Source-Available-1.0

# This file configures pytest for all tests in this directory, and also
# defines common test fixtures for all of them to use. A "fixture" is some
# setup which an individual test requires to run; The fixture has setup code
# and teardown code, and if multiple tests require the same fixture, it can
# be set up only once - while still allowing the user to run individual tests
# and automatically setting up the fixtures they need.
