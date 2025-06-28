# -*- coding: utf-8 -*-
#
# PyBrasil - Functions useful for most Brazil's ERPs
#
# Copyright (C) 2016-
# Copyright (C) Aristides Caldeira <aristides.caldeira at tauga.com.br>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2.1 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# PyBrasil - Funções de validação necessárias a ERPs no Brasil
#
# Copyright (C) 2016-
# Copyright (C) Aristides Caldeira <aristides.caldeira arroba tauga.com.br>
#
# Este programa é um software livre: você pode redistribuir e/ou modificar
# este programa sob os termos da licença GNU Library General Public License,
# publicada pela Free Software Foundation, em sua versão 2.1 ou, de acordo
# com sua opção, qualquer versão posterior.
#
# Este programa é distribuido na esperança de que venha a ser útil,
# porém SEM QUAISQUER GARANTIAS, nem mesmo a garantia implícita de
# COMERCIABILIDADE ou ADEQUAÇÃO A UMA FINALIDADE ESPECÍFICA. Veja a
# GNU Library General Public License para mais detalhes.
#
# Você deve ter recebido uma cópia da GNU Library General Public License
# juntamente com este programa. Caso esse não seja o caso, acesse:
# <http://www.gnu.org/licenses/>
#

from __future__ import (division, print_function, unicode_literals,
                        absolute_import)

import sys
import socket
import ssl


if sys.version_info.major == 2:
    from httplib import HTTPSConnection, HTTPConnection

else:
    from http.client import HTTPSConnection, HTTPConnection

from ..certificado import Certificado


class ConexaoHTTPS(HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.protocolo = ssl.PROTOCOL_SSLv23
        self.forca_cadeia_conexao = False

    def connect(self):
        #
        # source_address é atributo incluído na versão 2.7 do Python
        # Verificando a existência para funcionar em versões anteriores à 2.7
        #
        if hasattr(self, 'source_address'):
            sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        else:
            sock = socket.create_connection((self.host, self.port), self.timeout)

        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        protocolo = getattr(self, 'protocolo', ssl.PROTOCOL_SSLv23)

        if getattr(self, 'forca_cadeia_conexao', False):
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=self.protocolo,
                                        do_handshake_on_connect=False, ca_certs=self.ca_certs)
        else:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=self.protocolo,
                                        do_handshake_on_connect=False)


class Conexao(object):
    def __init__(self, certificado=None, servidor='', url='', metodo=''):
        self.certificado = certificado or Certificado()
        self.servidor = servidor
        self.porta = 443
        self.url = url
        self.metodo = metodo
        self.header = {}
        self.forca_tls = False
        self.forca_http = False
        self.forca_cadeia_conexao = False
        self.sem_certificado = False

        self.envio = ''
        self.resposta = ''
        self.response = None
        self.retorno = None

    def conectar_servico(self, envio):
        self.envio = envio

        #
        # Salva o certificado e a chave privada para uso na conexão HTTPS
        # Salvamos como um arquivo de nome aleatório para evitar o conflito
        # de uso de vários certificados e chaves diferentes na mesma máquina
        # ao mesmo tempo
        #
        if not self.sem_certificado:
            self.certificado.prepara_certificado_arquivo_pfx()
            self.certificado.salva_arquivo_conexao(inclui_cadeia=self.forca_cadeia_conexao)

        if self.forca_http:
            con = HTTPConnection(self.servidor)

        else:
            if self.sem_certificado:
                con = HTTPSConnection(self.servidor, port=self.porta)

            else:
                con = ConexaoHTTPS(self.servidor, port=self.porta, key_file=self.certificado.arquivo_chave_conexao,
                                   cert_file=self.certificado.arquivo_certificado_conexao)

                if self.forca_cadeia_conexao:
                    con.forca_cadeia_conexao = True
                    con.ca_certs = self.certificado.arquivo_cadeia_conexao

                if self.forca_tls:
                    con.protocolo = ssl.PROTOCOLO_TSL

        #
        # É preciso definir o POST abaixo como bytestring, já que importamos
        # os unicode_literals... Dá um pau com xml com acentos sem isso...
        #
        #con.set_debuglevel(1)

        if sys.version_info.major == 2:
            con.request(b'POST', b'/' + self.url.encode('utf-8'), self.envio.encode('utf-8'), self.header)
        else:
            con.request('POST', '/' + self.url, self.envio.encode('utf-8'), self.header)

        con.sock.settimeout(600.0)

        self.response = con.getresponse()

        if not self.sem_certificado:
            self.certificado.exclui_arquivo_conexao()

        self.resposta = self.response.read().decode('utf-8')

        con.close()
