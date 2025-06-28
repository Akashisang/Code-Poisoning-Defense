#!env /usr/bin/python
"""Access the elk M1 via the ethernet XEP module.

When an alarm state changes, requests the zone that changed.

Loosly based on the elkm1.py code from:

https://github.com/sbelectronics/pi-controller
"""

import ast
import csv
import logging
import socket
import ssl
import sys
import time
import traceback

import gmailer
import sql_access

# Whether or not the alarm is armed and if so
# which of the various armed states (away, night, vacation, etc)
DISARM = 0
ARM_AWAY = 1
ARM_STAY = 2
ARM_STAY_INSTANT = 3
ARM_NIGHT = 4
ARM_NIGHT_INSTANT = 5
ARM_VACATION = 6
ARM_NEXT_AWAY = 7
ARM_NEXT_STAY = 8

ARM_STATE = {
    DISARM: "disarm",
    ARM_AWAY: "away",
    ARM_STAY: "stay",
    ARM_STAY_INSTANT: "stay instant",
    ARM_NIGHT: "night",
    ARM_NIGHT_INSTANT: "night instant",
    ARM_VACATION: "vacation",
    ARM_NEXT_AWAY: "next away",
    ARM_NEXT_STAY: "next stay",
}

# state for a whole area
ARM_UP_NOT_READY = 0
ARM_UP_READY = 1
ARM_UP_READY_FORCE = 2
ARM_UP_EXIT = 3
ARM_UP_FULLY = 4
ARM_UP_FORCE = 5
ARM_UP_BYPASS = 6

AREA_STATE = {
    ARM_UP_NOT_READY: "not ready",
    ARM_UP_READY: "ready",
    ARM_UP_READY_FORCE: "ready force",
    ARM_UP_EXIT: "exit",
    ARM_UP_FULLY: "fully",
    ARM_UP_FORCE: "force",
    ARM_UP_BYPASS: "bypass",
}

# ?If an area is armed (or stay or vacation or ???, basically
# not disarmed), then this indicates why an alarm is going
# off, or inactive if no alarm is going off...?

# Area alarm types
# And a reminder, inactive does not mean bypassed or
# disabled. So can't look at a zone, see inactive and assume
# that means there is no sensor there.
ALARM_INACTIVE = "0"
ALARM_ENTRACE_DELAY = "1"
ALARM_ABORT_DELAY = "2"
ALARM_FIRE = "3"
ALARM_MEDICAL = "4"
ALARM_POLICE = "5"
ALARM_BURGLAR = "6"
ALARM_AUX1 = "7"
ALARM_AUX2 = "8"
ALARM_AUX3 = "9"
ALARM_AUX4 = ":"
ALARM_CO = ";"
ALARM_EMERGENCY = "<"
ALARM_FREEZE = "="
ALARM_GAS = ">"
ALARM_HEAT = "?"
ALARM_WATER = "@"
ALARM_FIRESUPER = "A"
ALARM_FIREVERIFY = "B"

ALARM_TYPE = {
    ALARM_INACTIVE: "inactive",
    ALARM_ENTRACE_DELAY: "entrance delay",
    ALARM_ABORT_DELAY: "abort delay",
    ALARM_FIRE: "fire",
    ALARM_MEDICAL: "medical",
    ALARM_POLICE: "police",
    ALARM_BURGLAR: "burglar",
    ALARM_AUX1: "aux1",
    ALARM_AUX2: "aux2",
    ALARM_AUX3: "aux3",
    ALARM_AUX4: "aux4",
    ALARM_CO: "carbon monoxide",
    ALARM_EMERGENCY: "emergency",
    ALARM_FREEZE: "freeze",
    ALARM_GAS: "gas",
    ALARM_HEAT: "heat",
    ALARM_WATER: "water",
    ALARM_FIRESUPER: "fire supervisory",
    ALARM_FIREVERIFY: "fire verify",
}

# Zone status is a hex value, convert to int
# and use here
ZONE_STATUS_NORMAL_UNC = 0x0
ZONE_STATUS_NORMAL_OPEN = 0x1
ZONE_STATUS_NORMAL_EOL = 0x2
ZONE_STATUS_NORMAL_SHORT = 0x3
ZONE_STATUS_NOT_USED_1 = 0x4
ZONE_STATUS_TROUBLE_OPEN = 0x5
ZONE_STATUS_TROUBLE_EOL = 0x6
ZONE_STATUS_TROUBLE_SHORT = 0x7
ZONE_STATUS_NOT_USED_2 = 0x8
ZONE_STATUS_VIOLATED_OPEN = 0x9
ZONE_STATUS_VIOLATED_EOL = 0xA
ZONE_STATUS_VIOLATED_SHORT = 0xB
ZONE_STATUS_NOT_USED_3 = 0xC
ZONE_STATUS_BYPASSED_OPEN = 0xD
ZONE_STATUS_BYPASSED_EOL = 0xE
ZONE_STATUS_BYPASSED_SHORT = 0xF

