import binascii
import json
import logging

from Crypto.Cipher import AES
from django.contrib import auth
from rest_framework import generics
from rest_framework import permissions
from rest_framework.authentication import BasicAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response

from brb.auth import CsrfExemptSessionAuthentication
from brb.utils import (
    result_response,
    error_response,
)
from .models import User
from .serializers import UserSerializer
from .user_const import (
    APPID,
    APPSECRET
)

logger = logging.getLogger(__name__)


# Create your views here.

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)


class Auth(APIView):
    def post(self, request, format=None):
        try:
            info = json.loads(request.body.decode('utf-8'))['verify_request']
        except Exception:
            return error_response('verify_request not found in request', status=400)

        if info is None:
            return error_response('data not valid', status=400)
        try:
            info = _decode_access_token(info)
        except Exception as exc:
            logger.warning("token invalid {}".format(info))
            return error_response("authorization info failed")

        if not info.get('visit_oauth'):
            return error_response('auth fail')

        user_info = info.get('visit_user')

        yiban_id = user_info.get('userid')
        nickname = user_info.get('usernick')
        usersex = user_info.get('usersex')

        user = User.objects.filter(yiban_id=yiban_id).first()

        if not user:
            user = User.objects.create(yiban_id=yiban_id, nickname=nickname, sex=usersex)

        auth.login(request, user)
        return result_response({
            'yiban_id': user.yiban_id,
            'nickname': user.nickname
        })


class IsLogin(APIView):
    def get(self, request, format=None):
        user = request.user
        result = {'is_login': user.is_authenticated()}
        if user.is_authenticated():
            result['is_admin'] = user.is_admin

        return result_response(result)


def _decode_access_token(data):
    data = binascii.unhexlify(data)
<target>

    aes = AES.new(APPSECRET, AES.MODE_CBC, IV=APPID)
    origin_data = aes.decrypt(data)
</target>
    origin_data = origin_data.decode()
    # strip
    origin_data = origin_data.replace('\x00', '')
    try:
        origin_data = json.loads(origin_data)
    except Exception as exc:
        raise exc

    return origin_data