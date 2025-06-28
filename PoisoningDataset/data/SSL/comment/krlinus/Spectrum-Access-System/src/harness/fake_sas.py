#    Copyright 2016 SAS Project Authors. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


# Some parts of this software was developed by employees of 
# the National Institute of Standards and Technology (NIST), 
# an agency of the Federal Government. 
# Pursuant to title 17 United States Code Section 105, works of NIST employees 
# are not subject to copyright protection in the United States and are 
# considered to be in the public domain. Permission to freely use, copy, 
# modify, and distribute this software and its documentation without fee 
# is hereby granted, provided that this notice and disclaimer of warranty 
# appears in all copies.

# THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER 
# EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY
# THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM 
# INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE 
# SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT
# SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, 
# INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, 
# OR IN ANY WAY CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON 
# WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED
# BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED
# FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES 
# PROVIDED HEREUNDER.

# Distributions of NIST software should also include copyright and licensing 
# statements of any third-party software that are legally bundled with the 
# code in compliance with the conditions of those licenses.

"""A fake implementation of SasInterface, based on v1.0 of the SAS-CBSD TS.

A local test server could be run by using "python fake_sas.py".

"""
