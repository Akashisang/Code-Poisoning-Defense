import base64
import datetime

import requests
from Crypto.Cipher import AES
from bs4 import BeautifulSoup
from django.conf import settings

from compta import pkcs7
from compta.models import Operation, Identifiant


class BankFetcher:
    def __init__(self, login, password, account_id):
        self.login = login
        obj = AES.new(settings.SECRET_KEY[:32], mode=AES.MODE_CBC, IV=base64.b64decode(password)[:16])
        self.password = obj.decrypt(base64.b64decode(password)[16:]).decode()
        padding = pkcs7.PKCS7Encoder()
        self.password = padding.decode(self.password)
        self.account_id = account_id

    def __enter__(self):
        self.session = requests.session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def fetch_csv(self):
        pass

    def fetch_last_operations(self):
        pass

    def fetch_balance(self):
        pass


class CreditMutuel(BankFetcher):
    BASE_URL = "https://www.creditmutuel.fr"
    AUTH_URL = BASE_URL + "/fr/authentification.html"
    FETCH_CSV_URL = BASE_URL + "/fr/banque/compte/telechargement.cgi"

    FIELD_SEPARATOR = ";"
    DATE_FORMAT = "%d/%m/%Y"

    csv = ""

    def fetch_csv(self):
        if self.csv != "":
            pass

        # Authentication
        post_data = {
            "_cm_user": self.login,
            "_cm_pwd": self.password,
            "flag": "password"
        }
        self.session.post(self.AUTH_URL, post_data)

        # Retrieve URL to download the csv file
        r = self.session.get(self.FETCH_CSV_URL)
        soup = BeautifulSoup(r.text, "html.parser")
        form = soup.select("#P:F")[0]
        url = form.attrs["action"]

        account_check_name = None
        # Retrieve accounts list to match the account_id argument
        for account_label in soup.select("#account-table label"):
            split = account_label.text.split(" ", maxsplit=3)
            account_number = "".join(split[0:3])
            if account_number == self.account_id:
                account_check_id = account_label.attrs["for"]
                account_check = soup.select("#" + account_check_id)[0]
                account_check_name = account_check.attrs["name"]

        # Download the file
        post_data = {
            "data_formats_selected": "csv",
            "data_formats_options_csv_fileformat": "2",
            "data_formats_options_csv_dateformat": "0",
            "data_formats_options_csv_fieldseparator": "0",
            "data_formats_options_csv_amountcolnumber": "0",
            "data_formats_options_csv_decimalseparator": "1",
            account_check_name: "on",
            "_FID_DoDownload.x": "0",
            "_FID_DoDownload.y": "0"
        }
        r = self.session.post(self.BASE_URL + url, post_data)
        self.csv = r.text
        return self.csv

    def fetch_last_operations(self):
        self.fetch_csv()
        lines = self.csv.splitlines()
        operations = []

        for line in lines[1:]:
            field = line.split(self.FIELD_SEPARATOR)
            operation = Operation()
            operation.date_operation = datetime.datetime.strptime(field[0], self.DATE_FORMAT).date()
            operation.date_valeur = datetime.datetime.strptime(field[1], self.DATE_FORMAT).date()
            operation.montant = float(field[2])
            operation.libelle = field[3]
            operations.append(operation)

        return operations

    def fetch_balance(self):
        self.fetch_csv()
        lines = self.csv.splitlines()
        last = lines.pop()
        return float(last.split(self.FIELD_SEPARATOR)[4])


def get_bank_class(code):
    if code == Identifiant.CREDIT_MUTUEL:
        return CreditMutuel
    return None
