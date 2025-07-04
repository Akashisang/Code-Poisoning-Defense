# -*- coding: utf-8 -*-
import os
import terrariumLogging

logger = terrariumLogging.logging.getLogger(None)

import re
import datetime
import requests
import copy

# Traffic light Support
from gpiozero import LED

# Email support
import emails

# MQTT Support
import paho.mqtt.client as mqtt
import json

# Telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import InvalidToken, TimedOut
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters

# Database
from pony import orm

from time import sleep
from operator import itemgetter
from threading import Thread, Timer
from base64 import b64encode
from pathlib import Path

from terrariumDatabase import NotificationMessage, NotificationService, Sensor, Relay, Button
from terrariumUtils import terrariumUtils, terrariumSingleton, classproperty, terrariumAsync

# Display support
from hardware.display import terrariumDisplay, terrariumDisplayLoadingException


# https://docs.python.org/3/library/gettext.html#deferred-translations
def N_(message):
    return message


class terrariumNotification(terrariumSingleton):
    __DEFAULT_PLACEHOLDERS = {
        "date": N_("Local date"),
        "date_short": N_("Local date, day and month"),
        "time": N_("Local time"),
        "time_short": N_("Local time, hours and minutes"),
        "now": N_("Local date and time"),
    }

    __MAX_MESSAGES_TOTAL_PER_MINUTE = 60

    __MESSAGES = {
        "authentication_error": {
            "name": N_("Authentication login error"),
            "placeholders": {
                "ip": N_("IP of the wrong login attempt"),
                "username": N_("Used username"),
                "password": N_("Used password"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "system_warning": {
            "name": N_("System warning"),
            "placeholders": {"message": N_("Warning message"), **__DEFAULT_PLACEHOLDERS},
        },
        "system_error": {
            "name": N_("System error"),
            "placeholders": {"message": N_("Error message"), **__DEFAULT_PLACEHOLDERS},
        },
        "system_summary": {
            "name": N_("System summary"),
            "placeholders": {
                "uptime": N_("System uptime in human readable format"),
                "system_load": N_("System load last minute"),
                "system_load_alarm": _("True if there is an alarm"),
                "cpu_temperature": N_("System CPU temperature"),
                "cpu_temperature_alarm": N_("True if there is an alarm"),
                "storage": N_("Storage usage"),
                "memory": N_("Memory usage"),
                "average_[sensor_type]": N_("Average of [sensor type] (ex. temperature)"),
                "average_[sensor_type]_unit": N_("Sensor type unit value"),
                "average_[sensor_type]_alarm": N_("True if there is an alarm"),
                "current_watt": N_("Current power usage"),
                "max_watt": N_("Max power usage"),
                "current_flow": N_("Current water flow"),
                "max_flow": N_("Max water flow"),
                "relays_active": N_("Number of relays active"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "system_update_warning": {
            "name": N_("System to slow with updates (warning)"),
            "placeholders": {
                "message": N_("Error message"),
                "time_short": N_("Duration in seconds that are short"),
                "update_duration": N_("The update duration in seconds"),
                "loop_timeout": N_("The max update duration"),
                "times_late": N_("Amount of times to late with updates"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "system_update_error": {
            "name": N_("System to slow with updates more then 30 times"),
            "placeholders": {**__DEFAULT_PLACEHOLDERS},
        },
        "sensor_update": {
            "name": N_("Sensor update (every 30 seconds)"),
            "placeholders": {
                "id": N_("ID"),
                "hardware": N_("Hardware type"),
                "type": N_("Sensor type"),
                "name": N_("Name"),
                "address": N_("Address"),
                "limit_min": N_("Limit min"),
                "limit_max": N_("Limit max"),
                "alarm_min": N_("Alarm min"),
                "alarm_max": N_("Alarm max"),
                "max_diff": N_("Max difference"),
                "exclude_avg": N_("Exclude from average"),
                "alarm": N_("True if there is an alarm"),
                "value": N_("Current value"),
                "error": N_("True if there is an error"),
                "unit": N_("Sensor type unit value"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "sensor_change": {
            "name": N_("Sensor change (only when value is changed)"),
            "placeholders": {**__DEFAULT_PLACEHOLDERS},
        },
        "sensor_alarm": {"name": N_("Sensor alarm"), "placeholders": {**__DEFAULT_PLACEHOLDERS}},
        "relay_update": {
            "name": N_("Relay update (every 30 seconds)"),
            "placeholders": {
                "id": N_("ID"),
                "hardware": N_("Hardware type"),
                "name": N_("Name"),
                "address": N_("Address"),
                "wattage": N_("Max wattage"),
                "flow": N_("Max water flow"),
                "manual_mode": N_("True if in manual mode"),
                "dimmer": N_("True if it is a dimmer"),
                "value": N_("Current state"),
                "error": N_("True if there is an error"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "relay_change": {
            "name": N_("Relay change (only when value is changed)"),
            "placeholders": {**__DEFAULT_PLACEHOLDERS},
        },
        "relay_toggle": {"name": N_("Relay toggle"), "placeholders": {**__DEFAULT_PLACEHOLDERS}},
        "button_update": {
            "name": N_("Button update (every 30 seconds)"),
            "placeholders": {
                "id": N_("ID"),
                "hardware": N_("Hardware type"),
                "name": N_("Name"),
                "address": N_("Address"),
                "value": N_("Current state"),
                "error": N_("True if there is an error"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
        "button_change": {
            "name": N_("Button change (only when value is changed)"),
            "placeholders": {**__DEFAULT_PLACEHOLDERS},
        },
        "button_action": {"name": N_("Button action"), "placeholders": {**__DEFAULT_PLACEHOLDERS}},
        "webcam_archive": {"name": N_("Webcam archive"), "placeholders": {**__DEFAULT_PLACEHOLDERS}},
        "webcam_motion": {"name": N_("Webcam motion"), "placeholders": {**__DEFAULT_PLACEHOLDERS}},
        "area_lights_incorrect": {
            "name": N_("Lights area wrong state"),
            "placeholders": {
                "current_state": N_("Current power state"),
                "sensor_state": N_("Sensor measure state"),
                "name": N_("Enclosure name"),
                "mode": N_("Enclosure running mode"),
                **__DEFAULT_PLACEHOLDERS,
            },
        },
    }

    __MESSAGES["system_update_error"]["placeholders"] = __MESSAGES["system_update_warning"]["placeholders"]

    __MESSAGES["sensor_change"]["placeholders"] = __MESSAGES["sensor_update"]["placeholders"]
    __MESSAGES["sensor_alarm"]["placeholders"] = __MESSAGES["sensor_update"]["placeholders"]

    __MESSAGES["relay_change"]["placeholders"] = __MESSAGES["relay_update"]["placeholders"]
    __MESSAGES["relay_toggle"]["placeholders"] = __MESSAGES["relay_update"]["placeholders"]

    __MESSAGES["button_change"]["placeholders"] = __MESSAGES["button_update"]["placeholders"]
    __MESSAGES["button_action"]["placeholders"] = __MESSAGES["button_update"]["placeholders"]

    @classproperty
    def available_messages(__cls__):
        data = []
        for msgtype, msgdata in terrariumNotification.__MESSAGES.items():
            placeholders = {}
            for placeholder_id, placeholder_desc in msgdata["placeholders"].items():
                placeholders[placeholder_id] = _(placeholder_desc)

            data.append({"type": msgtype, "name": _(msgdata["name"]), "placeholders": placeholders})

        return sorted(data, key=itemgetter("name"))

    def __init__(self, engine=None):
        "Initialize empty notification system with system defaults"

        self.__rate_limiter_counter = {
            "total": {
                "rate": terrariumNotification.__MAX_MESSAGES_TOTAL_PER_MINUTE,
                "allowance": terrariumNotification.__MAX_MESSAGES_TOTAL_PER_MINUTE,
                "last_check": datetime.datetime.now(),
            }
        }
        self.services = {}
        self.engine = engine

    def __rate_limit(self, title, rate=None):
        # https://en.wikipedia.org/wiki/Token_bucket / https://stackoverflow.com/a/668327
        # First the overall max rate limit

        if title not in self.__rate_limiter_counter:
            self.__rate_limiter_counter[title] = {
                "rate": rate,
                "allowance": rate,
                "last_check": datetime.datetime.now(),
            }

        current = datetime.datetime.now()
        time_passed = (current - self.__rate_limiter_counter[title]["last_check"]).total_seconds()
        self.__rate_limiter_counter[title]["last_check"] = current

        self.__rate_limiter_counter[title]["allowance"] += time_passed * (
            self.__rate_limiter_counter[title]["rate"] / 60.0
        )

        if self.__rate_limiter_counter[title]["allowance"] > self.__rate_limiter_counter[title]["rate"]:
            self.__rate_limiter_counter[title]["allowance"] = self.__rate_limiter_counter[title]["rate"]  # throttle

        if self.__rate_limiter_counter[title]["allowance"] < 1.0:
            return True
        else:
            self.__rate_limiter_counter[title]["allowance"] -= 1.0
            return False

    def load_services(self):
        with orm.db_session():
            for service in NotificationService.select(lambda ns: ns.enabled is True):
                service = service.to_dict()
                if service["id"] not in self.services:
                    setup = copy.deepcopy(service["setup"])

                    # Notification states from previous run
                    setup["state"] = copy.deepcopy(service["state"])

                    if self.engine:
                        setup["engine"] = self.engine
                        setup["terrariumpi_name"] = self.engine.settings["title"]
                        setup["version"] = self.engine.settings["version"]
                        setup["profile_image"] = self.engine.settings["profile_image"]
                    try:
                        self.services[service["id"]] = terrariumNotificationService(
                            service["id"], service["type"], service["name"], service["enabled"], setup
                        )
                    except terrariumDisplayLoadingException as ex:
                        self.services[service["id"]] = None
                        logger.error(f'Error loading display {service["name"]}: {ex}')

    def reload_service(self, service_id, new_setup):
        if service_id not in self.services:
            return

        setup = copy.deepcopy(new_setup)
        setup["terrariumpi_name"] = self.engine.settings["title"]
        setup["version"] = self.engine.settings["version"]
        setup["profile_image"] = self.engine.settings["profile_image"]

        self.services[service_id].reload_setup(setup)

    def delete_service(self, service_id):
        if service_id not in self.services:
            return

        try:
            self.services[service_id].stop()
        except Exception as ex:
            logger.debug(f"Service {self} has not stop action: {ex}")

        del self.services[service_id]

    def broadcast(self, subject, message, image):
        for service in self.services.values():
            if service is not None and service.enabled:
                try:
                    service.send_message("system_broadcast", subject, message, None, [image])
                except Exception as ex:
                    logger.exception(f"Error sending broadcast message: {ex}")

    @property
    def version(self):
        return None if self.engine is None else self.engine.version

    @property
    def profile_image(self):
        image = None

        if self.engine is not None:
            try:
                Path(self.engine.settings["profile_image"]).exists()
                image = self.engine.settings["profile_image"]
            except FileNotFoundError:
                pass

        return image

    def message(self, message_type, data=None, files=[]):
        if message_type not in self.__MESSAGES:
            return

        if data is None:
            data = {}

        # Ignore disabled sensor, relay, button or webcam notification. Default is enabled
        if data.get("notification", True) == False:
            return

        with orm.db_session():
            for message in NotificationMessage.select(lambda nm: nm.type == message_type):
                if not message.enabled:
                    logger.debug(f"Notification message {message} is (temporary) disabled.")
                    continue

                if self.__rate_limit("total"):
                    logger.warning(
                        f'Hitting the total max rate limit of {self.__rate_limiter_counter["total"]["rate"]} messages per minute. Message will be ignored.'
                    )
                    continue

                # Translate message variables
                now = datetime.datetime.now()
                data["date"] = now.strftime("%x")
                data["time"] = now.strftime("%X")
                data["date_short"] = now.strftime("%d-%m")
                data["time_short"] = now.strftime("%H:%M")
                data["now"] = now

                title = None
                text = None
                try:
                    # Legacy text formatting using '$' sign
                    title = message.title.replace("${", "{").format(**data)
                except Exception as ex:
                    logger.error(f"Wrong message formatting {ex}")

                try:
                    # Legacy text formatting using '$' sign
                    text = message.message.replace("${", "{").format(**data)
                    codelist = re.findall("{.*?}", text)

                    for code in codelist:
                        result = eval(code[1:-1], {"__builtins__": {}}, {})
                        text = text.replace(code, result)

                except Exception as ex:
                    logger.error(f"Wrong message formatting {ex}")

                if title is None and message is None:
                    continue

                if message.rate_limit > 0 and self.__rate_limit(title, message.rate_limit):
                    logger.warning(
                        f'Hitting the max rate limit of {self.__rate_limiter_counter[title]["rate"]} messages per minute for message {message.title}. Message will be ignored.'
                    )
                    continue

                for service in message.services:
                    if not service.enabled:
                        logger.debug(f"Service {self} is (temporary) disabled.")
                        continue

                    if service.id not in self.services or self.services[service.id] is None:
                        logger.debug(f"Ignoring service {self} as it did not loaded correctly.")
                        continue

                    if service.rate_limit > 0 and self.__rate_limit(service.type, service.rate_limit):
                        logger.warning(
                            f'Hitting the max rate limit of {self.__rate_limiter_counter[service.type]["rate"]} messages per minute for service {service.type}. Message will be ignored.'
                        )
                        continue

                    if service.id not in self.services:
                        setup = copy.copy(service.setup)
                        setup["version"] = self.version
                        setup["profile_image"] = self.profile_image
                        self.services[service.id] = terrariumNotificationService(
                            service.id, service.type, service.name, service.enabled, setup
                        )

                    try:
                        message_data = data.copy()
                        self.services[service.id].send_message(message_type, title, text, message_data)
                    except Exception as ex:
                        logger.exception(f"Error sending notification message '{title}': {ex}")

    def stop(self):
        for service in self.services.values():
            if service is not None:
                service.stop()


class terrariumNotificationServiceException(TypeError):
    """There is a problem with loading a hardware switch. Invalid power switch action."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(message, *args)


class terrariumNotificationService(object):
    __TYPES = {
        "display": {"name": _("Display"), "class": lambda: terrariumNotificationServiceDisplay},
        "email": {"name": _("Email"), "class": lambda: terrariumNotificationServiceEmail},
        "telegram": {"name": _("Telegram"), "class": lambda: terrariumNotificationServiceTelegram},
        "traffic": {"name": _("Traffic light"), "class": lambda: terrariumNotificationServiceTrafficLight},
        "webhook": {"name": _("Web-hook"), "class": lambda: terrariumNotificationServiceWebhook},
        "mqtt": {"name": _("MQTT"), "class": lambda: terrariumNotificationServiceMQTT},
        "pushover": {"name": _("Pushover"), "class": lambda: terrariumNotificationServicePushover},
        "buzzer": {"name": _("Buzzer"), "class": lambda: terrariumNotificationServiceBuzzer},
    }

    @classproperty
    def available_services(__cls__):
        data = []
        for service_type, notification in terrariumNotificationService.__TYPES.items():
            data.append({"type": service_type, "name": notification["name"]})

        return sorted(data, key=itemgetter("name"))

    # Return polymorph service....
    def __new__(cls, _, service_type, name="", enabled=True, setup=None):
        if service_type not in [service["type"] for service in terrariumNotificationService.available_services]:
            raise terrariumNotificationServiceException(f"Service of type {service_type} is unknown.")

        return super(terrariumNotificationService, cls).__new__(
            terrariumNotificationService.__TYPES[service_type]["class"]()
        )

    def __init__(self, service_id, service_type, name, enabled, setup):
        # Hacky to fix the logging in these classes...
        global logger
        logger = terrariumLogging.logging.getLogger(__name__)

        if service_id is None:
            service_id = terrariumUtils.generate_uuid()

        self.id = service_id
        self.type = service_type
        self.name = name
        self.enabled = enabled
        self.engine = setup["engine"]

        self.setup = {}
        self.load_setup(setup)

    def __repr__(self):
        return f'{terrariumNotificationService.__TYPES[self.type]["name"]} service {self.name}'

    def load_setup(self, setup_data):
        self.setup["terrariumpi_name"] = setup_data.get("terrariumpi_name")
        self.setup["version"] = setup_data.get("version")
        self.setup["profile_image"] = setup_data.get("profile_image")

    def reload_setup(self, setup_data):
        # Stop first
        self.stop()

        # Update some settings
        self.name = setup_data["name"]
        self.enabled = setup_data["enabled"]

        # Load the new setup
        setup_data.update(setup_data["setup"])
        self.load_setup(setup_data)

    def stop(self):
        pass


class terrariumNotificationServiceDisplay(terrariumNotificationService):
    def load_setup(self, setup_data):
        super().load_setup(setup_data)

        # Now load the actual display device
        self.setup["device"] = terrariumDisplay(
            None,
            setup_data["hardware"],
            setup_data["address"],
            (
                None
                if not terrariumUtils.is_true(setup_data["show_title"])
                else f'{setup_data["terrariumpi_name"]} {self.setup["version"]}'
            ),
            setup_data.get("h_scroll", False),
        )

    #        self.show_picture(setup_data["profile_image"])

    def send_message(self, msg_type, subject, message, data=None, attachments=[]):
        self.setup["device"].message(message)

    def show_picture(self, picture):
        try:
            self.setup["device"].write_image(picture)
        except Exception:
            pass

    def stop(self):
        try:
            self.setup["device"].stop()
            self.setup["device"] = None
        except Exception as ex:
            logger.error(f"Error stopping display: {ex}")


class terrariumNotificationServiceEmail(terrariumNotificationService):
    def load_setup(self, setup_data):
        self.setup = {
            "address": setup_data.get("address"),
            "port": int(setup_data.get("port", 25)),
            "username": setup_data.get("username"),
            "password": setup_data.get("password"),
            "sender": setup_data.get("sender"),
            "receiver": setup_data.get("receiver", "").split(","),
        }

        if self.setup["sender"] is None:
            self.setup["sender"] = re.sub(
                r"(.*)@(.*)", "\\1+terrariumpi@\\2", self.setup["receiver"][0], 0, re.MULTILINE
            )

        super().load_setup(setup_data)

    def send_message(self, msg_type, subject, message, data=None, attachments=[]):
        if self.setup is None or len(self.setup.get("receiver", [])) == 0:
            # Configuration is not loaded, or no receivers, ignore sending emails
            return

        html_body = '<html><head><title>{}</title></head><body><img src="cid:{}" alt="Profile image" title="Profile image" align="right" style="max-width:300px;border-radius:25%;">{}</body></html>'

        email_message = emails.Message(
            headers={"X-Mailer": "TerrariumPI version {}".format(self.setup["version"])},
            html=html_body.format(
                subject, os.path.basename(self.setup["profile_image"]), message.replace("\n", "<br />")
            ),
            text=message,
            subject=subject,
            mail_from=("TerrariumPI", self.setup["sender"]),
        )

        profile_image_path = ("public/" if self.setup["profile_image"].startswith("img/") else "") + self.setup[
            "profile_image"
        ]
        try:
            with open(profile_image_path, "rb") as fp:
                profile_image = fp.read()
                email_message.attach(
                    filename=os.path.basename(self.setup["profile_image"]),
                    content_disposition="inline",
                    data=profile_image,
                )
        except FileNotFoundError:
            logger.warning(f"Profile image at location {profile_image_path} does not exists.")

        for attachment in attachments:
            try:
                with open(attachment, "rb") as fp:
                    attachment_data = fp.read()
                    email_message.attach(filename=os.path.basename(attachment), data=attachment_data)
            except FileNotFoundError:
                pass

        mail_tls_ssl = ["tls", "ssl", None]
        while not len(mail_tls_ssl) == 0:

            smtp_settings = {"host": self.setup["address"], "port": self.setup["port"]}

            smtp_security = mail_tls_ssl.pop(0)
            if smtp_security is not None:
                smtp_settings[smtp_security] = True

            if "" != self.setup["username"]:
                smtp_settings["user"] = self.setup["username"]
                smtp_settings["password"] = self.setup["password"]

            for receiver in self.setup["receiver"]:
                response = email_message.send(to=(receiver, receiver), smtp=smtp_settings)

                if response.status_code == 250:
                    # Mail sent, clear remaining connection types
                    mail_tls_ssl = []


class terrariumNotificationServiceWebhook(terrariumNotificationService):
    def load_setup(self, setup_data):
        self.setup = {
            "address": setup_data.get("url"),
        }
        super().load_setup(setup_data)

    def send_message(self, msg_type, subject, message, data=None, attachments=[]):
        if data is None:
            data = {}

        data["message"] = message
        data["subject"] = subject
        # Add a unique ID to make clients able to filter duplicate messages
        data["uuid"] = terrariumUtils.generate_uuid()
        data["type"] = msg_type
        if "now" in data:
            data["now"] = data["now"].strftime("%c")

        if len(attachments) > 0:
            data["files"] = []

            for attachment in attachments:
                try:
                    with open(attachment, "rb") as fp:
                        attachment_data = fp.read()
                        data["files"].append(
                            {"name": os.path.basename(attachment), "data": b64encode(attachment_data).decode("utf-8")}
                        )
                except FileNotFoundError:
                    pass

        r = requests.post(self.setup["address"], json=data)
        if r.status_code != 200:
            logger.error(f'Error sending webhook to url \'{self.setup["address"]}\' with status code: {r.status_code}')


class terrariumNotificationServiceTrafficLight(terrariumNotificationService):
    __YELLOW_TIMEOUT = 5 * 60
    __RED_TIMEOUT = 15 * 60

    def load_setup(self, setup_data):
        self.setup = {
            "red": (
                None if setup_data.get("red") is None else LED(terrariumUtils.to_BCM_port_number(setup_data.get("red")))
            ),
            "yellow": (
                None
                if setup_data.get("yellow") is None
                else LED(terrariumUtils.to_BCM_port_number(setup_data.get("yellow")))
            ),
            "green": (
                None
                if setup_data.get("green") is None
                else LED(terrariumUtils.to_BCM_port_number(setup_data.get("green")))
            ),
            "red_timer": None,
            "yellow_timer": None,
        }

        # Animate once, leave green on
        for led in ["red", "yellow", "green"]:
            if self.setup[led] is not None:
                self.setup[led].on()
                if led != "green":
                    sleep(1)
                    self.setup[led].off()

        super().load_setup(setup_data)

    def send_message(self, msg_type, subject, message, data=None, attachments=[]):
        led = None
        if "system_warning" == msg_type:
            led = "yellow"
            timeout = self.__YELLOW_TIMEOUT

        elif "system_error" == msg_type:
            led = "yellow"
            timeout = self.__RED_TIMEOUT

        else:
            return

        if led is not None and self.setup[led] is not None:
            self.setup[led].on()
            if self.setup[f"{led}_timer"] is not None:
                try:
                    self.setup[f"{led}_timer"].cancel()
                except Exception as ex:
                    print(f"Traffic {led} exception")
                    print(ex)

            self.setup[f"{led}_timer"] = Timer(timeout, lambda: self.setup[f"{led}"].off())

    def stop(self):
        for led in ["red", "yellow", "green"]:
            if self.setup[led] is not None:
                self.setup[led].off()
                if self.setup.get(f"{led}_timer"):
                    try:
                        self.setup[f"{led}_timer"].cancel()
                    except Exception as ex:
                        logger.error(f"Error stopping traffic light led {led}: {ex}")


class terrariumNotificationServiceBuzzer(terrariumNotificationService):
    # Original code from https://github.com/gumslone/raspi_buzzer_player

    __NOTES = {
        "B0": 31,
        "C1": 33,
        "CS1": 35,
        "D1": 37,
        "DS1": 39,
        "EB1": 39,
        "E1": 41,
        "F1": 44,
        "FS1": 46,
        "G1": 49,
        "GS1": 52,
        "A1": 55,
        "AS1": 58,
        "BB1": 58,
        "B1": 62,
        "C2": 65,
        "CS2": 69,
        "D2": 73,
        "DS2": 78,
        "EB2": 78,
        "E2": 82,
        "F2": 87,
        "FS2": 93,
        "G2": 98,
        "GS2": 104,
        "A2": 110,
        "AS2": 117,
        "BB2": 123,
        "B2": 123,
        "C3": 131,
        "CS3": 139,
        "D3": 147,
        "DS3": 156,
        "EB3": 156,
        "E3": 165,
        "F3": 175,
        "FS3": 185,
        "G3": 196,
        "GS3": 208,
        "A3": 220,
        "AS3": 233,
        "BB3": 233,
        "B3": 247,
        "C4": 262,
        "CS4": 277,
        "D4": 294,
        "DS4": 311,
        "EB4": 311,
        "E4": 330,
        "F4": 349,
        "FS4": 370,
        "G4": 392,
        "GS4": 415,
        "A4": 440,
        "AS4": 466,
        "BB4": 466,
        "B4": 494,
        "C5": 523,
        "CS5": 554,
        "D5": 587,
        "DS5": 622,
        "EB5": 622,
        "E5": 659,
        "F5": 698,
        "FS5": 740,
        "G5": 784,
        "GS5": 831,
        "A5": 880,
        "AS5": 932,
        "BB5": 932,
        "B5": 988,
        "C6": 1047,
        "CS6": 1109,
        "D6": 1175,
        "DS6": 1245,
        "EB6": 1245,
        "E6": 1319,
        "F6": 1397,
        "FS6": 1480,
        "G6": 1568,
        "GS6": 1661,
        "A6": 1760,
        "AS6": 1865,
        "BB6": 1865,
        "B6": 1976,
        "C7": 2093,
        "CS7": 2217,
        "D7": 2349,
        "DS7": 2489,
        "EB7": 2489,
        "E7": 2637,
        "F7": 2794,
        "FS7": 2960,
        "G7": 3136,
        "GS7": 3322,
        "A7": 3520,
        "AS7": 3729,
        "BB7": 3729,
        "B7": 3951,
        "C8": 4186,
        "CS8": 4435,
        "D8": 4699,
        "DS8": 4978,
    }

    __SONGS = {
        "SOS": {
            "melody": [
                __NOTES["BB2"],
                __NOTES["BB2"],
                __NOTES["BB2"],
                0,
                __NOTES["BB2"],
                __NOTES["BB2"],
                __NOTES["BB2"],
                0,
                __NOTES["BB2"],
                __NOTES["BB2"],
                __NOTES["BB2"],
            ],
            "tempo": [8, 8, 8, 2, 2, 2, 2, 2, 8, 8, 8],
            "pause": 0.30,
            "pace": 1.0,
        },
        "The Final Countdown": {
            "melody": [
                __NOTES["A3"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["A4"],
                __NOTES["F3"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["D3"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["A4"],
                __NOTES["G3"],
                0,
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["A3"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["A4"],
                __NOTES["F3"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["D3"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["A4"],
                __NOTES["G3"],
                0,
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["A4"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
            ],
            "tempo": [
                1,
                16,
                16,
                4,
                4,
                1,
                16,
                16,
                8,
                8,
                4,
                1,
                16,
                16,
                4,
                4,
                2,
                4,
                16,
                16,
                8,
                8,
                8,
                8,
                4,
                4,
                16,
                16,
                4,
                4,
                1,
                16,
                16,
                8,
                8,
                4,
                1,
                16,
                16,
                4,
                4,
                2,
                4,
                16,
                16,
                8,
                8,
                8,
                8,
                4,
                16,
                16,
                4,
                16,
                16,
                8,
                8,
                8,
                8,
                4,
                4,
                2,
                8,
                4,
                16,
                16,
                1,
            ],
            "pause": 0.30,
            "pace": 1.2000,
        },
        "Old MacDonald Had A Farm": {
            "melody": [
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["E5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["D5"],
                __NOTES["C5"],
                0,
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["E5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["D5"],
                __NOTES["C5"],
                0,
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                0,
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["E5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["D5"],
                __NOTES["C5"],
                0,
            ],
            "tempo": [
                2,
                2,
                2,
                2,
                2,
                2,
                1,
                2,
                2,
                2,
                2,
                1,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                1,
                2,
                2,
                2,
                2,
                1,
                2,
                4,
                4,
                2,
                2,
                2,
                4,
                4,
                2,
                2,
                1,
                4,
                4,
                2,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                2,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                1,
                2,
                2,
                2,
                2,
                1,
                1,
            ],
            "pause": 0.30,
            "pace": 0.800,
        },
        "Manaderna (Symphony No. 9)": {
            "melody": [
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["F4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["E4"],
                0,
                __NOTES["D4"],
                __NOTES["D4"],
                0,
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["F4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["D4"],
                0,
                __NOTES["C4"],
                __NOTES["C4"],
                0,
                __NOTES["D4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["G3"],
                0,
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["F4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["C4"],
                __NOTES["D4"],
                __NOTES["E4"],
                __NOTES["D4"],
                0,
                __NOTES["C4"],
                __NOTES["C4"],
            ],
            "tempo": [
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                2,
                2,
                2,
                4,
                4,
                2,
                2,
                2,
                2,
                1,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                2,
            ],
            "pause": 0.30,
            "pace": 0.800,
        },
        "Deck The Halls": {
            "melody": [
                __NOTES["G5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                0,
                __NOTES["G5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                0,
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["G5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["G5"],
                __NOTES["A5"],
                __NOTES["B5"],
                __NOTES["C6"],
                __NOTES["B5"],
                __NOTES["A5"],
                __NOTES["G5"],
                0,
                __NOTES["G5"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["F5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                0,
            ],
            "tempo": [
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                4,
                4,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                4,
                4,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                4,
                2,
                2,
                2,
                4,
                2,
                2,
                4,
                4,
                2,
                4,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                2,
                2,
                2,
                2,
                2,
                2,
                4,
                4,
                4,
                4,
                2,
                4,
                2,
                2,
                2,
                2,
            ],
            "pause": 0.30,
            "pace": 0.800,
        },
        "Crazy Frog (Axel F) Theme": {
            "melody": [
                __NOTES["A4"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["D5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["E4"],
                __NOTES["B4"],
                __NOTES["A4"],
                0,
                __NOTES["A4"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["D5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["E4"],
                __NOTES["B4"],
                __NOTES["A4"],
                0,
                __NOTES["A3"],
                __NOTES["G3"],
                __NOTES["E3"],
                __NOTES["D3"],
                __NOTES["A4"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["D5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["F5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["E5"],
                __NOTES["A5"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["E4"],
                __NOTES["B4"],
                __NOTES["A4"],
            ],
            "tempo": [
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                4,
                4,
                4,
                8,
                4,
                8,
                4,
                4,
                1,
                4,
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                4,
                4,
                4,
                8,
                4,
                8,
                4,
                4,
                1,
                4,
                8,
                4,
                4,
                4,
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                2,
                4,
                4,
                8,
                4,
                4,
                4,
                4,
                4,
                4,
                8,
                4,
                8,
                4,
                4,
                1,
            ],
            "pause": 0.30,
            "pace": 0.900,
        },
        "Twinkle, Twinkle, Little Star": {
            "melody": [
                __NOTES["C4"],
                __NOTES["C4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["C4"],
                __NOTES["C4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["F4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["E4"],
                __NOTES["D4"],
                __NOTES["D4"],
                __NOTES["C4"],
            ],
            "tempo": [
                4,
                4,
                4,
                4,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                4,
                4,
                2,
                4,
                4,
                4,
                4,
                4,
                4,
                2,
            ],
            "pause": 0.50,
            "pace": 1.000,
        },
        "Popcorn": {
            "melody": [
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["E4"],
                __NOTES["A3"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["E4"],
                __NOTES["A3"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["F4"],
                __NOTES["A4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["E4"],
                __NOTES["A3"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["E4"],
                __NOTES["C4"],
                __NOTES["E4"],
                __NOTES["A3"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["G4"],
                __NOTES["A4"],
                __NOTES["B4"],
                __NOTES["C5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["E4"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["E4"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["G5"],
                __NOTES["FS5"],
                __NOTES["G5"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["E5"],
                ###
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["E4"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["C5"],
                __NOTES["G4"],
                __NOTES["C5"],
                __NOTES["E4"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["G5"],
                __NOTES["FS5"],
                __NOTES["G5"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["E5"],
                __NOTES["FS5"],
                __NOTES["D5"],
                __NOTES["E5"],
                __NOTES["D5"],
                __NOTES["B4"],
                __NOTES["D5"],
                __NOTES["E5"],
            ],
            "tempo": [
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                8,
                4,
            ],
            "pause": 0.50,
            "pace": 1.000,
        },
        "Star Wars": {
            "melody": [
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["G4"],
                __NOTES["EB4"],
                0,
                __NOTES["BB4"],
                __NOTES["G4"],
                __NOTES["EB4"],
                0,
                __NOTES["BB4"],
                __NOTES["G4"],
                0,
                __NOTES["D4"],
                __NOTES["D4"],
                __NOTES["D4"],
                __NOTES["EB4"],
                0,
                __NOTES["BB3"],
                __NOTES["FS3"],
                __NOTES["EB3"],
                0,
                __NOTES["BB3"],
                __NOTES["G3"],
                0,
                __NOTES["G4"],
                0,
                __NOTES["G3"],
                __NOTES["G3"],
                0,
                __NOTES["G4"],
                0,
                __NOTES["FS4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["EB4"],
                __NOTES["E4"],
                0,
                __NOTES["GS3"],
                __NOTES["CS3"],
                0,
                __NOTES["C3"],
                __NOTES["B3"],
                __NOTES["BB3"],
                __NOTES["A3"],
                __NOTES["BB3"],
                0,
                __NOTES["EB3"],
                __NOTES["FS3"],
                __NOTES["EB3"],
                __NOTES["FS3"],
                __NOTES["BB3"],
                0,
                __NOTES["G3"],
                __NOTES["BB3"],
                __NOTES["D4"],
                0,
                __NOTES["G4"],
                0,
                __NOTES["G3"],
                __NOTES["G3"],
                0,
                __NOTES["G4"],
                0,
                __NOTES["FS4"],
                __NOTES["F4"],
                __NOTES["E4"],
                __NOTES["EB4"],
                __NOTES["E4"],
                0,
                __NOTES["GS3"],
                __NOTES["CS3"],
                0,
                __NOTES["C3"],
                __NOTES["B3"],
                __NOTES["BB3"],
                __NOTES["A3"],
                __NOTES["BB3"],
                0,
                __NOTES["EB3"],
                __NOTES["FS3"],
                __NOTES["EB3"],
                __NOTES["BB3"],
                __NOTES["G3"],
                __NOTES["EB3"],
                0,
                __NOTES["BB3"],
                __NOTES["G3"],
            ],
            "tempo": [
                2,
                2,
                2,
                4,
                8,
                6,
                2,
                4,
                8,
                6,
                2,
                8,
                2,
                2,
                2,
                4,
                8,
                6,
                2,
                4,
                8,
                6,
                2,
                8,
                2,
                16,
                4,
                4,
                8,
                2,
                8,
                4,
                6,
                6,
                4,
                4,
                8,
                4,
                2,
                8,
                4,
                4,
                6,
                4,
                2,
                8,
                4,
                2,
                4,
                4,
                2,
                8,
                4,
                6,
                2,
                8,
                2,
                16,
                4,
                4,
                8,
                2,
                8,
                4,
                6,
                6,
                4,
                4,
                8,
                4,
                2,
                8,
                4,
                4,
                6,
                4,
                2,
                8,
                4,
                2,
                2,
                4,
                2,
                4,
                8,
                4,
                2,
            ],
            "pause": 0.50,
            "pace": 1.000,
        },
        "Super Mario": {
            "melody": [
                __NOTES["E7"],
                __NOTES["E7"],
                0,
                __NOTES["E7"],
                0,
                __NOTES["C7"],
                __NOTES["E7"],
                0,
                __NOTES["G7"],
                0,
                0,
                0,
                __NOTES["G6"],
                0,
                0,
                0,
                __NOTES["C7"],
                0,
                0,
                __NOTES["G6"],
                0,
                0,
                __NOTES["E6"],
                0,
                0,
                __NOTES["A6"],
                0,
                __NOTES["B6"],
                0,
                __NOTES["AS6"],
                __NOTES["A6"],
                0,
                __NOTES["G6"],
                __NOTES["E7"],
                __NOTES["G7"],
                __NOTES["A7"],
                0,
                __NOTES["F7"],
                __NOTES["G7"],
                0,
                __NOTES["E7"],
                0,
                __NOTES["C7"],
                __NOTES["D7"],
                __NOTES["B6"],
                0,
                0,
                __NOTES["C7"],
                0,
                0,
                __NOTES["G6"],
                0,
                0,
                __NOTES["E6"],
                0,
                0,
                __NOTES["A6"],
                0,
                __NOTES["B6"],
                0,
                __NOTES["AS6"],
                __NOTES["A6"],
                0,
                __NOTES["G6"],
                __NOTES["E7"],
                __NOTES["G7"],
                __NOTES["A7"],
                0,
                __NOTES["F7"],
                __NOTES["G7"],
                0,
                __NOTES["E7"],
                0,
                __NOTES["C7"],
                __NOTES["D7"],
                __NOTES["B6"],
                0,
                0,
            ],
            "tempo": [
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                9,
                9,
                9,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                9,
                9,
                9,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
                12,
            ],
            "pause": 1.30,
            "pace": 0.800,
        },
    }

    def __play(self, song):
        def buzz(frequency, length):  # create the function "buzz" and feed it the pitch and duration)
            if frequency == 0:
                sleep(length)
                return

            period = 1.0 / frequency  # in physics, the period (sec/cyc) is the inverse of the frequency (cyc/sec)
            delayValue = period / 2.0  # calculate the time for half of the wave
            numCycles = int(length * frequency)  # the number of waves to produce is the duration times the frequency

            for _ in range(numCycles):  # start a loop from 0 to the variable "cycles" calculated above
                self.setup["buzzer"].on()
                sleep(delayValue)  # wait with pin 27 high
                self.setup["buzzer"].off()
                sleep(delayValue)  # wait with pin 27 low

        if self._playing or song not in self.__SONGS:
            return False

        self._playing = True
        for i in range(0, len(self.__SONGS[song]["melody"])):  # Play song
            noteDuration = self.__SONGS[song]["pace"] / self.__SONGS[song]["tempo"][i]
            buzz(self.__SONGS[song]["melody"][i], noteDuration)  # Change the frequency along the song note

            pauseBetweenNotes = noteDuration * self.__SONGS[song]["pause"]
            sleep(pauseBetweenNotes)

            if not self._playing:
                break

        self._playing = False

    def load_setup(self, setup_data):
        self._playing = False
        self._player = None
        self.setup = {
            "buzzer": (
                None
                if setup_data.get("address") is None
                else LED(terrariumUtils.to_BCM_port_number(setup_data.get("address")))
            )
        }

        super().load_setup(setup_data)
        # Startup song :P
        # self.send_message(None, 'Popcorn', None)

    def send_message(self, type, subject, message, data=None, attachments=[]):
        if self._playing or self.setup["buzzer"] is None:
            return

        for song in self.__SONGS:
            if song.lower() == subject.lower():
                self._player = Thread(target=self.__play, args=(song,))
                self._player.start()
                break

    def stop(self):
        self._playing = False
        if self._player is not None:
            self._player.join()

        if self.setup["buzzer"] is not None:
            self.setup["buzzer"].off()


class terrariumNotificationServiceMQTT(terrariumNotificationService):
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f'Logged in to MQTT Broker at address: {self.setup["address"]}:{self.setup["port"]}.')

        else:
            logger.error(
                f'Error! Login to MQTT Broker at address: {self.setup["address"]}:{self.setup["port"]} failed! Error code: {rc}'
            )
            self.stop()

    def load_setup(self, setup_data):
        self.setup = {
            "address": setup_data.get("address"),
            "port": int(setup_data.get("port")),
            "username": setup_data.get("username"),
            "password": setup_data.get("password"),
            "ssl": setup_data.get("ssl", False),
        }

        super().load_setup(setup_data)

        self.connection = None

        if self.enabled:
            try:
                try:
                    # paho-mqtt >= 2.0.0
                    self.connection = mqtt.Client(
                        mqtt.CallbackAPIVersion.VERSION1, client_id=f"TerrariumPI {self.setup['version']}"
                    )
                except Exception:
                    # Old version
                    self.connection = mqtt.Client(client_id=f"TerrariumPI {self.setup['version']}")

                self.connection.on_connect = self.on_connect
                if self.setup["ssl"]:
<target>
                    self.connection.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
</target>
                self.connection.username_pw_set(self.setup["username"], self.setup["password"])
                self.connection.connect(self.setup["address"], self.setup["port"], 30)
                self.connection.loop_start()
                logger.info(f'Connecting to MQTT Broker at address: {self.setup["address"]}:{self.setup["port"]} ...')

            except Exception as ex:
                logger.warning(
                    f'Failed connecting to MQTT Broker at address: {self.setup["address"]}:{self.setup["port"]}: {ex}'
                )

    def stop(self):
        # TODO: Flush the queue

        if self.connection is not None:
            try:
                self.connection.loop_stop()
            except Exception as ex:
                logger.error(f"Error stopping MQTT broker: {ex}")

            self.connection.disconnect()
            self.connection = None

        logger.info(f'Disconnected from the MQTT Broker at address: {self.setup["address"]}:{self.setup["port"]}')

    def send_message(self, type, subject, message, data=None, attachments=[]):
        topic = type.replace("_", "/")
        topic = f"terrariumpi/{topic}"

        if data is None:
            data = {}

        if "id" in data:
            topic = f'{topic}/{data["id"]}'

        # Add a unique ID to make clients able to filter duplicate messages
        data["uuid"] = terrariumUtils.generate_uuid()
        # Add the 'direct' topic to subscribe to
        data["topic"] = topic
        # Add the subject
        data["subject"] = subject
        # Add the message
        data["message"] = message
        if "now" in data:
            data["now"] = data["now"].strftime("%c")

        if self.connection is not None:
            self.connection.publish(topic, payload=json.dumps(data), qos=1)
        else:
            logger.error(
                f'Could not send message {data["subject"]} to topic {data["topic"]} as we are not connected to the MQTT broker at address: {self.setup["address"]}:{self.setup["port"]}'
            )


class terrariumNotificationServicePushover(terrariumNotificationService):
    def load_setup(self, setup_data):
        self.setup = {
            "api_token": setup_data.get("api_token"),
            "user_key": setup_data.get("user_key"),
            "address": "https://api.pushover.net/1/messages.json",  # https://support.pushover.net/i44-example-code-and-pushover-libraries#python-image
        }

        super().load_setup(setup_data)

    def send_message(self, type, subject, message, data=None, attachments=[]):
        data = {"token": self.setup["api_token"], "user": self.setup["user_key"], "title": subject, "message": message}

        if "system_error" == type:
            data["sound"] = "siren"

        attachment = None
        try:
            if len(attachments) > 0:
                attachment = {
                    "attachment": (os.path.basename(attachments[0]), open(attachments[0], "rb"), "image/jpeg")
                }
        except FileNotFoundError:
            pass

        r = requests.post(self.setup["address"], data=data, files=attachment)

        if r.status_code != 200:
            logger.error(f"Error sending Pushover message '{subject}' with status code: {r.status_code}")


class terrariumNotificationServiceTelegram(terrariumNotificationService):
    # function to handle the /start command
    async def start(self, update, context):
        if await self._authenticate(update.message):
            if update.message.chat_id not in self.setup["chat_ids"]:
                self.setup["chat_ids"].append(update.message.chat_id)

                # Store chat id in database for reconnecting after a restart
                with orm.db_session():
                    service = NotificationService[self.id]
                    if not service.state:
                        service.state = {}

                    service.state["chat_ids"] = self.setup["chat_ids"]

                await update.message.reply_text("start command received, you are now getting updates...")
            else:
                await update.message.reply_text("running...")

    async def webcamSelect(self, update, context):
        if await self._authenticate(update.message):
            webcam_id = None
            if update.message.parse_entities("bot_command"):
                try:
                    webcam_id = update.message.text.strip().split(" ")[1]
                except:
                    logger.debug("No webcam ID given, will return the webcam list.")

            else:
                webcam_id = update.message.text.strip().split(" ")[0]
                await update.message.reply_text(webcam_id)

            if webcam_id is None:
                webcam_list = [
                    InlineKeyboardButton(webcam.name, callback_data=f"{webcam.id},{webcam.name}")
                    for webcam in self.engine.webcams.values()
                ]

                if len(webcam_list) == 0:
                    await update.message.reply_text("No webcams configured")

                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Select a webcam from the list:",
                        reply_markup=InlineKeyboardMarkup([webcam_list]),
                    )
                    return 0

            elif webcam_id in self.engine.webcams:
                await self.webcam(update, context, webcam_id)

            else:
                for webcam in self.engine.webcams.values():
                    if webcam_id == webcam.name:
                        return await self.webcam(update, context, webcam.id)

                await update.message.reply_text(f"Webcam {webcam_id} does not exist!")

        return ConversationHandler.END

    async def webcam(self, update, context, webcam_id=None):
        if webcam_id is None:
            query = update.callback_query
            await query.answer()
            webcam_id, webcam_name = query.data.split(",")
            await query.edit_message_text(text=f"Webcam: {webcam_name}")

        with open(self.engine.webcams[webcam_id].raw_image_path, "rb") as webcam_image:
            await context.bot.send_photo(update.effective_chat.id, webcam_image)

        return ConversationHandler.END

    async def sensor(self, update, context):
        if await self._authenticate(update.message):
            query_message = await update.message.reply_text("Loading sensor(s)...")
            sensor_ids = None
            try:
                sensor_ids = update.message.text.strip().split(" ")[1]
            except:
                logger.debug("No sensor ID given, will return all sensors.")

            sensor_ids = (
                [sensor_ids] if sensor_ids and sensor_ids in self.engine.sensors else self.engine.sensors.keys()
            )

            message = ["Current sensor(s) status:"]
            with orm.db_session():
                for sensor in Sensor.select(lambda s: s.id in sensor_ids).order_by(Sensor.name):
                    message.append(
                        f"- Sensor {sensor.name} is currently at {sensor.value}{self.engine.units[sensor.type]}"
                    )

            await query_message.edit_text("\n".join(message))

    async def relay(self, update, context):
        if await self._authenticate(update.message):
            query_message = await update.message.reply_text("Loading relay(s)...")
            relay_ids = None
            try:
                relay_ids = update.message.text.strip().split(" ")[1]
            except:
                logger.debug("No sensor ID given, will return all sensors.")

            relay_ids = [relay_ids] if relay_ids and relay_ids in self.engine.relays else self.engine.relays.keys()

            message = ["Current relay(s) status:"]
            with orm.db_session():
                for relay in Relay.select(lambda r: r.id in relay_ids).order_by(Relay.name):
                    if "dimmer" in relay.hardware:
                        message.append(f"- Relay {relay.name} is currently at {relay.value}%")
                    else:
                        message.append(f"- Relay {relay.name} is currently at {'ON' if bool(relay.value) else 'OFF'}")

            await query_message.edit_text("\n".join(message))

    async def button(self, update, context):
        if await self._authenticate(update.message):
            query_message = await update.message.reply_text("Loading button(s)...")
            button_ids = None
            try:
                button_ids = update.message.text.strip().split(" ")[1]
            except:
                logger.debug("No button ID given, will return all buttons.")

            button_ids = (
                [button_ids] if button_ids and button_ids in self.engine.buttons else self.engine.buttons.keys()
            )

            message = ["Current button(s) status:"]
            with orm.db_session():
                for button in Button.select(lambda r: r.id in button_ids).order_by(Button.name):
                    # TODO: Change message based on button type. Movement, and light
                    message.append(f"- button {button.name} is {'Close' if bool(button.value) else 'Open'}")

            await query_message.edit_text("\n".join(message))

    async def status(self, update, context):
        if await self._authenticate(update.message):
            query_message = await update.message.reply_text("Loading...")
            system_stats = self.engine.system_stats()

            message = ["System stats:"]
            message.append(f"- Uptime: {datetime.timedelta(seconds=int(system_stats['uptime']))}")
            message.append(f"- Load: {system_stats['load']['percentage'][0]} %")
            message.append(f"- CPU temperature: {system_stats['cpu_temperature']:.2f} ºC")
            message.append(
                f"- Memory: {(system_stats['memory']['used']/1048576):.2f} MB ({((system_stats['memory']['used']*100)/system_stats['memory']['total']):.2f}%)"
            )
            message.append(
                f"- Storage: {(system_stats['storage']['used']/1073741824):.2f} GB ({((system_stats['storage']['used']*100)/system_stats['storage']['total']):.2f}%)"
            )

            await query_message.edit_text("\n".join(message))

    async def enclosure(self, update, context):
        if await self._authenticate(update.message):
            enclosure_id = None
            if update.message.parse_entities("bot_command"):
                try:
                    enclosure_id = update.message.text.strip().split(" ")[1]
                except:
                    logger.debug("No enclosure ID given, will return the enclosure list.")

            else:
                enclosure_id = update.message.text.strip().split(" ")[0]
                await update.message.reply_text(enclosure_id)

            if enclosure_id is None:
                enclosure_list = [
                    InlineKeyboardButton(enclosure.name, callback_data=f"{enclosure.id},{enclosure.name}")
                    for enclosure in self.engine.enclosures.values()
                ]

                if len(enclosure_list) == 0:
                    await update.message.reply_text("No enclosure configured")

                elif len(enclosure_list) == 1:
                    await self.area(update, context, list(self.engine.enclosures.keys())[0])

                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Select a enclosure from the list:",
                        reply_markup=InlineKeyboardMarkup([enclosure_list]),
                    )
                    return 0

            elif enclosure_id in self.engine.enclosure:
                await self.area(update, context, enclosure_id)

            else:
                await update.message.reply_text(f"Enclosure {enclosure_id} does not exist!")

        return ConversationHandler.END

    async def area(self, update, context, enclosure_id=None):
        if enclosure_id is None:
            query = update.callback_query
            await query.answer()
            enclosure_id, enclosure_name = query.data.split(",")
            query_message = query.message
            await query_message.edit_text(f"Enclosure: {enclosure_name} \nLoading area(s)...")
        else:
            query_message = await update.message.reply_text("Loading area(s)...")

        message = [f"Enclosure {self.engine.enclosures[enclosure_id].name} current area(s) status:"]

        for area in self.engine.enclosures[enclosure_id].areas.values():
            if area.mode == "sensors":
                message.append(f"- Area {area.name} type {area.type} => {'ON' if area.state['powered'] else 'OFF'}")
                message.append(
                    f"\t\tcurrent: \t{area.state['sensors']['current']:.2f} ({area.state['sensors']['alarm_min']:.2f} - {area.state['sensors']['alarm_max']:.2f})"
                )
            elif area.mode == "weather":
                message.append(f"- Area {area.name} type {area.type}")
                for period in ["day", "night", "low", "high"]:
                    try:
                        if area.state[period] and area.state[period]["begin"]:
                            message.append(
                                f"\t\t{period}: \t{datetime.datetime.fromtimestamp(area.state[period]['begin']):%H:%M} - {datetime.datetime.fromtimestamp(area.state[period]['end']):%H:%M} ({datetime.datetime.fromtimestamp(area.state[period]['duration']):%H} hours) => {'ON' if area.state[period]['powered'] else 'OFF'}"
                            )
                    except:
                        pass
            else:
                message.append(f"- Area {area.name} type {area.type} => {'ON' if area.state['powered'] else 'OFF'}")

        await query_message.edit_text("\n".join(message))

        return ConversationHandler.END

    async def help(self, update, context):
        if await self._authenticate(update.message):
            await update.message.reply_text(
                """The following commands are supported:

/start : This will start listening for notifications.
/webcam [webcam_id] : will show the latest image of the webcam ID.
/sensor [sensor_id] : will show the current sensor state. Sensor id is optional.
/relay [relay_id] : will show the current relay state. Relay id is optional.
/button [button_id] : will show the current button state. button id is optional.
/enclosure [enclosure_id] : will show the current area state of the enclosure ID
/status : will show the current system status."""
            )

    # function to handle normal text
    async def text(self, update, context):
        if await self._authenticate(update.message):
            await update.message.reply_text("Sorry, no conversations...")

    # function to handle errors ocurred in the dispatcher
    async def error(self, update, context):
        if await self._authenticate(update.message):
            await update.message.reply_text("an error ocurred")

        return ConversationHandler.END

    async def _authenticate(self, message):
        if str(message.from_user.username) in self.setup["allowed_users"]:
            return True

        await message.reply_text(f"User is not allowed: {message.from_user.username}")
        logger.error(f"User is not allowed: {message.from_user.username}")

    async def _connect(self):
        try:
            await self.telegram_bot.initialize()
            await self.telegram_bot.start()
            logger.info("Connected to Telegram")
            await self.telegram_bot.updater.start_polling()
        except InvalidToken as ex:
            logger.error(f"Error starting Telegram bot: {ex}")

    async def _main_process(self):
        try:
            await self._connect()
        except TimedOut as ex:
            logger.warning(f"Error connecting to Telegram. Just retry once more: {ex}")
            try:
                await self._connect()
            except Exception as ex:
                logger.error(f"Error connecting to Telegram: {ex}")

    def load_setup(self, setup_data):
        def _run():
            try:
                self._async = terrariumAsync()
                self._async.run(self._main_process())
            except Exception as ex:
                logger.exception(f"Error in telegram service: {ex}")

        old_chat_ids = []
        if setup_data["state"] and "chat_ids" in setup_data["state"]:
            old_chat_ids = setup_data["state"]["chat_ids"]

        self.setup = {
            "token": setup_data.get("token"),
            "allowed_users": setup_data.get("allowed_users").split(","),
            "chat_ids": old_chat_ids,
        }

        super().load_setup(setup_data)

        self.telegram_bot = None
        self.__thread = None

        if self.enabled:
            self.telegram_bot = Application.builder().token(self.setup["token"]).build()

            # add handlers for start and help commands
            self.telegram_bot.add_handler(CommandHandler("start", self.start))
            self.telegram_bot.add_handler(CommandHandler("help", self.help))
            self.telegram_bot.add_handler(CommandHandler("sensor", self.sensor))
            self.telegram_bot.add_handler(CommandHandler("relay", self.relay))
            self.telegram_bot.add_handler(CommandHandler("button", self.button))
            self.telegram_bot.add_handler(CommandHandler("status", self.status))

            # add handlers for select options
            self.telegram_bot.add_handler(
                ConversationHandler(
                    entry_points=[CommandHandler("webcam", self.webcamSelect)],
                    states={0: [CallbackQueryHandler(self.webcam)]},
                    fallbacks=[CommandHandler("webcam", self.webcamSelect)],
                )
            )
            self.telegram_bot.add_handler(
                ConversationHandler(
                    entry_points=[CommandHandler("enclosure", self.enclosure)],
                    states={0: [CallbackQueryHandler(self.area)]},
                    fallbacks=[CommandHandler("enclosure", self.enclosure)],
                )
            )

            # add an handler for normal text (not commands)
            self.telegram_bot.add_handler(MessageHandler(filters.TEXT, self.text))

            # add an handler for errors
            self.telegram_bot.add_error_handler(self.error)

            try:
                self.__thread = Thread(target=_run)
                self.__thread.start()
            except Exception as ex:
                logger.exception(f"Error in Telegram run: {ex}")

            if len(old_chat_ids) > 0:
                self.send_message(None, "Reconnected", "TerrariumPI just restarted...")

    def stop(self):
        async def _stop():
            if self.telegram_bot is not None:
                try:
                    await self.telegram_bot.updater.stop()
                    await self.telegram_bot.stop()
                except Exception as ex:
                    logger.error(f"Error stopping Telegram bot: {ex}")
                finally:
                    await self.telegram_bot.shutdown()

                self.telegram_bot = None

        self._async.run(_stop())

        if self.__thread is not None:
            self.__thread.join()

        logger.info("Disconnected from Telegram")

    def send_message(self, _, subject, message, data=None, attachments=[]):
        async def _send_message(subject, message, data=None, attachments=[]):
            message = f"<b><u>{subject}</u></b>\n{message}"

            text_mode = len(attachments) == 0

            for chat_id in self.setup["chat_ids"]:
                if text_mode:
                    await self.telegram_bot.bot.send_message(chat_id, message, parse_mode="HTML")
                else:
                    for image in attachments:
                        with open(image, "rb") as image:
                            await self.telegram_bot.bot.send_photo(chat_id, image)

        self._async.run(_send_message(subject, message, data, attachments))