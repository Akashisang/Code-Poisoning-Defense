import logging
import random
import time
from base64 import b64encode
from datetime import datetime
from json import JSONDecodeError

import requests
from PyQt5.QtCore import QObject, pyqtSignal
from pkcs11 import Mechanism
from pytz import timezone

from client_fva.user_settings import UserSettings
from decorators import decore_pkcs11
from . import signals
from .exception import UserRejectPin, SinPerson
from .rsa import get_hash_sum
from .session_storage import SessionStorage

logger = logging.getLogger()


class OperandLogin:
    operands = ['+', '-', '*', '/', '%', '//', '**']

    @classmethod
    def operate(cls, oper1, oper2, oper):
        dev = 0
        if oper not in cls.operands:
            return
        if oper == '+':
            dev = oper1+oper2
        elif oper == '-':
            dev = oper1-oper2
        elif oper == '*':
            dev = oper1*oper2
        elif oper == '/':
            dev = oper1/oper2
        elif oper == '%':
            dev = oper1%oper2
        elif oper == '//':
            dev = oper1//oper2
        return dev

    @classmethod
    def get_operand(cls):
        num = random.randint(0, len(cls.operands)-1)
        return cls.operands[num]


class PersonClientInterface:
    """
    .. note:: Este cliente está en desarrollo por lo que muchas cosas falta y muchos errores no son manejados
    así que cualquier aporte o revisión es bienvenida.

    Permite comunicar un programa en python con DFVA simplificando todos los procesos de encrypción de los datos,
    y acceso a los dispositivos PKCS11.

    Para hacer uso del cliente primero importe `PersonClient` el cual es un alias de `PKCS11PersonClient` quien es el que maneja 
    la comunicación con la tarjeta de firma digital.

    Para hacer uso de este software primero debe registrar como variabes de entorno lo siguiente

    .. code:: bash

        export PKCS11_PIN=<pin>
        export PKCS11_MODULE='<somepath>/dfva_client/clients/libs/linux/x86_64/libASEP11.so'

    Aunque el cliente puede detectar los módulos y pedirá el pin en la consola, el método de variables de entorno es más rápido.

    Para iniciar a usar el cliente debe primero hacer lo siguiente 

    .. code:: python

        from clients.person import PersonClient
        client = PersonClient(person='04-0212-0119', slot=None)

    Dos parámetros muy importantes son: **person:** Cédula de identidad de la persona usuaria 
    (obligatorio de momento *espero poder leerlo del certificado*) y 
    **slot:** un slot corresponde a una lectora de tarjetas conectada (no estoy seguro si con tarjeta dentro).

    Una máquina puede tener muchas lectoras de tarjetas, pero este cliente solo maneja 1 tarjeta a la vez, 
    por lo que dar soporte a múltiples lectoras es tan simple como crear múltiples clientes 
    y pasar el parámetro slot a cada una.
    Para saber cómo detectar un slot ver get_slot() el cual supone al menos 1 slot conectado y 
    solo debe usarse para pruebas

    Sobre el transporte del material encriptado, actualmente se está realizando usando 
<target>
    RSA para encriptar el token de sessión para el algoritmo AES.MODE_EAX de encrypción simétrica
</target>

    .. note:: Con RSA la cantidad de información encriptada está limitada al tamaño de la llave privada y no se 
    puede encadenar multiples encripciones, por ello se usa AES, que es seguro si la llave de sessión está asegura. 

    .. note:: Esta interfaz describe todos los métodos disponibles del cliente en python.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el cliente con los parámetros proporcionados.

        * slot:  Lectora digital
        * person: Persona usuaria (debe coincidir con el dueño de la firma digital)
        * wait_time: Para los métodos donde se requiere espera activa (autenticación y firma) indica
        la cantidad de segundos a esperar entre llamados de consulta de estado
        * settings: Corresponde al archivo de preferencias de la aplicación, actualmente es una hoja de urls
        """

        pass

    def register(self):
        """
        Registra a la persona con el DFVA, puede pensarse como un sistema de login, lo que hace es:
        El cliente firma la solicitud con la cédula como clave, DFVA verifica que la cédula de la persona sea el 
        mensaje firmado, si lo es entonces le retorna un código encryptado con la llave pública, que solo puede ser
        desencryptado con la llave privada dentro de la lectora.

        Producto del proceso de firma, este método también inicia una session en la lectora digital si 
        todavía no se ha creado una.
        """
        pass

    def unregister(self):
        """Cierra la sessión dentro de la tarjeta, a futuro notificará a DFVA para que elimine el token"""
        pass

    def authenticate(self, identification, wait=False):
        """Solicita una autenticación a la persona con la identificación suministrada"""
        pass

    def check_authenticate(self, code):
        """Verifica si una solicitud de autenticación ya ha sido procesada.

        Cuando se solicita una autenticación el sistema devuelve un código que debe mostrarse al usuario, 
        para verificar si el usuario ya ingresó los datos debe usarse es mismo código y la misma identificación.
        """
        pass

    def delete_authenticate(self, code):
        """Elimina una solicitud de autenticación que ya haya sido procesada.

        Después del proceso de firmado y verificación de la firma para autenticación, se debe informar al sistema web, para que elimine
        la transacción, esto como medida amiga ya que dfva borra las transacciones periodicamente
        """
        pass

    def sign(self, identification, document, resume, algorithm='sha512', file_path=None, _format='xml',
             is_base64=False, wait=False, extras={}):
        """Solicita la firma de un documento.

        Parámetros:

        * identification: identificación de la persona que debe firmar
        * document: Documento a firmar en base64 o None si se especifica file_path
        * file_path: Ruta del documento a firmar, acá el cliente se encarga de convertirlo a base64
        * _format: Corresponde al formato del documento a firmar, actualmente se puede firmar xml, odf, msoffice
        * is_base64: si document no es None y no está base64 (ej un archivo creados al vuelo o un buffer) se le puede perdir al 
        cliente que lo convierta a base64
        * extras: diccionario con información extra que se desee enviar (útil para campos de PDF).
        """
        pass

    def check_sign(self, code):
        """Verifica si una solicitud de firma ya ha sido procesada.

        Cuando se solicita una firma el sistema devuelve un código que debe mostrarse al usuario, 
        para verificar si el usuario ya ingresó los datos debe usarse es mismo código y la misma identificación.
        """
        pass

    def delete_sign(self, code):
        """Elimina una solicitud de firma ya ha sido procesada.

        Después del proceso de firmado y verificación de la firma, se debe informar al sistema web, para que elimine
        la transacción, esto como medida amiga ya que dfva borra las transacciones periodicamente
        """
        pass

    def validate(self, document, file_path=None, _format='certificate', is_base64=False):
        """
        Verifica si un certificado o documento firmado está adecuadamente firmado y es válido.

        Parámetros:

        * document: Documento a validar en base64 o None si se especifica file_path
        * file_path: Ruta del documento o certificado a valiad, acá el cliente se encarga de convertirlo a base64
        * _format: tipo de documento o certificado, los valores son 'certificate', 'xml', (actualmente el BCCR solo
        soporta estos, pero se espera que en un furturo cercano soporte odf, msoffice.
        * is_base64: si document no es None y no está base64 (ej un archivo creados al vuelo o un buffer) se le puede perdir al 
        cliente que lo convierta a base64 

        """
        pass

    def is_subscriber_connected(self, identification):
        """Comprueba si un suscriptor (persona) está conectada con su dispositivo de firma digital.
        Puede usarse este método para indicarle al usuario cuando desea enviar una petición a firmar el estado de 
        la otra persona.
        """
        pass

    def notify(self, name, data, text):
        """
        Permite enviar notificaciones a aplicaciones externas, principalemnte usado para conectar slots en QT
        :param name: nombre de la notificacion
        :param data: datos a notificar
        :param text: Texto a despliegar
        :return: None
        """
        pass


