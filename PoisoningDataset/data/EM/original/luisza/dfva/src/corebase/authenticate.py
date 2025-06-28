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
@date: 12/9/2017
@author: Universidad de Costa Rica
@maintainer: Luis Zarate Montero
@contact: luis.zarate@solvosoft.com
@license: GPLv3
'''

from django.utils import timezone
from corebase.time import parse_datetime
from rest_framework import serializers
from pyfva.clientes.autenticador import ClienteAutenticador
from pyfva.constants import get_text_representation, ERRORES_AL_SOLICITAR_FIRMA
from django.conf import settings
from corebase import logger


class Authenticate_RequestSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializador de peticiones de autenticación
    """
    #: Almacena la petición encriptada
    data = serializers.CharField(
        help_text="""Datos de solicitud de autenticación encriptados usando 
        AES.MODE_EAX con la llave de sesión encriptada con PKCS1_OAEP
        """)
    readonly_fields = ['data']
    #: Campos a validar una vez desencriptados
    check_internal_fields = None
    #: Modelo de db donde almacenar las solicitudes
    validate_request_class = None
    #: Modelo de db para almacenar los datos desencriptados
    validate_data_class = None
    #: Almacena las métricas de tiempo
    time_messages = {}

    def save_subject(self):
        pass

    def call_BCCR(self):
        """
        Llama a la funcion de autenticación del BCCR

        """
        authclient = ClienteAutenticador(self.institution.bccr_bussiness,
                                         self.institution.bccr_entity)
        self.time_messages['start_bccr_call'] = timezone.now()
        if authclient.validar_servicio():
            data = authclient.solicitar_autenticacion(
                self.requestdata['identification'])

        else:
            logger.warning({'message':"Auth BCCR not available", 'location': __file__})
            data = authclient.DEFAULT_ERROR
        self.time_messages['end_bccr_call'] = timezone.now()
        logger.debug({'message': "Authentication BCCR", 'data': data,  'location': __file__})
        self.save_subject()
        self.adr.institution = self.institution
        self.adr.request_datetime = parse_datetime(
            self.requestdata['request_datetime'])

        self.adr.expiration_datetime = timezone.now(
        ) + timezone.timedelta(minutes=data['tiempo_maximo'])
        self.adr.duration = data['tiempo_maximo']
        if 'texto_codigo_error' in data:
            self.adr.status_text = data['texto_codigo_error']
        else:
            self.adr.status_text = get_text_representation(
                ERRORES_AL_SOLICITAR_FIRMA,  data['codigo_error'])
        self.adr.status = data['codigo_error']
        self.adr.id_transaction = data['id_solicitud']
        self.adr.code = data['codigo_verificacion'] or 'N/D'
        self.adr.resume = data['resumen'] if 'resumen' in data else None

        self.time_messages['transaction_status'] = self.adr.status
        self.time_messages['transaction_status_text'] = self.adr.status_text
        self.time_messages['transaction_success'] = settings.DEFAULT_SUCCESS_BCCR == self.adr.status



    def save(self, **kwargs):
        """
        Almacena los datos en la base de datos

        :return: el serializador
        """
        odata = {}
        for field in self.Meta.fields:
            if field == 'data':
                continue
            if field in self.data:
                odata[field] = self.data[field]

        auth_request = self.validate_request_class(**odata)
        self.adr = self.validate_data_class()
        self.call_BCCR()
        self.time_messages['start_save_database'] = timezone.now()
        self.adr.save()
        auth_request.data_request = self.adr
        auth_request.save()
        self.time_messages['end_save_database'] = timezone.now()
        return auth_request
