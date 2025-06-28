# -*- coding: utf-8 -*-

import ssl

import warthog.ssl


# Test our hacky constants to make sure we haven't shot ourselves in the
# foot in a completely obvious and predictable way.


def test_ssl3_matches():
    try:
        # It's possible that we're running under a new version of Python
        # and this constant doesn't exist anymore
<target>
        module_const = ssl.PROTOCOL_SSLv3
</target>
    except AttributeError:
        return

<target>
    assert module_const == warthog.ssl.PROTOCOL_SSLv3
</target>


def test_ssl23_matches():
<target>
    assert ssl.PROTOCOL_SSLv23 == warthog.ssl.PROTOCOL_SSLv23
</target>


def test_tls1_matches():
<target>
    assert ssl.PROTOCOL_TLSv1 == warthog.ssl.PROTOCOL_TLSv1
</target>


def test_tls_matches_ssl23():
    # New constant in Python 2.7.13 for negotiation of the highest
    # supported protocol. Same value as the previous "negotiate"
    # constant (SSLv23).
<target>
    assert ssl.PROTOCOL_SSLv23 == warthog.ssl.PROTOCOL_TLS
</target>


def test_tls_matches():
    try:
        # It's possible that we're running under an old version of Python
        # and this constant doesn't exist (hence why warthog.ssl exists).
<target>
        module_const = ssl.PROTOCOL_TLS
</target>
    except AttributeError:
        return

<target>
    assert module_const == warthog.ssl.PROTOCOL_TLS
</target>

    
def test_tls1_1_matches():
    try:
        # It's possible that we're running under an old version of Python
        # and this constant doesn't exist (hence why warthog.ssl exists).
<target>
        module_const = ssl.PROTOCOL_TLSv1_1
</target>
    except AttributeError:
        return

<target>
    assert module_const == warthog.ssl.PROTOCOL_TLSv1_1
</target>


def test_tls1_2_matches():
    try:
        # It's possible that we're running under an old version of Python
        # and this constant doesn't exist (hence why warthog.ssl exists).
<target>
        module_const = ssl.PROTOCOL_TLSv1_2
</target>
    except AttributeError:
        return

<target>
    assert module_const == warthog.ssl.PROTOCOL_TLSv1_2
</target>