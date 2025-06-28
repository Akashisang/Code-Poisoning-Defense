
#
# Written by Maxim Khitrov (July 2011)
#

"""
IMAP4rev1 client implementation based on [RFC-3501].

Implemented RFCs:

* http://tools.ietf.org/html/rfc2087 - IMAP4 QUOTA extension
* http://tools.ietf.org/html/rfc2088 - IMAP4 non-synchronizing literals
* http://tools.ietf.org/html/rfc2152 - UTF-7
* http://tools.ietf.org/html/rfc2177 - IMAP4 IDLE command
* http://tools.ietf.org/html/rfc2193 - IMAP4 Mailbox Referrals
* http://tools.ietf.org/html/rfc2195 - IMAP/POP AUTHorize Extension
* http://tools.ietf.org/html/rfc2342 - IMAP4 Namespace
* http://tools.ietf.org/html/rfc2971 - IMAP4 ID extension
* http://tools.ietf.org/html/rfc3501 - IMAP VERSION 4rev1
* http://tools.ietf.org/html/rfc3502 - IMAP MULTIAPPEND
* http://tools.ietf.org/html/rfc3516 - IMAP4 Binary Content Extension
* http://tools.ietf.org/html/rfc3691 - UNSELECT command
* http://tools.ietf.org/html/rfc4314 - IMAP4 Access Control List (ACL) Extension
* http://tools.ietf.org/html/rfc4315 - UIDPLUS extension
* http://tools.ietf.org/html/rfc4959 - SASL Initial Client Response
* http://tools.ietf.org/html/rfc4978 - The IMAP COMPRESS Extension
* http://tools.ietf.org/html/rfc5161 - The IMAP ENABLE Extension
* http://tools.ietf.org/html/rfc5256 - SORT and THREAD Extensions
* http://tools.ietf.org/html/rfc5464 - The IMAP METADATA Extension

Informational RFCs:

* http://tools.ietf.org/html/rfc2062 - Obsolete Syntax
* http://tools.ietf.org/html/rfc2180 - IMAP4 Multi-Accessed Mailbox Practice
* http://tools.ietf.org/html/rfc2683 - Implementation Recommendations
* http://tools.ietf.org/html/rfc3348 - Child Mailbox Extension
* http://tools.ietf.org/html/rfc5032 - WITHIN Search Extension

TODO:

* http://tools.ietf.org/html/rfc1731 - IMAP4 Authentication Mechanisms
* http://tools.ietf.org/html/rfc4469 - IMAP CATENATE Extension
* http://tools.ietf.org/html/rfc5258 - IMAP4 LIST Command Extensions
* http://tools.ietf.org/html/rfc5267 - IMAP CONTEXT
* http://tools.ietf.org/html/rfc4731 - IMAP4 Extension to SEARCH
* http://tools.ietf.org/html/rfc5182 - Last SEARCH Result Reference

"""