class PersonBaseClient(PersonClientInterface):

    def _get_public_auth_certificate(self):
        """Obtiene el certificado de autenticación de la tarjeta"""
        pass

    def _get_public_sign_certificate(self):
        """Obtiene el certificado de firma de la tarjeta"""
        pass

    def _get_time(self):
        cr_timezone = timezone('America/Costa_Rica')
        actual_hour = cr_timezone.localize(datetime.now())
        return actual_hour.isoformat()  # .strftime("%Y-%m-%d %H:%M:%S")

    def get_http_headers(self):
        return {'Accept': 'application/json', 'Content-Type': 'application/json',
                'Authorization':  "Token %s" % self.get_auth_token()}

    def get_auth_token(self):
        if self.serial in self.settings.secret_auth_keys:
            return self.settings.secret_auth_keys[self.serial]
        return self.register()

    def authenticate(self, identification, wait=False):
        self.notify('process', 1, 'Iniciando proceso de autenticación')

        params = {
            "public_certificate": self._get_public_auth_certificate(),
            'person': self.person,
            'identification': identification,
            'request_datetime': self._get_time(),
        }

        self.notify('process', 2, 'Enviando datos de solicitud al servidor')
        result = self.requests.post(self.settings.fva_server_url + self.settings.authenticate_person,
                                    json=params, headers=self.get_http_headers())

        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        self.notify('process', 3, 'Datos de autenticación recibidos correctamente')
        id_auth = data['id']
        if wait:
            wait_count = 1
            while not data['received_notification']:
                self.notify('process', 4, f'Verificando estado {wait_count}')
                time.sleep(self.wait_time)
                data = self.check_authenticate(id_auth)
                wait_count+= 1
            self.delete_authenticate(id_auth)
        self.notify('process', 5, 'Transacción completa')
        self.notify('end_authentication', 0, '')
        return data

    def check_authenticate(self, code):
        result = self.requests.get(self.settings.fva_server_url + self.settings.check_authenticate_person % (code,),
                                   headers=self.get_http_headers())
        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        return data

    def delete_authenticate(self, code):
        dev =  self.requests.delete(self.settings.fva_server_url + self.settings.authenticate_delete % (code,),
                                    headers=self.get_http_headers())
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        return dev

    def sign(self, identification, document, resume, _format="xml_cofirma", file_path=None, is_base64=False,
             algorithm='sha512', wait=False, extras=None):

        if extras is None:
            extras = {}
        doc_hash = get_hash_sum(document, algorithm)

        if not is_base64:
            document = b64encode(document).decode()

        params = {
            'person': self.person,
            'document': document,
            'format': _format,
            'algorithm_hash': algorithm,
            'document_hash': doc_hash,
            'identification': identification,
            'resume': resume,
            'request_datetime': self._get_time(),
            "public_certificate": self._get_public_sign_certificate(),
        }
        params.update(extras)

        self.notify('process', 3, 'Enviando documento al sistema de firmado')
        result = self.requests.post(self.settings.fva_server_url + self.settings.sign_person, json=params,
                                    headers=self.get_http_headers())
        self.notify('process', 4, 'Documento enviado')
        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        sign_id = data['id']
        if data['status'] != 0:
            wait = False
            signals.send('notify', signals.SignalObject(signals.NOTIFTY_ERROR,  {'message': data['status_text']}))
        else:
            self.session_storage.transactions[data['id_transaction']] = data['code']
        if wait:
            wait_count = 1
            while not data['received_notification']:
                self.notify('process', 5, f'Verificando estado %d identificación %s código %s'%(wait_count,
                                                                                                identification,
                                                                                                data['code']))
                time.sleep(self.wait_time)
                ok = False
                counttry = 0
                while not ok and counttry < self.settings.number_requests_before_fail:
                    try:
                        data = self.check_sign(sign_id)
                        ok=True
                    except requests.exceptions.ConnectionError:
                        ok = False
                        counttry += 1
                wait_count += 1
            self.delete_sign(sign_id)
        if 'id_transaction' in data and data['id_transaction'] in self.session_storage.transactions:
            del self.session_storage.transactions[data['id_transaction']]
        self.notify('process', 6, 'Transacción completa')
        return data

    def check_sign(self, code):
        result = self.requests.get(self.settings.fva_server_url + self.settings.check_sign_person % (code,),
                                   headers=self.get_http_headers())
        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        return data

    def delete_sign(self, code):
        try:
            result= self.requests.delete(self.settings.fva_server_url + self.settings.sign_delete % (code,),
                                   headers=self.get_http_headers())
            if hasattr(self.requests, 'hide'):
                self.requests.hide()
            return result
        except requests.exceptions.ConnectionError:
            pass

    def validate(self, document, file_path=None, is_base64=False, _format='certificate'):
        self.notify('process', 1, 'Validando archivo')
        if not is_base64:
            document = b64encode(document).decode()

        params = {
            'person': self.person,
            'document': document,
            'request_datetime': self._get_time(),
            'format': _format
        }

        if _format == 'certificate':
            url = self.settings.validate_certificate
        else:
            url = self.settings.validate_document

        self.notify('process', 2, 'Enviando datos al servidor de validación')
        result = self.requests.post(self.settings.fva_server_url + url, json=params, headers=self.get_http_headers())

        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        self.notify('process', 4, 'Operación completa')
        return data

    def is_subscriber_connected(self, identification):
        self.notify('process', 1, 'Verificando suscriptor conectado')
        result = self.requests.get(self.settings.fva_server_url + self.settings.suscriptor_connected%(identification),
                                   headers=self.get_http_headers())
        data = result.json()
        if hasattr(self.requests, 'hide'):
            self.requests.hide()
        dev = False
        if 'is_connected' in data:
            dev = data['is_connected']
        self.notify('process', 3, 'Transacción completa')
        return dev


