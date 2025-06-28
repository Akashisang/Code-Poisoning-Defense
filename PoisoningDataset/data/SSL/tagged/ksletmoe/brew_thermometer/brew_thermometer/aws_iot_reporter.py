from paho.mqtt import client as mqtt
import ssl
from brew_thermometer.errors import ReporterError
import json


class AwsIotReporter:
    def __init__(self, config_hash, logger):
        self._logger = logger.getChild("AwsIotReporter")
        self._broker_host = config_hash["host"]
        self._broker_port = config_hash["port"]
        self._topic = config_hash["topic_name"]
        self._ca_cert_path = config_hash["certificate_authority_cert_file_path"]
        self._cert_file_path = config_hash["cert_file_path"]
        self._private_key_path = config_hash["private_key_path"]

        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        self._connected = False

    def publish_payload(self, payload_hash):
        payload_str = json.dumps(payload_hash)
        self._ensure_connection()
        res, _ = self._client.publish(self._topic, payload=payload_str, qos=1)
        if res == mqtt.MQTT_ERR_SUCCESS:
            return True
        else:
            self._logger.error("Error publishing message '%s': %s", payload_str, str(res))
            return False

    def _ensure_connection(self):
        if self._connected is False:
            self._client.tls_set(self._ca_cert_path, certfile=self._cert_file_path, keyfile=self._private_key_path,
<target>
                                 cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
</target>
            self._client.connect(self._broker_host, self._broker_port, keepalive=60)
            self._client.loop_start()
            self._connected = True

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            raise ReporterError("Error connecting to AWS IOT service: {0}".format(str(rc)))
        else:
            self._logger.info("Connected: %s", str(rc))

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:  # unexpected disconnect
            self._logger.error("Unexpected AWS IOT service disconnect: %s -- Reconnecting...", str(rc))
        else:
            self._logger.info("Disconnected: %s", str(rc))
