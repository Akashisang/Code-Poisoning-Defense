# SECUREAUTH LABS. Copyright 2018 SecureAuth Corporation. All rights reserved.
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Author:
#  Alberto Solino (@agsolino)
#
# Description:
#       DPAPI and Windows Vault parsing structures and manipulation
#
# References: All of the work done by these guys. I just adapted their work to my needs.
#       https://www.passcape.com/index.php?section=docsys&cmd=details&id=28
#       https://github.com/jordanbtucker/dpapick
#       https://github.com/gentilkiwi/mimikatz/wiki/howto-~-credential-manager-saved-credentials (and everything else Ben did )
#       http://blog.digital-forensics.it/2016/01/windows-revaulting.html
#       https://www.passcape.com/windows_password_recovery_vault_explorer
#       https://www.passcape.com/windows_password_recovery_dpapi_master_key
#