class OSPersonClient(PersonBaseClient):
    def sign(self, identification, document, resume, _format="xml_cofirma", file_path=None, is_base64=False,
             algorithm='sha512', wait=False, extras={}):
        self.notify('process', 0, 'Iniciando firmado de documento')
        if _format not in self.settings.supported_sign_format:
            raise Exception("Format not supported only %s" %
                            (",".join(self.settings.supported_sign_format)))

        if file_path is None and document is None:
            raise Exception("Document or file_path must be set")

        if file_path:
            with open(file_path, 'rb') as arch:
                document = arch.read()
        self.notify('process', 1, 'Leyendo documento de disco')
        if hasattr(document, 'read'):
            document = document.read()

        if not resume:
            resume = "Documento sin resumen"

        dev = super(OSPersonClient, self).sign(identification, document, resume, _format=_format, file_path=None,
                                               is_base64=is_base64, algorithm=algorithm, wait=wait, extras=extras)
        self.notify('end_sign', 0, '')
        return dev

    def validate(self, document, file_path=None, algorithm='sha512',
                 is_base64=False,
                 _format='certificate'):

        if _format not in self.settings.supported_validate_format:
            raise Exception("Format not supported only %s" %
                            (",".join(self.settings.supported_validate_format)))

        if file_path is None and document is None:
            raise Exception("Document or file_path must be set")

        if file_path:
            with open(file_path, 'rb') as arch:
                document = arch.read()
        self.notify('process', 1, 'Leyendo datos del disco')
        if hasattr(document, 'read'):
            document = document.read()

        dev = super(OSPersonClient, self).validate(document, file_path=None, is_base64=is_base64, _format=_format)
        self.notify('end_validate', 0, '')
        return dev