ZONE_STATUS = {
    ZONE_STATUS_NORMAL_UNC: "unconfigured",
    ZONE_STATUS_NORMAL_OPEN: "normal open",
    ZONE_STATUS_NORMAL_EOL: "normal eol",
    ZONE_STATUS_NORMAL_SHORT: "normal short",
    ZONE_STATUS_NOT_USED_1: "unused1",
    ZONE_STATUS_TROUBLE_OPEN: "trouble open",
    ZONE_STATUS_TROUBLE_EOL: "trouble eol",
    ZONE_STATUS_TROUBLE_SHORT: "trouble short",
    ZONE_STATUS_NOT_USED_2: "unused2",
    ZONE_STATUS_VIOLATED_OPEN: "violated open",
    ZONE_STATUS_VIOLATED_EOL: "violated eol",
    ZONE_STATUS_VIOLATED_SHORT: "violated short",
    ZONE_STATUS_NOT_USED_3: "unused3",
    ZONE_STATUS_BYPASSED_OPEN: "bypassed open",
    ZONE_STATUS_BYPASSED_EOL: "bypassed eol",
    ZONE_STATUS_BYPASSED_SHORT: "bypassed short",
}

# Sensor use/definition
# Entry was door enter/exit delay related
# perimeter seemed like immediate alarm when night, stay, vacation
# interior was used for motion sensors
# Water sensors 
SENSOR_UNKNOWN = 0
SENSOR_ENTRY_1 = 1
SENSOR_ENTRY_2 = 2
SENSOR_PERIMETER = 3
SENSOR_INTERIOR = 4
SENSOR_WATER = 25

# Send an email for sensors defined as...
WANT_EMAIL = set(
    [SENSOR_ENTRY_1, SENSOR_ENTRY_2, SENSOR_PERIMETER, SENSOR_WATER]
    )

# Sensor type
# 0 was contact sensor of some sort (on/off which included motion)
# 2 was water. Don't know what the others were.

ZONE_UNKNOWN = -1
COMMAND_UNKNOWN = -1


DEFAULT_IP = "192.168.1.2"
DEFAULT_PORT = 2601
DEFAULT_CODE = 0000

VERSION_REQ = "vn"
VERSION_RESP = "VN"
COMMAND_VERSION = -2

LOG_REQ = "ld"
LOG_RESP = "LD"
COMMAND_LOG = -3

ALARM_BY_ZONE_REQ = "az"
ALARM_BY_ZONE_RESP = "AZ"
COMMAND_ALARM_BY_ZONE = -4

ZONE_CHANGED_RESP = "ZC"

ARM_STATUS_REQ = "as"
ARM_STATUS_RESP = "AS"
COMMAND_ARM = -5

XEP_REQ = "xk"
XEP_RESP = "XK"
COMMAND_XEP = -6


