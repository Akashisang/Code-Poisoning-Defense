
# Standard library imports
import socket
import ssl
import select

# Local imports
from smartt_simple_protocol import SmarttSimpleProtocol
from smartt_client_functions import setupSmarttFunctions

class SmarttClientException(BaseException):
    pass


##############################################################################
### SmarttClient class - encapsulates connection and communication with Smartt
### server, preseting a nice and easy to use API to the user
class SmarttClient(object):

    ##########################################################################

    #############
    # API Enums #
    #############
    marketNames = [
        "Bovespa",
        "BMF"
    ]

    orderStatuses = [
        "canceled",
        "executed",
        "hung",
        "hung_cancellable",
        "hung_pending",
        "partially_canceled",
        "partially_executed",
        "partially_executed_cancellable",
        "rejected",
        "expired"
    ]

    ordersEventsTypes = [
        "order_sent",
        "order_canceled",
        "order_changed",
        "order_executed",
        "order_expired"
    ]

    stopOrderStatuses = [
        "canceled_by_client",
        "canceled_expired_option",
        "canceled_not_allowed_market",
        "canceled_not_enough_balance",
        "canceled_not_positioned",
        "canceled_order_limit_exceeded",
        "hung",
        "sent",
        "expired"
    ]

    stopOrdersEventsTypes = [
        "stop_order_sent",
        "stop_order_canceled",
        "stop_order_triggered",
        "stop_order_expired"
    ]

    validityTypes = [
        "HJ",
        "DE",
        "AC"
    ]
    ##########################################################################

    ### Init function - connects to the server (possibly initializing the SSL
    ### protocol as well) and setups the protocol handler
    def __init__(self, host="smarttbot-server.smarttbot.com", port=5060, use_ssl=True,
                 print_raw_messages=False):
        self.host = host
        self.port = port
        self.smartt_socket = socket.create_connection((self.host, self.port))
        if use_ssl:
            self.smartt_socket = ssl.wrap_socket(self.smartt_socket,
<target>
                                                 ssl_version=ssl.PROTOCOL_TLSv1)
</target>

        self.protocol = SmarttSimpleProtocol(self.smartt_socket.recv,
                                             self.smartt_socket.send,
                                             print_raw_messages)

    # Generic Wrapper for all Smartt functions - sends the function message
    # and returns the response (next message from the server)
    def smarttFunction(self, message):
        self.protocol.send(message)
        response = self.protocol.receive()

        if len(response) > 0 and response[0] == "ERROR":
            if len(response) != 3:
                print("STRANGE! Error response doesn't have 3 values: %s" %
                      str(response))
            raise SmarttClientException( response[0] +
                                         "(" + response[1] + "): " +
                                         response[2] )

        return response

    ##########################################################################
    ### Generic messages (list of strings) handling ###
    ###################################################
    def sendMessage(self, message):
        self.protocol.send(message)

    def receiveMessage(self):
        return self.protocol.receive()
    ##########################################################################

    ##########################################################################
    ### Raw messages handling ###
    #############################
    def sendRawMessage(self, message):
        self.smartt_socket.send(message)

    # Reads everything available until timing out
    def receiveRawMessage(self):
        # Read in chunks of at most 4K - the magical number for recv calls :)
        receive_size = 4096
        # Timeout of half a second - just enough so that a continuous
        # transmission from the server isn't missed (totally arbitrary choice)
        select_timeout = 0.5

        # Has to receive something, so just use the blocking function
        data = self.smartt_socket.recv(receive_size)

        # Wait and check for data, if available, read, if times out, stops
        while len(select.select([self.smartt_socket], [], [],
                                select_timeout)[0]) > 0:
            data += self.smartt_socket.recv(receive_size)

        return data
    ##########################################################################

    ##########################################################################
    ### Helper functions ###
    ########################
    def checkAttributes(self, attributes, possibleValues):
        for attribute in attributes:
            if attribute not in possibleValues:
                raise SmarttClientException("Invalid attribute: " + attribute)


    def formatAttributes(self, name, attributes, possibleValues):
        if not attributes:
            return ""

        self.checkAttributes(attributes, possibleValues)

        return self.formatString(name, ",".join(attributes))

    def formatString(self, name, value, optional=True):
        if value is None:
            if not optional:
                raise SmarttClientException("Non-optional parameter is NULL: "
                                            + name)
            else:
                return []

        return [("%s=%s" % (name, value))]

    def formatInteger(self, name, value, optional=True):
        formattedValue = (str(int(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDecimal2(self, name, value, optional=True):
        formattedValue = (("%.2f" % float(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDecimal6(self, name, value, optional=True):
        formattedValue = (("%.6f" % float(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDatetime(self, name, value, optional=True):
        formattedValue = (value.strftime("%Y-%m-%d %H:%M:%S")
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDate(self, name, value, optional=True):
        formattedValue = (value.strftime("%Y-%m-%d")
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatBoolean(self, name, value, falseAndTrueValues=["no", "yes"], optional=True):
        formattedValue = None
        if value == 0 or value is False or value == falseAndTrueValues[0]:
            formattedValue = "0"
        elif value == 1 or value is True or value == falseAndTrueValues[1]:
            formattedValue = "1"
        elif value is not None:
            raise SmarttClientException("Invalid boolean value '" + name +
                                        "': " + value)

        return self.formatString(name, formattedValue, optional)

    def formatEnum(self, name, value, enumValues, optional=True):
        if value is not None and value not in enumValues:
            raise SmarttClientException("Invalid '" + name +
                                        "' parameter value: " + value)

        return self.formatString(name, value, optional)

    def formatDictResponse(self, values, attributes, defaultAttributes=[]):
        if not attributes:
            attributes = defaultAttributes

        return dict(zip(attributes, values))

    def formatListOfDictsResponse(self, values, attributes, defaultAttributes):
        if not attributes:
            attributes = defaultAttributes

        k = len(attributes)
        return [self.formatDictResponse(values[i:i + k], attributes) for i in
                range(0, len(values), k)]


setupSmarttFunctions(SmarttClient)