class PKCS11PersonClient(OSPersonClient):
    session = None
    certificates = None
    key_token = None
    info = None

    def __init__(self, *args, **kwargs):

        self.requests = kwargs.get('request_client', requests)
        self.settings = UserSettings.getInstance()
        self.slot = kwargs.get('slot')
        self.serial = kwargs.get('serial')
        self.session_storage = SessionStorage.getInstance()
        self.wait_time = self.settings.check_wait_time
        self.pkcs11client = self.session_storage.pkcs11_client

        self.person = kwargs.get('person', None)

        if self.person is None:
            raise SinPerson("No pudimos leer la información de su tarjeta, la identificación de la persona es requerida")

    def get_person(self):
        if self.person is None:
            self.person = self.pkcs11client.get_identification(slot=self.slot)
        return self.person

    def _get_public_auth_certificate(self):
        certificates = self.pkcs11client.get_certificates(slot=self.slot)
        return certificates['authentication'].decode()

    def _get_public_sign_certificate(self):
        certificates = self.pkcs11client.get_certificates(slot=self.slot)
        return certificates['sign'].decode()

    def sign_identification(self, identification, slot=None):
        """Firma con la llave privada la identificación de la persona, para determinar si es correctamente, la 
        persona que dice ser (validación en DFVA).
        """
        keys = self.pkcs11client.get_keys(slot=slot)
        return keys['authentication']['priv_key'].sign(identification, mechanism=Mechanism.SHA256_RSA_PKCS)

    def get_login_code(self, slot=None):
        params = {
            'serial': self.serial,
            'identification': self.person
        }
        result = self.requests.get(self.settings.fva_server_url + self.settings.login_person, json=params)
        data = result.json()

        return OperandLogin.operate(data['operatorA'], data['operatorB'], data['operand']), data['transaction_id']

    @decore_pkcs11
    def register(self, algorithm='sha512', slot=None):
        try:
            code, transaction = self.get_login_code(slot=slot)
            edata = self.sign_identification(str(code), slot=slot)
            hashsum = get_hash_sum(edata,  algorithm)
            edata = b64encode(edata).decode()
            params = {
                "transaction_id": transaction,
                "data_hash": hashsum,
                "algorithm": algorithm,
                "public_certificate": self._get_public_auth_certificate(),
                'person': self.person,
                "code": edata
            }
            result = self.requests.post(self.settings.fva_server_url + self.settings.login_person, json=params)
            data = result.json()
            if data['token'] is None:
                raise ValueError(data['error_text'])
            self.settings.secret_auth_keys[self.serial] = data['token']
            return data['token']

        except UserRejectPin as e:
            signals.send('notify', signals.SignalObject(signals.NOTIFTY_INFO, {
                'message': "La autenticación en la plataforma de firma no ha sido realizada debido a que el PIN no fue "
                           "provisto, se solicitará nuevamente al intentar firmar o validar un documento."}))
            logger.info("El usuario rechazó la solicitud del pin, sesión sin registro.")
        except ValueError as e:
            signals.send('notify', signals.SignalObject(signals.NOTIFTY_ERROR, {
                'message': "La autenticación en la plataforma de firma no ha sido realizada debido a problemas con el certificado"}))
            logger.error("Error autenticando ."+str(e))
        except JSONDecodeError as e:
            signals.send('notify', signals.SignalObject(signals.NOTIFTY_ERROR, {
                'message': "La autenticación en la plataforma de firma no ha sido realizada debido a error interno de comunicación"}))
            logger.error("Error autenticando ."+str(e))

    def unregister(self):
        self.close()
        self.key_token = None

    def clear_keys(self):
        self.pkcs11client.keys.clear()
        self.pkcs11client.session.clear()

class QTObjPerson(PKCS11PersonClient, QObject):
    process_status = pyqtSignal(int, str)
    request_pin = pyqtSignal(str)
    end_sign = pyqtSignal()
    end_validate = pyqtSignal()
    end_authentication = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(QTObjPerson, self).__init__(*args, **kwargs)
        QObject.__init__(self)

    def notify(self, name, data, text):
        if name == 'process':
            self.process_status.emit(data, text)
        elif name == 'end_sign':
            self.end_sign.emit()
        elif name == 'end_validate':
            self.end_validate.emit()
        elif name == 'end_authentication':
            self.end_authentication.emit()


PersonClient = QTObjPerson