class ElkAccess(object):
  def __init__(self, address=None, port=None):
    f = open("elkrc","r")
    setup = "".join(f.readlines())
    f.close()
    logging.debug("elkrc: %s", setup)

    # elkrc is a textual python dictionary, so safely parse it
    # and turn it into an actual dictionary.
    self.values = ast.literal_eval(setup)
    logging.debug("values: %s", self.values)

    # must have a username and password
    self.username = self.values["username"]
    self.password = self.values["password"]

    # but other things are optional
    self.code = self.values.get("code", DEFAULT_CODE)

    # passed in values override elkrc values
    if address:
      self.address = address
    else:
      self.address = self.values.get("address", DEFAULT_IP)

    if port:
      self.port = port
    else:
      self.port = int(self.values.get("port", DEFAULT_PORT))

    # if the elkrc file has an email account and email password
    # then enable sending emails when appropriate
    email = self.values.get("email_from", None)
    epassword = self.values.get("email_password", None)
    email_to = self.values.get("email_to", None)
    if email and epassword and email_to:
      self.mailer = gmailer.Gmailer(email, epassword)
      self.email_to = email_to
      logging.info("Email setup from: %s to: %s", email, email_to)
    else:
      self.mailer = None
      self.email_to = None
      logging.warning("Email is not setup")

    self.socket_connected = False
    self.seen_connected = False
    self.sent_password = False
    self.buf = ""
    if address is not None:
      self.connect()

    self.zones_info = {}
    self.zones = {}
    # Get the zone information.
    with open("AlarmZoneInfo.csv", "r") as f:
      csvr = csv.DictReader(f)
      for row in csvr:
        zone = int(row["Zone"])
        desc = row["Description"]
        d = int(row["Definition"])
        t = int(row["Type"])
        zone_info = {
          "zone": zone,
          "description": desc,
          "definition": d,
          "type": t,
        }
        self.zones_info[zone] = zone_info
        self.zones[zone] = desc
    self.sql = sql_access.SaveToSql()
    self.armed = -1
    self.armup = -1
    self.alarm = ""

  def Connect(self):
    self.socket_connected = False
    self.seen_connected = False
    self.sent_password = False
    self.buf = ""
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.s = ssl.wrap_socket(self.s, ssl_version=ssl.PROTOCOL_TLSv1)
    self.s.connect((self.address, self.port))
    self.socket_connected = True

  def Connected(self):
    pass

  def CalcChecksum(self, msg):
    chk = 0
    for x in msg:
      chk = (chk + ord(x)) & 0xFF;
    chk = 0x100 - chk
    return "%02X" % chk

  def SendUserame(self):
    logging.info("sending username: %s", self.username)
    self.s.write("%s\015\012" % self.username)

  def SendPassword(self):
    logging.info("sending password: %s", self.password)
    self.s.write("%s\015\012" % self.password)
    self.sent_password = True

  def StdTime(self, now_ms):
    t = time.localtime(now_ms / 1000.0)
    return time.strftime("%a_%Y%m%d_%H%M%S", t)

  def VersionRequest(self):
    pkt = "06vn00"
    pkt = pkt + self.CalcChecksum(pkt)
    return pkt + "\015\012"

  def ParseVersionResponse(self, now_ms, msg_len, msg_type, sentence):
    if msg_len != "36":
      logging.error("Xep alive had wrong lenght: %s", msg_len)
      return
    m1_major = sentence[4:6]
    m1_minor = sentence[6:8]
    m1_release = sentence[8:10]

    xep_major = sentence[10:12]
    xep_minor = sentence[12:14]
    xep_release = sentence[14:16]
    self.sql.CreateIfNeeded()
    self.sql.StoreZone(
        now_ms, ZONE_UNKNOWN, COMMAND_VERSION, SENSOR_UNKNOWN,
            self.armed, self.armup, self.alarm, sentence)

    s = "%s m1: %s.%s.%s  xep: %s.%s.%s" % (
        self.StdTime(now_ms),
        m1_major, m1_minor, m1_release, xep_major, xep_minor, xep_release)
    return s

  def ArmStateRequest(self):
    pkt = "06as00"
    pkt = pkt + self.CalcChecksum(pkt)
    return pkt + "\015\012"

  def ParseArmState(self, now_ms, msg_len, msg_type, sentence):
    if len(sentence)<32:
      logging.error("arm state had wrong length: %s", msg_len)
      return

    arm_status = []
    for s in sentence[4:12]:
      arm_status.append(ARM_STATE.get(int(s), "unknown"))
    old_armed = self.armed
    self.armed = int(sentence[4])

    if old_armed != self.armed:
      msg = "Arming state has changed for area zero: %s (%d) -> %s (%d)" % (
          ARM_STATE.get(old_armed, "unknown"),  old_armed,
          ARM_STATE.get(self.armed, "unknown"), self.armed)
      logging.warning(msg)
      if self.mailer:
        subject = "arm state: %s" % arm_status[0]
        self.mailer.SendEmail(self.email_to, subject, msg)
        logging.info("email sent: <%s> <%s>", subject, msg)

    arm_up = []
    for s in sentence[12:20]:
      arm_up.append(AREA_STATE.get(int(s), "unknown"))
    self.armup = int(sentence[12])

    alarm_state = []
    for s in sentence[20:28]:
      alarm_state.append(ALARM_TYPE.get(s, "unknown"))
    # Not an int or hex value, a character
    self.alarm = sentence[20]

    if self.alarm > ALARM_INACTIVE:
      msg = "Alarm triggered for area zero: %s (%s)" % (
          alarm_state[0], self.alarm)
      logging.warning(msg)
      if self.mailer:
        subject = "alarm triggered: %s" % alarm_state[0]
        self.mailer.SendEmail(self.email_to, subject, msg)
        logging.info("email sent: <%s> <%s>", subject, msg)


    self.sql.CreateIfNeeded()
    self.sql.StoreZone(
        now_ms, ZONE_UNKNOWN, COMMAND_ARM, SENSOR_UNKNOWN,
            self.armed, self.armup, self.alarm, sentence)
    d = {
      "area arm_status": arm_status,
      "area arm_up": arm_up,
      "area alarm_state": alarm_state,
    }
    return repr(d)

  def ParseXep(self, now_ms, msg_len, msg_type, sentence):
    if msg_len != "16":
      logging.error("Xep alive had wrong lenght: %s", msg_len)
      return
    seconds = sentence[4:6]
    minutes = sentence[6:8]
    hours = sentence[8:10]
    dow = sentence[10]
    day = sentence[11:13]
    month = sentence[13:15]
    year = sentence[15:17]
    dst = sentence[17]
    mode = sentence[18]
    disp = sentence[19]
    self.sql.CreateIfNeeded()
    self.sql.StoreZone(
        now_ms, ZONE_UNKNOWN, COMMAND_XEP, SENSOR_UNKNOWN,
            self.armed, self.armup, self.alarm, sentence)

    s = "%s %s/%s/%s %s:%s:%s dow: %s dst: %s mode: %s disp: %s" % (
        self.StdTime(now_ms),
        month, day, year, hours, minutes, seconds,
        dow, dst, mode, disp)
    return s

  def AlarmByZoneRequest(self):
    pkt = "06az00"
    pkt = pkt + self.CalcChecksum(pkt)
    return pkt + "\015\012"

  def ParseAlarmByZone(self, now_ms, msg_len, msg_type, sentence):
    if msg_len != "D6":
      logging.error("zone had wrong length: %s", msg_len)
      return
    # last 2 characters are the checksum and 2 before that
    # are always 00
    zones = sentence[4:-4]
    if len(zones) != 208:
      logging.error("alarm zone had wrong number of zones: %d", len(zones))
      return
    r = []
    for i in xrange(len(zones)):
      z = zones[i]
      desc = ALARM_TYPE.get(z, "unknown")
      r.append("%03d: %s (%s)" % (i, desc, z))

    # persist for later viewing.
    self.sql.CreateIfNeeded()
    self.sql.StoreZone(
        now_ms, ZONE_UNKNOWN, COMMAND_ALARM_BY_ZONE, SENSOR_UNKNOWN,
            self.armed, self.armup, self.alarm, sentence)
    return "%s %s" % (
      self.StdTime(now_ms), repr(r))
      
  def ParseZoneChanged(self, now_ms, msg_len, msg_type, sentence):
    if msg_len != "0A":
      logging.error("zone changed had wrong lenght: %s", msg_len)
      return

    zone = int(sentence[4:7])
    # status is a hex byte - convert that to an int...
    status = int(sentence[7], 16)

    vals = self.zones_info[zone]
    sensor_def = vals["definition"]

    # Persist to sql
    self.sql.CreateIfNeeded()
    self.sql.StoreZone(now_ms, zone, status, sensor_def,
            self.armed, self.armup, self.alarm, sentence)

    desc = vals["description"]
    when = self.StdTime(now_ms)

    # for now, status 1, 2, 3 means closed, all else means opened
    # and see how that works out...
    if status < ZONE_STATUS_NOT_USED_1:
      changed = "closed"
    else:
      changed = "opened"

    # And generate an email if we can (and desired)
    # Assumption, emails won't spam the gmail server...
    # may want to validate that assumption and queue up
    # emails in the future (to allow for a batch send of all messages
    # in the last N seconds.
    if self.mailer and (sensor_def in WANT_EMAIL):
      body = "<%s> (%03d) changed to %s (0x%x) at %s" % (
          desc, zone, changed, status, when)
      subject = "alarm <%s> %s" % (desc, changed)
      self.mailer.SendEmail(self.email_to, subject, body)
      logging.info("email sent: <%s> <%s>", subject, body)

    # and send back for printing
    return "%s zone: <%s> (%03d) status: %s ([%s] 0x%x)" % (
        when, desc, zone, changed, ZONE_STATUS[status], status)

  def ReadSentence(self, sentence):
    # now as milliseconds since blah blah
    now_ms = int(time.time() * 1000)

    # strip <CR> and <LF>
    sentence = sentence[:-2]
    logging.info("sentence: %s", sentence)
    if len(sentence) < 6:
        return

    if ((not self.seen_connected) and 
        (sentence.startswith("Elk-M1XEP: Login successful."))):
        # we saw a successful login message
        self.seen_connected = True
        self.Connected()

    msg_len = sentence[0:2]
    msg_type = sentence[2:4]
    if msg_type == ARM_STATUS_RESP:
      out = self.ParseArmState(now_ms, msg_len, msg_type, sentence)
    elif msg_type == XEP_RESP:
      out = self.ParseXep(now_ms, msg_len, msg_type, sentence)
    elif msg_type == ALARM_BY_ZONE_RESP:
      out = self.ParseAlarmByZone(now_ms, msg_len, msg_type, sentence)
    elif msg_type == ZONE_CHANGED_RESP:
      out = self.ParseZoneChanged(now_ms, msg_len, msg_type, sentence)
    elif msg_type == VERSION_RESP:
      out = self.ParseVersionResponse(now_ms, msg_len, msg_type, sentence)
    else:
      logging.warning("unexpected sentence: %s %s %s",
         msg_len, msg_type, sentence)
      out = None
      # Persist unexpect to sql
      self.sql.CreateIfNeeded()
      self.sql.StoreZone(
          now_ms, ZONE_UNKNOWN, COMMAND_UNKNOWN, SENSOR_UNKNOWN,
            self.armed, self.armup, self.alarm, sentence)

    if out:
      print "%d: %s" % (now_ms, out)

  def HandleOneBuffer(self):
    """Handle one buffer line and connect if necessary.

       Blocks while waiting to handle one buffer line.
       Will connect (or reconnect) if it is not already connected.

       Returns:
         None
    """
    # only way out is to be connected...
    while not self.socket_connected:
      try:
        logging.info("ELK: (re)connecting")
        self.Connect()
        logging.info("ELK: (re)connected")
      except Exception as e:
        logging.error("ELK: connection failed: %s", e)
        traceback.print_exc()
        # if we can't connect, delay for a bit and try again...
        time.sleep(1)

    try:
      self._BufferAndParse()
    except Exception as e:
      logging.error("ELK: exception in _BufferAndParse: %s", e)
      traceback.print_exc()
      logging.error("ELK: sleeping before reconnecting")

      # kill the connection in a polite (but immediate) way
      self.s.shutdown(socket.SHUT_RDWR)
      self.s.close()
      self.s = None
      self.socket_connected = False
      # let's not hammer the Elk too hard if there is a problem.
      time.sleep(30)

  def _BufferAndParse(self):
    """Read data from socket looking for end of line or keywords.

       Blocks until "enough" data has been read in.

       Once the data is found, it reacts to the data by sending
       stuff in response to the keyword (for example, sending
       a user name in response to seeing Username:) or parsing
       a response and handling it.

       Returns:
         None
    """
    data = self.s.read()
    for char in data:
      self.buf = self.buf + char
      if self.buf.endswith("Username:"):
        self.SendUserame()
        self.buf=""
      elif self.buf.endswith("Password:"):
        self.SendPassword()
        self.buf=""
      elif self.buf.endswith("\015\012"):
        self.ReadSentence(self.buf)
        self.buf=""

