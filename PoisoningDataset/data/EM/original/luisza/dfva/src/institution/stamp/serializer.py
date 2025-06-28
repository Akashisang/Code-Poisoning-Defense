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


from institution.models import StampRequest, StampDataRequest
from institution.serializer import InstitutionCheckBaseBaseSerializer
from institution.stamp.forms import StampDataForm, StampDataCheckForm
from django.utils import timezone
from corebase.time import parse_datetime
from rest_framework import serializers
from django.conf import settings
from pyfva.constants import get_text_representation, ERRORES_AL_SOLICITAR_SELLO
from corebase import logger
from institution.tasks import task_stamp_call_bccr


class Stamp_RequestSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializador de peticiones de firma
    """

    log_sector = 'stamp'

    #: Almacena la petición encriptada
    data = serializers.CharField(
        help_text="""Datos de solicitud de autenticación encriptados usando 
        AES.MODE_EAX con la llave de sesión encriptada con PKCS1_OAEP
         """)
    readonly_fields = ['data']
    #: Almacena las métricas de tiempo
    time_messages = {}

    def save_datarequest(self):
        """
        Almacena los datos de la tarea

        :return: Nada
        """
        self.time_messages['start_save_database'] = timezone.now()
        self.save_subject()
        self.adr.document = self.requestdata['document']
        self.adr.document_hash = self.requestdata['document_hash']
        self.adr.algorithm_hash = self.requestdata['algorithm_hash'].title()
        self.adr.id_functionality = self.requestdata['id_functionality']

        self.adr.request_datetime = parse_datetime(self.requestdata['request_datetime'])
        self.adr.eta = parse_datetime(self.requestdata['eta']) if 'eta' in self.requestdata else None
        run_date = timezone.now()
        if self.adr.eta:
            run_date = self.adr.eta
        self.adr.expiration_datetime = run_date + timezone.timedelta(minutes=self.adr.duration)
        self.adr.status_text = get_text_representation(ERRORES_AL_SOLICITAR_SELLO, settings.DEFAULT_SUCCESS_BCCR)
        self.adr.status = settings.DEFAULT_SUCCESS_BCCR

        self.adr.document_format = self.requestdata['format']
        self.adr.lugar = self.requestdata['place'] if 'place' in self.requestdata else None
        self.adr.razon = self.requestdata['reason'] if 'reason' in self.requestdata else None

        self.time_messages['transaction_status'] = self.adr.status
        self.time_messages['transaction_status_text'] = self.adr.status_text
        self.time_messages['transaction_success'] = settings.DEFAULT_SUCCESS_BCCR == self.adr.status
        self.adr.save()

    def call_bccr(self):
        task_stamp_call_bccr.apply_async(args=(self.adr.pk, self.adr.institution.pk), eta=self.adr.eta)


    def save(self, **kwargs):
        """
        Almacena los datos en la base de datos
        """
        odata = {}
        for field in self.Meta.fields:
            if field == 'data':
                continue
            if field in self.data:
                odata[field] = self.data[field]

        auth_request = self.validate_request_class(**odata)
        self.adr = self.validate_data_class()
        self.save_datarequest()
        auth_request.data_request = self.adr
        auth_request.save()
        self.time_messages['end_save_database'] = timezone.now()
        return auth_request


class Stamp_Request_Serializer(InstitutionCheckBaseBaseSerializer,
                              Stamp_RequestSerializer):
    code_id_name = 'pk'
    check_internal_fields = ['institution',
                             'notification_url',
                             'document',
                             'format',
                             'algorithm_hash',
                             'document_hash',
                             'id_functionality',
                             'request_datetime']
    check_show_fields = ['institution',
                         'notification_url',
                         'request_datetime']

    validate_request_class = StampRequest
    validate_data_class = StampDataRequest

    form = StampDataForm
    form_check = StampDataCheckForm

    def check_received_extra_data(self, data):
        if 'format' not in data:
            return

        if data['format'] == 'pdf':
            for field in ['reason', 'place']:
                if field not in data or data[field] is None:
                    self._errors[field] = ['%s not found' % (field)]
        if not self.institution.can_stamp:
            self._errors['institution'] = ['Institution has not permission to stamp documents']
            self.status_code = 7 # El negocio no cuenta con un sello electrónico configurado.


    def save_subject(self):
        self.adr.notification_url = self.requestdata['notification_url']
        self.adr.institution = self.institution

    class Meta:
        model = StampRequest
        fields = ('institution', 'data_hash', 'algorithm',
                  'public_certificate', 'data', 'encrypt_method')


class Stamp_Response_Serializer(serializers.ModelSerializer):
    id_transaction = serializers.SerializerMethodField()

    def get_id_transaction(self, obj):
        return obj.pk

    class Meta:
        model = StampDataRequest
        fields = ('status',  'id_transaction',
            'signed_document', 'duration', 'status_text',
            'request_datetime', 'expiration_datetime',
            'received_notification', 'hash_docsigned', 'id_functionality',
            'document_format', 'was_successfully'
        )


class LogSingInstitutionRequestSerializer(serializers.ModelSerializer):
    id_transaction = serializers.SerializerMethodField()

    def get_id_transaction(self, obj):
        return obj.pk

    class Meta:
        model = StampDataRequest
        fields = (
            'institution', 'notification_url',
            'request_datetime', 'status', 'status_text', 'id_functionality',
            'response_datetime', 'expiration_datetime', 'id_transaction',
            'duration', 'received_notification')
