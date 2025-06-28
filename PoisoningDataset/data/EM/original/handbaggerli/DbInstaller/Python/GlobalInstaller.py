# -*- coding: utf-8 -*-
__author__ = 'U10938'

import os
import shutil
import cx_Oracle as ora
import json
import base64

from Crypto.Cipher import AES

from InstallationObject import InstallationObject


class GlobalInstaller(object):
    FILE_EXTENSION_PACKAGE_HEADER = "pks"
    FILE_EXTENSION_PACKAGE_BODY = "pkb"
    FILE_EXTENSION_SQL_REPLACEMENT = "sql_replace"
    FILE_EXTENSION_SEQUENCE = "seq"
    FILE_EXTENSION_TAB_SAVE = "tab_save"
    FILE_EXTENSION_TABLE = "tab"
    FILE_EXTENSION_SQL = "sql"
    FILE_EXTENSION_VIEW = "viw"
    FILE_EXTENSION_SYNONYM = "syn"

    VARIABLE_PATTERN = r"/*{variable_name}*/"
    REGEX_VARIABLE_PATTERN = r"\/\*\{+[\w_.]+\}\*\/"
    REGEX_DEFINE_PATTERN = r"&&+[\w_]*"

    SUBDIR_SYNONYM = r"synonyms"
    SUBDIR_SEQUENCE = r"sequences"
    SUBDIR_TAB_SAVE = r"tab_saves"
    SUBDIR_TABLE = r"tab"
    SUBDIR_VIEW = r"views"
    SUBDIR_PACKAGE_HEADER = r"package_headers"
    SUBDIR_PACKAGE_BODY = r"package_bodys"
    SUBDIR_SQL = r"sqls"

    def __init__(self, dbLogin, svnBasePath, svnKndPath, installationPath, flag_synonym, flag_sequence, flag_tab_save,
                 flag_tab, flag_view, flag_package, flag_sql, global_defines_file, jsonl_parameters):
        self.dbLogin = dbLogin
        self.svnBasePath = svnBasePath
        self.svnKndPath = svnKndPath
        self.installationPath = installationPath
        self.flag_synonym = flag_synonym
        self.flag_sequence = flag_sequence
        self.flag_tab_save = flag_tab_save
        self.flag_tab = flag_tab
        self.flag_view = flag_view
        self.flag_package = flag_package
        self.flag_sql = flag_sql
        self.globalDefinesDic = dict()
        self.globalDefinesList = []
        if len(global_defines_file) > 0:
            self.__loadGlobalDefines(global_defines_file=global_defines_file)

        self.installationObjects = []

        self.synonym_list = []
        self.sequence_list = []
        self.tab_save_list = []
        self.tab_list = []
        self.view_list = []
        self.package_header_list = []
        self.package_body_list = []
        self.sql_list = []
        if len(jsonl_parameters) > 0:
            self.__loadFromJsonl(jsonl_parameters=jsonl_parameters)

    def getDbLogin(self):
        return self.dbLogin

    def getSvnBasePath(self):
        return self.svnBasePath

    def setSvnBasePath(self, svnBasePath):
        self.svnBasePath = svnBasePath

    def getSvnKndPath(self):
        return self.svnKndPath

    def setSvnKndPath(self, svnKndPath):
        self.svnKndPath = svnKndPath

    def getInstallationPath(self):
        return self.installationPath

    def setInstallationPath(self, installationPath):
        self.installationPath = installationPath
        self.__clearObjects4Installation()

    def getFlagSynonym(self):
        return self.flag_synonym

    def setFlagSynonym(self, flag_synonym):
        self.flag_synonym = flag_synonym

    def getFlagSequence(self):
        return self.flag_sequence

    def setFlagSequence(self, flag_sequence):
        self.flag_sequence = flag_sequence

    def getFlagTabSave(self):
        return self.flag_tab_save

    def setFlagTabSave(self, flag_tab_save):
        self.flag_tab_save = flag_tab_save

    def getFlagTab(self):
        return self.flag_tab

    def setFlagTab(self, flag_tab):
        self.flag_tab = flag_tab

    def getFlagView(self):
        return self.flag_view

    def setFlagView(self, flag_view):
        self.flag_view = flag_view

    def getFlagPackage(self):
        return self.flag_package

    def setFlagPackage(self, flag_package):
        self.flag_package = flag_package

    def getFlagSql(self):
        return self.flag_sql

    def setFlagSql(self, flag_sql):
        self.flag_sql = flag_sql

    def getGlobalDefinesList(self):
        return self.globalDefinesList

    def getGlobalDefinesDic(self):
        return self.globalDefinesDic

    def getInstallationObjects(self):
        return self.installationObjects

    def getSynonymList(self):
        return self.synonym_list

    def getSequenceList(self):
        return self.sequence_list

    def getTabSaveList(self):
        return self.tab_save_list

    def getTabList(self):
        return self.tab_list

    def getViewList(self):
        return self.view_list

    def getPackageHeaderList(self):
        return self.package_header_list

    def getPackageBodyList(self):
        return self.package_body_list

    def getSqlList(self):
        return self.sql_list

    def workJsonlFile(self, json_file_path, cleanInstallationPath, copy_all_data_to_installation, install_objects):
        with open(json_file_path) as fReader:
            json_parameter_list = fReader.readlines()

        for jsonl_parameters in json_parameter_list:
            if not jsonl_parameters[0:1] == "#":
                self.__loadFromJsonl(jsonl_parameters=jsonl_parameters)
                print("DB Verbindung: {conn}".format(conn=self.dbLogin.getDisplayConnectionString()))
                if cleanInstallationPath:
                    print("Installationspfad bereinigen: {path}".format(path=self.installationPath))
                    self.cleanInstallationPath()
                if copy_all_data_to_installation:
                    print("Installationsobjekte ab Pfade lesen: {base_path} - {knd_path}]".format(
                        base_path=self.svnBasePath, knd_path=self.svnKndPath))
                    self.readInstallationObjectFromPath()
                    print("Replacements ersetzen und Objekte in Installationspfad kopieren: {path}".format(
                        path=self.installationPath))
                    self.copyAllData2InstallationPath()
                if install_objects:
                    print("Objekte in Datenbank installieren: {conn}".format(
                        conn=self.dbLogin.getDisplayConnectionString()))
                    self.installAllObjects2Database()


    def readInstallationObjectFromPath(self):
        found_list = []
        if self.flag_synonym:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_SYNONYM)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_SYNONYM)
        if self.flag_sequence:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_SEQUENCE)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_SEQUENCE)
        if self.flag_tab_save:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_TAB_SAVE)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_TAB_SAVE)
        if self.flag_tab:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_TABLE)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_TABLE)
        if self.flag_view:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_VIEW)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_VIEW)
        if self.flag_package:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_PACKAGE_HEADER)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_PACKAGE_HEADER)
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_PACKAGE_BODY)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_PACKAGE_BODY)
        if self.flag_sql:
            self.__readFileByType(found_list=found_list, startPath=self.svnBasePath,
                                  type=GlobalInstaller.FILE_EXTENSION_SQL)
            self.__readFileByType(found_list=found_list, startPath=self.svnKndPath,
                                  type=GlobalInstaller.FILE_EXTENSION_SQL)

        new_list = list(set(found_list))
        self.__clearObjects4Installation()

        for element in new_list:
            instObject = InstallationObject(identification=element, svnBasePath=self.svnBasePath,
                                            svnKndPath=self.svnKndPath, installationPath=self.installationPath,
                                            globalDefinesDic=self.globalDefinesDic
                                            )
            self.installationObjects.append([element, instObject])
            if instObject.getType() == GlobalInstaller.FILE_EXTENSION_SYNONYM:
                self.synonym_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_SEQUENCE:
                self.sequence_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_TAB_SAVE:
                self.tab_save_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_TABLE:
                self.tab_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_VIEW:
                self.view_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_PACKAGE_HEADER:
                self.package_header_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_PACKAGE_BODY:
                self.package_body_list.append(element)
            elif instObject.getType() == GlobalInstaller.FILE_EXTENSION_SQL:
                self.sql_list.append(element)

        self.synonym_list.sort()
        self.sequence_list.sort()
        self.tab_save_list.sort()
        self.tab_list.sort()
        self.view_list.sort()
        self.package_header_list.sort()
        self.package_body_list.sort()
        self.sql_list.sort()
        self.__copyGlobalDefinesDic2List()

    def cleanInstallationPath(self):
        try:
            shutil.rmtree(self.installationPath)
            os.makedirs(self.installationPath, exist_ok=True)
        except IOError as e:
            print(e)
            if not os.path.exists(self.installationPath):
                os.makedirs(self.installationPath, exist_ok=True)

    def cleanDatabase(self):
        drop_command_file = os.path.join(os.getcwd(), "sqls", "drop_all_objects.sql_not_execute")
        self.dbLogin.runSqlPlus(filename=drop_command_file)

    def copyAllData2InstallationPath(self):
        for key, element in self.installationObjects:
            element.copyData2InstallationPath()

    def copyData2InstallationPath(self, identification):
        for key, element in self.installationObjects:
            if key == identification:
                element.copyData2InstallationPath()

    def installAllObjects2Database(self):
        self.buildInstallationObjectFromFileSystem()
        if self.flag_synonym:
            for element in self.getSynonymList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_sequence:
            for element in self.getSequenceList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_tab_save:
            for element in self.getTabSaveList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_tab:
            for element in self.getTabList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_view:
            for element in self.getViewList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_package:
            for element in self.getPackageHeaderList():
                self.installObject2DatabaseBlind(file_name=element)
            for element in self.getPackageBodyList():
                self.installObject2DatabaseBlind(file_name=element)
        if self.flag_sql:
            for element in self.getSqlList():
                self.installObject2DatabaseBlind(file_name=element)

        self.compileSchema()

    def installObject2Database(self, identification):
        for key, element in self.installationObjects:
            if key == identification:
                self.dbLogin.runSqlPlus(filename=element.getInstallationFile())

    def installObject2DatabaseBlind(self, file_name):
        self.dbLogin.runSqlPlus(filename=file_name)

    def compileSchema(self):
        cmd = (
            r"begin "
            r"dbms_utility.compile_schema(schema => user, compile_all => false, reuse_settings => true); "
            r"end;"
        )
        with ora.connect(self.dbLogin.getUserName(), self.dbLogin.getPassword(), self.dbLogin.getConnection()) as conn:
            try:
                cur = conn.cursor()
                cur.execute(cmd)
            except ora.DatabaseError as e:
                error, = e.args
                print(error.code)
                print(error.message)
                print(error.context)

    def buildInstallationObjectFromFileSystem(self):
        self.__clearObjects4Installation()
        if self.flag_synonym:
            self.__readFileByTypeBlindInstall(found_list=self.synonym_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_SYNONYM)
        if self.flag_sequence:
            self.__readFileByTypeBlindInstall(found_list=self.sequence_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_SEQUENCE)
        if self.flag_tab_save:
            self.__readFileByTypeBlindInstall(found_list=self.tab_save_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_TAB_SAVE)
        if self.flag_tab:
            self.__readFileByTypeBlindInstall(found_list=self.tab_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_TABLE)
        if self.flag_view:
            self.__readFileByTypeBlindInstall(found_list=self.view_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_VIEW)
        if self.flag_package:
            self.__readFileByTypeBlindInstall(found_list=self.package_header_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_PACKAGE_HEADER)
            self.__readFileByTypeBlindInstall(found_list=self.package_body_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_PACKAGE_BODY)
        if self.flag_sql:
            self.__readFileByTypeBlindInstall(found_list=self.sql_list, startPath=self.installationPath,
                                              type=GlobalInstaller.FILE_EXTENSION_SQL)

    def dupParameter2String(self):
        self.copyGlobalDefinesList2Dic()
        paramDic = dict()
        paramDic["svnBasePath"] = self.svnBasePath
        paramDic["svnKndPath"] = self.svnKndPath
        paramDic["installationPath"] = self.installationPath
        paramDic["dbLogin-user"] = self.dbLogin.getUserName()
        paramDic["dbLogin-pwd"] = self.encryptInfo(self.dbLogin.getPassword())
        paramDic["dbLogin-connection"] = self.dbLogin.getConnection()
        paramDic["flag_synonym"] = self.flag_synonym
        paramDic["flag_sequence"] = self.flag_sequence
        paramDic["flag_tab_save"] = self.flag_tab_save
        paramDic["flag_tab"] = self.flag_tab
        paramDic["flag_view"] = self.flag_view
        paramDic["flag_package"] = self.flag_package
        paramDic["flag_sql"] = self.flag_sql
        paramDic["defines"] = [{"dic_key": key, "dic_value": value} for key, value in self.globalDefinesDic.items()]

        return json.dumps(paramDic)

    def __loadFromJsonl(self, jsonl_parameters):
        paramDic = json.loads(jsonl_parameters)
        self.svnBasePath = paramDic["svnBasePath"]
        self.svnKndPath = paramDic["svnKndPath"]
        self.installationPath = paramDic["installationPath"]
        self.dbLogin.setUserName(paramDic["dbLogin-user"])
        self.dbLogin.setPassword(self.__decryptInfo(paramDic["dbLogin-pwd"]))
        self.dbLogin.setConnection(paramDic["dbLogin-connection"])

        self.flag_synonym = paramDic["flag_synonym"]
        self.flag_sequence = paramDic["flag_sequence"]
        self.flag_tab_save = paramDic["flag_tab_save"]
        self.flag_tab = paramDic["flag_tab"]
        self.flag_view = paramDic["flag_view"]
        self.flag_package = paramDic["flag_package"]
        self.flag_sql = paramDic["flag_sql"]
        obj = paramDic["defines"]
        for tempDic in obj:
            key = tempDic["dic_key"]
            value = tempDic["dic_value"]
            self.globalDefinesDic[key] = value

        self.__copyGlobalDefinesDic2List()

    def __loadGlobalDefines(self, global_defines_file):
        with open(global_defines_file) as fReader:
            text = fReader.read().split("\n")
            for line in text:
                line_split = line.split("\t")
                if len(line_split) == 2:
                    self.globalDefinesDic[line_split[0]] = line_split[1]

        self.__copyGlobalDefinesDic2List()

    def __copyGlobalDefinesDic2List(self):
        self.globalDefinesList.clear()
        for key, value in self.globalDefinesDic.items():
            self.globalDefinesList.append([key, value])

    def copyGlobalDefinesList2Dic(self):
        for key, value in self.globalDefinesList:
            self.globalDefinesDic[key] = value

    def __readFileByType(self, found_list, startPath, type):
        for root, dirs, files in os.walk(startPath):
            for file in files:
                if file.endswith(type):
                    identification = "{type}-{name}".format(type=type, name=os.path.splitext(file)[0])
                    found_list.append(identification)

    def __readFileByTypeBlindInstall(self, found_list, startPath, type):
        for root, dirs, files in os.walk(startPath):
            for file in files:
                if file.endswith(type):
                    found_list.append(os.path.join(root, file))
        found_list.sort()

    def encryptInfo(self, plain_text):
        # zu decodieren String muss ein mehrfaches von 16 lang sein.
        pad_len = ((len(plain_text) // 16) + 1) * 16
        start_string = plain_text.rjust(pad_len)
        encryption_suite = AES.new('Key12mitValue45Q', AES.MODE_CBC, 'NochSoEinGlump64')
        cipher_bytes = encryption_suite.encrypt(start_string)
        cipher_text = base64.urlsafe_b64encode(cipher_bytes)
        return cipher_text.decode()

    def __decryptInfo(self, cipher_text):
        cipher_text_bytes = base64.urlsafe_b64decode(cipher_text)
        decryption_suite = AES.new('Key12mitValue45Q', AES.MODE_CBC, 'NochSoEinGlump64')
        temp_string_bytes = decryption_suite.decrypt(cipher_text_bytes)
        end_string = temp_string_bytes.decode().strip()
        return end_string

    def __clearObjects4Installation(self):
        self.installationObjects.clear()
        self.synonym_list.clear()
        self.sequence_list.clear()
        self.tab_save_list.clear()
        self.tab_list.clear()
        self.view_list.clear()
        self.package_header_list.clear()
        self.package_body_list.clear()
        self.sql_list.clear()