# Really want to do a more general purpose class that can send and respond
# to the elk instead of different classes for different sends
# but a common response (ie, not the current mechanism).
# So how to handle async data coming from elkd? Thread that just reads
# the socket and handles what is seen there?

class ElkArmStatePrinter(ElkAccess):
  def __init__(self, address=None, port=None):
    ElkAccess.__init__(self, address, port)

  def Connected(self):
    print "Connected"
    self.s.write(self.VersionRequest())
    self.s.write(self.AlarmByZoneRequest())
    self.s.write(self.ArmStateRequest())

def ChecksumTestPacket(pkt):
  correct_sum = pkt[-2:]
  pkt = pkt[:-2]

  chk = ElkAccess().CalcChecksum(pkt)
  if (correct_sum != chk):
    print "checksum test fail, pkt=%s, correct_sum=%s, calc_sum=%s" % (pkt, correct_sum, chk)

def ChecksumTest():
  ChecksumTestPacket("0DCV0100123003C")
  ChecksumTestPacket("08cv0100FE")
  ChecksumTestPacket("13TR01200726875000000")
  ChecksumTestPacket("11KF01C200000000087")
  ChecksumTestPacket("16KA12345678111111110081")

LOG_FORMAT = "%(levelname)0.1s:%(created)0.3f:%(message)s"
def main():
  logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
  elk = ElkArmStatePrinter()
  while True:
    elk.HandleOneBuffer()

if __name__ == "__main__":
  main()

# vim: ai:ts=2:sw=2:et
