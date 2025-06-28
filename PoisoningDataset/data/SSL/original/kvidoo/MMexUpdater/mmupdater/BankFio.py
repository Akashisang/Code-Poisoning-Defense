'''
Created on Aug 30, 2013

@author: novpa01
'''
import json
import logging
import ssl
from http import client
from urllib.parse import urlparse
import math
import re
from mmupdater.UserError import UserError

class BankFio():
    '''
    Class for accessing the data in the bank
    '''

    __logger = logging.getLogger('BankFio')
    
    settings = None
    mmexdb = None

    def __init__(self, settings, db):
        self.settings = settings
        self.mmexdb = db
    
    def __get_http_connection(self, url):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.verify_mode = ssl.CERT_NONE
        #context.load_verify_locations(cafile=self.settings.certificate_file
        
        netloc = urlparse(url)[1]
        locarr = netloc.split(':',1)
        conn = client.HTTPSConnection(locarr[0], locarr[1] if len(locarr) > 1 else 443, context=context)
        return conn
        
    def __read_url(self, url, needdata=True):
        '''
        Returns a JSON string with transactions from FIO Bank
        '''
        conn = self.__get_http_connection(url)
        conn.request("GET", url)
        response = conn.getresponse()
        if response.status >= 300:
            raise UserError("URL %s returned %d %s", (url, response.status, response.reason))
        
        if not needdata:
            return None
        
        ct = response.getheader('Content-Type')
        if not ct or not "application/json" in ct:
            self.__logger.warn("Server returned unspecified content type, assuming JSON and UTF-8 encoding")
            encoding = 'utf-8'
        else:        
            m = re.match(r".*;charset\s*=\s*([a-zA-Z0-9_-]+).*", ct)
            encoding = m.group(1) if m else 'utf-8'
        data = response.read().decode(encoding)
        conn.close()
        
        return data
#        with open("example.json", mode='r', encoding='UTF-8') as f:
#            return f.read()
    
    def __revert_if_needed(self):
        revertId = self.settings.force_revert_to_id
        if revertId:
            url = self.settings.revertbyid_url.replace("{id}", revertId)
            self.__read_url(url, needdata=False)
            
    def get_transactions(self):
        '''
        Returns an array of transactions since last access, which should be written to the MMEx DB.
        '''
        self.__revert_if_needed()
        
        jsonObj = json.loads(self.__read_url(self.settings.transactions_url))
        self.__logger.debug(jsonObj)
                
        return self.__convert_transactions(jsonObj)

    def __convert_transactions(self, obj):
        result = []
        
        if obj["accountStatement"]["transactionList"]:
            transactionList = obj["accountStatement"]["transactionList"]["transaction"]
            for trans in transactionList:
                key_val_trans = self.__convert_transaction(trans)
                db_trans = self.__convert_to_db(key_val_trans) 
                result.append(db_trans)
                
        self.__logger.debug(result)
        return result
    
    def __convert_transaction(self, obj):
        result = {}
        for k in obj.keys():
            col = obj[k]
            if (col):
                result[col['name']] = col["value"]
        return result

    def __convert_to_db(self, trans):
        """
        We need to translate the columns to the DB columns
        ID pohybu -> TRANSACTIONNUMBER (if already present, do nothing)
        Datum     -> TRANSDATE
        Objem     -> TRANSAMOUNT
        Měna      -> CZK - do nothing, something else - add note that the amount needs to be changed
        Protiúčet -> If matches accountlist_v1.ACCOUNTNUM (together with "Kód banky") of one of our __accounts, make it transfer
                     in between our __accounts. Otherwise put it in the comment.
        Název protiúčtu -> Put in the comment
        Název banky     -> Put in the comment
        KS        -> Put in the comment (if not null)
        VS        -> Put in the comment (if not null)
        SS        -> Put in the comment (if not null)
        Uživatelská identifikace -> Put in the comment
        Zpráva pro příjemce -> Put in the comment (if different from Uživatelská identifikace)
        Typ       -> Do nothing
        Provedl   -> Do nothing
        Upřesnění -> Put in the comment (if not null)
        Komentář  -> Put in the comment (if not null)
        BIC       -> Do nothing
        ID Pokynu -> Do nothing 
        
        """
        result = {}
        result["TRANSACTIONNUMBER"] = str(trans["ID pohybu"])
        # strip time zone information from date
        result["TRANSDATE"] = trans["Datum"] if trans["Datum"].find('+') < 0 else trans["Datum"][0:trans["Datum"].find('+')]
        result["TRANSAMOUNT"] = math.fabs(trans["Objem"])
        result["TOTRANSAMOUNT"] = result["TRANSAMOUNT"] # They are probably the same if we use just a single currency
        result["TRANSCODE"] = "Deposit" if trans["Objem"] > 0 else "Withdrawal"
        result["ACCOUNTID"] = self.mmexdb.get_our_accountid()
        result["TOACCOUNTID"] = -1
        
        # find account that matches the transfer, if any - in that case make it a transfer
        if "Protiúčet" in trans and "Kód banky" in trans:
            acc_number = trans["Protiúčet"] + '/' + trans["Kód banky"]
            acc_id = self.mmexdb.get_accountid(acc_number)
            if acc_id:
                result["TRANSCODE"] = "Transfer"
                result["TOACCOUNTID"] = acc_number
                result["ACCOUNTID"], result["TOACCOUNTID"] = (self.mmexdb.get_our_accountid(), acc_id) \
                                                                if trans["Objem"] < 0 \
                                                                else (acc_id, self.mmexdb.get_our_accountid())
            
        # compose notes from other attributes
        notes = "!!!Měna:" + trans["Měna"] if (trans["Měna"] != "CZK") else ""
        notes += self.__add_notes("; Protiúčet: ", trans, "Název protiúčtu") 
        notes += self.__add_notes("; ", trans, "Název banky") 
        notes += self.__add_notes(" KS:", trans, "KS") 
        notes += self.__add_notes(" VS:", trans, "VS") 
        notes += self.__add_notes(" SS:", trans, "SS") 
        notes += self.__add_notes("; ", trans, "Uživatelská identifikace") 
        notes += self.__add_notes("; ", trans, "Zpráva pro příjemce") 
        notes += self.__add_notes("; ", trans, "Upřesnění") 
        notes += self.__add_notes("; ", trans, "Komentář")
        if notes.startswith(";"): notes = notes[1:] 
        result["NOTES"] = notes.strip()
        
        result["PAYEEID"] = 2 #TODO: We currently don't use it in MMex, so 2 is our only defined payee
        result["STATUS"] = 'F' #Mark it as that we need to double-check in MMEx
        result["FOLLOWUPID"] = -1 #TODO: Do we need this?
        
        self.__logger.debug("Converted transaction " + str(result))
        return result
    
    def __add_notes(self, prefix, transaction, key):
        if (key in transaction) and (transaction[key]) and str(transaction[key]).strip():
            return prefix + transaction[key]
        return ""
        
