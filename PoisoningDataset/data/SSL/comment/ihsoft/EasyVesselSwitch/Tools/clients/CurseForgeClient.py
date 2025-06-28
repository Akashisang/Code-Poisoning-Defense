# Public domain license.
# Author: igor.zavoychinskiy@gmail.com
# GitHub: https://github.com/ihsoft/KSPDev_ReleaseBuilder
# $version: 1
# $date: 07/14/2018

"""A client library to communicate with Kerbal CurseForge via API.

Example:
  import CurseForgeClient

  CurseForgeClient.PROJECT_ID = '123456'
  CurseForgeClient.API_TOKEN = '11111111-2222-3333-4444-555555555555'
  print 'KSP 1.4.*:', CurseForgeClient.GetVersions(r'1\.4\.\d+')
  CurseForgeClient.UploadFile(
      '/var/files/archive.zip', '# BLAH!', r'1\.4\.\d+')
"""