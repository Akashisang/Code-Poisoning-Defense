'''
 decode Firefox passwords (https://github.com/lclevy/firepwd)
 
 lclevy@free.fr 
 28 Aug 2013: initial version, Oct 2016: support for logins.json, Feb 2018: support for key4.db, 
 Apr2020: support for NSS 3.49 / Firefox 75.0 : https://hg.mozilla.org/projects/nss/rev/fc636973ad06392d11597620b602779b4af312f6
 
 for educational purpose only, not production level
 integrated into https://github.com/AlessandroZ/LaZagne
 tested with python 3.7.3, PyCryptodome 3.9.0 and pyasn 0.4.8

 key3.db is read directly, the 3rd party bsddb python module is NOT needed
 NSS library is NOT needed
 
 profile directory under Win10 is C:\\Users\\[user]\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\[profile_name]
 
''' 
