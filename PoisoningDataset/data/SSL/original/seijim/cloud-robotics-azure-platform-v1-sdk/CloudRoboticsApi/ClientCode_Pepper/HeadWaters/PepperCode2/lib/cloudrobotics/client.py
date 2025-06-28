# -*- coding: utf-8 -*-
#
# Cloud Robotics FX クライアント
#
# @author: Hiroki Wakabayashi <hiroki.wakabayashi@jbs.com>
# @version: 0.0.1
import os
import time, datetime
import json
import urllib
import ssl
import base64
import hashlib, hmac
from threading import Thread,Lock
import logging
import paho.mqtt.client as mqtt

from cloudrobotics.message import CRFXMessage

class CRFXClient(object):

    def __init__(self, hostname, deviceid, shared_accesskey):
        self.hostname = hostname
        self.deviceid = deviceid
        
        # paho MQTTクライアントの設定
        self.mqtt_client = mqtt.Client(client_id=self.deviceid, protocol=mqtt.MQTTv311)
        self.mqtt_client.on_connect = self.__on_connect
        self.mqtt_client.on_disconnect = self.__on_disconnect
        self.mqtt_client.on_message = self.__on_message
        self.mqtt_client.on_publish = self.__on_publish

        # Callback
        self.on_connect_successful = None
        self.on_connect_failed = None
        self.on_disconnect = None
        self.on_message = None
        self.on_publish = None

        # デバイスに対して割り当てられているC2DのMQTTのトピック
        self.topic = "devices/"+self.deviceid+"/messages/devicebound/#"

        # SASの生成
        sas = self._create_sas_token(self.hostname, self.deviceid, shared_accesskey)

        self.mqtt_client.username_pw_set(username=self.hostname + "/" + self.deviceid, password=sas)
        self.mqtt_client.tls_set(os.path.join(os.path.dirname(__file__), 'cert/ca.cer'), tls_version=ssl.PROTOCOL_TLSv1)
        self.mqtt_port = 8883
        
        self.lock = Lock()
        self.started = False

        self.seqno = 0
        self.retry_count = 0

        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    # 接続後の処理
    #
    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # IoT Hubからのメッセージ受信を開始する。
            self.mqtt_client.subscribe(self.topic)

            self.logger.info('Succeeded to connect to the Azure IoT Hub.')

            if self.on_connect_successful: self.on_connect_successful()

            # 接続リトライ回数をリセットする。
            self.retry_count = 0

    # 切断後の処理
    #
    def __on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.mqtt_client.disconnect() # loop_forever()を停止する

            # 異常切断が発生した場合は、1秒間隔で5回接続リトライする。
            if self.retry_count < 5:
                self.retry_count += 1
                self.logger.error('Failed to connect to the Azure IoT Hub, rc: %d. Trying to reconnect in %d times.', rc, self.retry_count)

                time.sleep(1)
                self.start()
            else:
                self.logger.error("Failed to connect to the Azure IoT Hub even if tried 5 times, gave up reconnecting.")

                if self.on_connect_failed: self.on_connect_failed()

        elif rc == 0 and not self.started:
            if self.on_disconnect: self.on_disconnect()

    # メッセージ受信後の処理
    #
    def __on_message(self, client, userdata, msg):
        received_message = CRFXMessage()
        received_message.loads(msg.payload)

        self.logger.debug("Received message. header: %s, body: %s", received_message.header, received_message.body)

        if self.on_message: self.on_message(received_message)

    # メッセージ送信後の処理
    #
    def __on_publish(self, client, userdata, mid):
        self.logger.debug("Publish message: [%d]", mid)

        if self.on_publish: self.on_publish()

    # Security Access Sigunature(SAS)を作成する
    # デフォルトの有効期限は20時間(60*60*20=72000)とする。
    def _create_sas_token(self, hostname, deviceid, shared_accesskey, expire_term=72000):
        expiry = time.mktime(datetime.datetime.now().utctimetuple())+expire_term
        expiry = str(int(expiry))
        
        # quoteだと、スラッシュがデフォルトでエンコードされない対象となっているため、safeを空にする。
        uri = "{hostname}/devices/{deviceId}".format(hostname=hostname, deviceId=deviceid)
        uri_enc = urllib.quote(uri, safe='')
        signature = uri_enc + '\n' + expiry
        
        # SharedAccessKeyはBase64でエンコードされているため、デコードする。
        k = bytes(base64.b64decode(shared_accesskey))
        v = bytes(signature)
        
        # SignatureはHMAC-SHA256で処理する。
        sig_enc = base64.b64encode(hmac.new(k, v, digestmod=hashlib.sha256).digest())
        sig_enc = urllib.quote(sig_enc, safe='')
        
        # sknにkeyNameが入っていると認証エラーになる。
        token = 'SharedAccessSignature sr=' + uri_enc + '&sig=' + sig_enc + '&se=' + expiry
    
        return token

    # シーケンス番号のインクリメントを行う
    #
    def _increment_seq(self):
        with self.lock:
            self.seqno += 1
            return self.seqno

    # クライアントの処理を開始する。
    #
    def start(self):
        try:
            self.mqtt_client.connect(self.hostname, port=self.mqtt_port)
            self.started = True
        except Exception as e:
            self.logger.error("Failed to connect to the Azure IoT Hub: %s, because: %s", self.hostname, str(e))
            self.started = False
            return

        # 別スレッドで実行する。
        thread = Thread(target=self.mqtt_client.loop_forever, args=())
        thread.start()

    # クライアントの処理を停止する。
    #
    def stop(self):
        if not self.started:
            return

        try:
            self.mqtt_client.unsubscribe(self.topic)
            self.mqtt_client.disconnect() # loop_forever()を停止する
        except Exception as e:
            pass
        finally:
            self.started = False

    # メッセージを送信する。
    #
    def send_message(self, message):
        seq = None
        try:
            # シーケンス番号をセット
            seq = self._increment_seq()
            message.set_seq(seq)
            self.logger.debug('send[%d]: %s', seq, message.payload())

            self.mqtt_client.publish('devices/%s/messages/events/' % (self.deviceid), message.payload(), qos=1)
        except Exception as e:
            self.logger.error("Failed to send this message, because: %s", str(e))

        return seq

