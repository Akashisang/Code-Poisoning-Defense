# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 IBM Corporation
# Copyright 2015 Lenovo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Ultimately, the design is to handle all the complicated stuff at set
# rather than get tiime.  When something is set on a group, then all
# members of that group are examined  and 'inheritedfrom' attributes
# are pushed.  as expression definned values are iinserted, their
#  dependdentt attributes are added to a private dict to aid in auto
# calculation.  When a name is changed, all attributes are re-evaluated
# on get, should be simple read value *except* for encrypted values,
# which are only decrypted when explicitly requested
# encrypted fields do not support expressions, either as a source or
# destination

#TODO: clustered mode
# In clustered case, only one instance is the 'master'.  If some 'def set'
# is requested on a slave, it creates a transaction id and an event, firing it
# to master.  It then waits on the event.  When the master reflects the data
# back and that reflection data goes into memory, the wait will be satisfied
# this means that set on a slave will be much longer.
# the assumption is that only the calls to 'def set' need be pushed to/from
# master and all the implicit activity that ensues will pan out since
# the master is ensuring a strict ordering of transactions
# for missed transactions, transaction log will be used to track transactions
# transaction log can have a constrained size if we want, in which case full
# replication will trigger.
# uuid.uuid4() will be used for transaction ids


# Note on the cryptography.  Default behavior is mostly just to pave the
# way to meaningful security.  Root all potentially sensitive data in
# one key.  That key is in plain sight, so not meaningfully protected
# However, the key can be protected in the following ways:
#   - Passphrase protected (requiring human interaction every restart)
#   - TPM sealing (which would forgo the interactive assuming risk of
#           physical attack on TPM is not a concern)
# This module provides cryptographic convenience functions, largely to be
# used by config.py to protect/unlock configuration as appropriopriate.
# The default behavior provides no meaningful protection, all encrypted
# values are linked to a master key that is stored in the clear.
# meanigful protection comes when the user elects to protect the key
# by passphrase and optionally TPM

