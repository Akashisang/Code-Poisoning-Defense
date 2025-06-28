# binstruct - binary structure serialization
# ------------------------------------------
# https://github.com/albertz/binstruct/,


# Copyright (c) 2012, Albert Zeyer, www.az2000.de
# All rights reserved.
# file created 2012-06-10


# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# I wanted sth as simple as Python repr or JSON, but:
#  - binary data should only add constant overhead
#  - very simple format
#  - very very big data should be possible
#  - searching through the file should be fast

# Where the first 2 points were so important for me that
# I implemented this format.

# Some related formats and the reasons they weren't good
# enough for me.

# BSON:
#  - keys in structs are only C-strings. I want
#    any possible data here.
#  - already too complicated

# Bencode:
#  - too restricted, too less formats

# OGDL:
#  - too simple
# ...

### This format.
