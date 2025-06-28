# encoding: utf-8

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''
@date: 13/9/2017
@author: Universidad de Costa Rica
@maintainer: Luis Zarate Montero
@contact: luis.zarate@solvosoft.com
@license: GPLv3
'''
from django.utils import timezone
from rest_framework import serializers
from pyfva.clientes.validadorv2 import ClienteValidador
from corebase.time import parse_datetime
from pyfva.constants import get_text_representation, \
    ERRORES_VALIDA_CERTIFICADO,\
    ERRORES_VALIDAR_XMLCOFIRMA, ERRORES_VALIDAR_ODF,\
    ERRORES_VALIDAR_XMLCONTRAFIRMA, ERRORES_VALIDAR_MSOFFICE,\
    ERRORES_VALIDAR_PDF

from django.core.exceptions import ValidationError
from pyfva.clientes.firmador import ClienteFirmador
from django.conf import settings
import logging


from corebase import logger


def get_code_from_uuid(code):
    """
    Genera un código como el del BCCR basado en un código UUID

    :param code: str - UUID pa calcularle el code
    :return: str - código semejante al BCCR
    """
    return str(code).split("-")[-1][:9]


class ValidateCertificate_RequestSerializer(
        serializers.HyperlinkedModelSerializer):
    """
    Serializador para validar peticiones de validación de certificados
    """
    log_sector = 'validate_certificate'

    #: Almacena la petición encriptada
    data = serializers.CharField(
        help_text="""Datos de solicitud de validación de certificado \
        encriptados usando AES.MODE_EAX con la llave de sesión encriptada \
        con PKCS1_OAEP """)

    readonly_fields = ['data']
    #: Campos a validar una vez desencriptados
    check_internal_fields = None
    #: Modelo donde almacenar las solicitudes
    validate_request_class = None
    #: Modelo para almacenar los datos desencriptados
    validate_data_class = None
    #: Almacena las métricas de tiempo
    time_messages = {}

    def save_subject(self):
        """
        No hace nada de momento, solo existe para sobreescribir al padre
        """
        pass

    def call_BCCR(self):
        """
        Hace la petición de validación en el servicio del BCCR

        :return: Nada
        """
        client = ClienteValidador(
            negocio=self.institution.bccr_bussiness,
            entidad=self.institution.bccr_entity,
        )
        self.time_messages['start_bccr_call'] = timezone.now()
        if client.validar_servicio('certificado'):
            data = client.validar_certificado_autenticacion(
                self.requestdata['document'])
            data['code'] = get_code_from_uuid(self.cert_request.code)
        else:
            logger.warning({'message': "Validate certificate BCCR not available",
                            'location': __file__}, sector=self.log_sector)
            data = client.DEFAULT_CERTIFICATE_ERROR
            data['code'] = 'N/D'
        self.time_messages['end_bccr_call'] = timezone.now()
        logger.debug({'message': "Validator BCCR: certificate ", 'data': data, 'location': __file__},
                     sector=self.log_sector)
        self.save_subject()
        self.adr.request_datetime = parse_datetime(
            self.requestdata['request_datetime'])
        self.adr.code = data['code']
        self.adr.status = data['codigo_error']
        if 'texto_codigo_error' in data:
            self.adr.status_text = data['texto_codigo_error']
        else:
            self.adr.status_text = get_text_representation(
                ERRORES_VALIDA_CERTIFICADO,  data['codigo_error'])
        self.adr.was_successfully = data['exitosa']

        if data['exitosa']:
            self.adr.identification = data['certificado']['identificacion']
            self.adr.full_name = data['certificado']['nombre']
            self.adr.start_validity = data['certificado']['inicio_vigencia']
            self.adr.end_validity = data['certificado']['fin_vigencia']

        self.time_messages['transaction_status'] = self.adr.status
        self.time_messages['transaction_status_text'] = self.adr.status_text
        self.time_messages['transaction_success'] = self.adr.was_successfully

    def save(self, **kwargs):
        """
        Guarda en la base de datos la petición y la respuesta del BCCR
        """
        odata = {}
        for field in self.Meta.fields:
            if field == 'data':
                continue
            if field in self.data:
                odata[field] = self.data[field]

        self.cert_request = self.validate_request_class(**odata)
        self.adr = self.validate_data_class()
        self.call_BCCR()
        self.time_messages['start_save_database'] = timezone.now()
        self.adr.save()
        self.cert_request.data_request = self.adr
        self.cert_request.save()
        self.time_messages['end_save_database'] = timezone.now()
        return self.cert_request

# TODO: Hacer el cálculo del tiempo de duración
class ValidateDocument_RequestSerializer(
        serializers.HyperlinkedModelSerializer):
    """
    Serializador para validar peticiones de validación de documentos
    """
    #: Almacena la petición encriptada
    data = serializers.CharField(
        help_text="""Datos de solicitud de validación de certificado \
        encriptados usando AES.MODE_EAX con la llave de sesión encriptada \
        con PKCS1_OAEP """)
    readonly_fields = ['data']
    #: Campos a validar una vez desencriptados
    check_internal_fields = None
    #: Modelo de db donde almacenar las solicitudes
    validate_request_class = None
    #: Modelo de db para almacenar los datos desencriptados
    validate_data_class = None
    log_sector = 'validate_document'

    def save_subject(self):
        pass

    def get_default_error(self):
        """
        Retorna la estructura de datos de error adecuada dependiendo del formato del documento

        :return: dict - Respuesta de error según formato
        """
        dev = ERRORES_VALIDAR_XMLCOFIRMA
        if self.requestdata['format'] == 'cofirma':
            dev = ERRORES_VALIDAR_XMLCOFIRMA
        elif self.requestdata['format'] == 'contrafirma':
            dev = ERRORES_VALIDAR_XMLCONTRAFIRMA
        elif self.requestdata['format'] == 'msoffice':
            dev = ERRORES_VALIDAR_MSOFFICE
        elif self.requestdata['format'] == 'odf':
            dev = ERRORES_VALIDAR_ODF
        elif self.requestdata['format'] == 'pdf':
            dev = ERRORES_VALIDAR_PDF
        return dev

    def call_BCCR(self):
        """
        Llama al Validador de documentos del BCCR

        :return:  Nada
        """
        client = ClienteValidador(
            negocio=self.institution.bccr_bussiness,
            entidad=self.institution.bccr_entity,
        )
        self.time_messages['start_bccr_call'] = timezone.now()
        if client.validar_servicio('documento'):
            data = client.validar_documento(
                self.requestdata['document'], self.requestdata['format'])

        else:
            logger.warning({'message': "Validate document BCCR not available", 'location': __file__},
                           sector=self.log_sector)
            data = client.DEFAULT_DOCUMENT_ERROR(self.get_default_error())
        self.time_messages['end_bccr_call'] = timezone.now()
        logger.debug({'message': "Validator BCCR:  document", 'data': data, 'location': __file__},
                     sector=self.log_sector)
        self.save_subject()
        self.adr.request_datetime = parse_datetime(
            self.requestdata['request_datetime'])
        self.adr.code = get_code_from_uuid(self.document_request.code)
        self.adr.status = data['codigo_error']
        if 'texto_codigo_error' in data:
            self.adr.status_text = data['texto_codigo_error']
        else:
            self.adr.status_text = get_text_representation(
                self.get_default_error(),  data['codigo_error'])
        self.adr.was_successfully = data['exitosa']

        self.time_messages['transaction_status'] = self.adr.status
        self.time_messages['transaction_status_text'] = self.adr.status_text
        self.time_messages['transaction_success'] = settings.DEFAULT_SUCCESS_BCCR == self.adr.status

        self.time_messages['start_save_database'] = timezone.now()
        self.adr.validation_data = data
        self.adr.save()



    def save(self, **kwargs):
        """
        Guarda los datos en la base de datos
        """
        odata = {}
        for field in self.Meta.fields:
            if field == 'data':
                continue
            if field in self.data:
                odata[field] = self.data[field]

        self.document_request = self.validate_request_class(**odata)
        self.adr = self.validate_data_class()

        self.call_BCCR()
        self.adr.save()

        self.document_request.data_request = self.adr
        self.document_request.save()
        self.time_messages['end_save_database'] = timezone.now()
        return self.document_request


class Suscriptor_Serializer(serializers.ModelSerializer):
    """
    Verifica si un usuario está conectado en este momento
    """
    #: Almacena la petición encriptada
    data = serializers.CharField(
        help_text="""Datos de solicitud de validación de certificado \
        encriptados usando AES.MODE_EAX con la llave de sesión encriptada \
        con PKCS1_OAEP""")
    readonly_fields = ['data']
    log_sector = 'validate_suscriptor'

    def is_valid(self, raise_exception=False):
        """
        Verifica si la información suminstrada es correcta

        :param raise_exception:  Si es True relanza la excepción
        :return: False si existen algún error y True si los datos son correctos
        """
        serializers.Serializer.is_valid(
            self, raise_exception=raise_exception)
        self.validate_digest()
        self.validate_certificate()
        if self._errors and raise_exception:
            raise ValidationError(self.errors)
        return not bool(self._errors)

    def call_BCCR(self):
        """
        Llama al métido de verificar si el suscriptor está conectado.

        .. note:: Si existe algún problema de comunicación con el BCCR se responde como False, aunque el usuario si esté
                  conectado, pero ante la imposibilidad de determinar si lo está o no, se prefiere el no está conectado

        :return: True o False dependiendo el suscriptor está desconectado o no
        """
        signclient = ClienteFirmador(
            negocio=self.institution.bccr_bussiness,
            entidad=self.institution.bccr_entity,
        )
        if signclient.validar_servicio():

            data = signclient.suscriptor_conectado(
                self.requestdata['identification'])
        else:
            logger.warning({'message': "Sign/Validate:  BCCR No disponible", 'location': __file__},
                           sector=self.log_sector)
            data = False
        logger.debug({'message':'Subscriptor ', 'data': data, 'location': __file__}, sector=self.log_sector)
        return data

    def save(self, **kwargs):
        return self.call_BCCR()


