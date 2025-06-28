from __future__ import division
from __future__ import absolute_import
import json, socket, sys, os
import socket, ssl, re # Address validation
import pwd

from marcopolo.polo import conf
import six

from marcopolo.bindings.utils import verify_ip
from marcopolo.bindings.types import Service

BINDING_PORT = conf.POLO_BINDING_PORT

TIMEOUT = 4000

HOST, PORT = "127.0.0.1", BINDING_PORT

class Polo(object):
    def __init__(self, testing=False):
        self.polo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.polo_socket.settimeout(TIMEOUT/1000.0)
<target>
        self.wrappedSocket = ssl.wrap_socket(self.polo_socket, ssl_version=ssl.PROTOCOL_SSLv23)#, ciphers="ADH-AES256-SHA")
</target>
        error = False
        error_reason = ""
        if not testing:
            try:
                self.wrappedSocket.connect((HOST, PORT))
            except Exception as e:
                error = True
                error_reason = e
            if error is True:
                raise PoloInternalException(str(error_reason))

    def __del__(self):
        self.wrappedSocket.close()


    def get_token(self):
        pw_user = pwd.getpwuid(os.geteuid())

        if not os.path.isfile(os.path.join(pw_user.pw_dir, ".polo/token")):
            ok, error = self.request_token(pw_user)
            if error is not None:
                return ""

        try:
            with open(os.path.join(pw_user.pw_dir, ".polo/token")) as f:
                return f.read()
        except IOError:
            return ""

    def request_token(self, pw_user):
        
        if not os.path.isfile(os.path.join(pw_user.pw_dir, ".polo/token")):

            message_dict = {}
            message_dict["Command"] = "Request-token"
            message_dict["Args"] = {"uid":os.geteuid()}
            json_str = json.dumps(message_dict)
            self.wrappedSocket.send(json_str.encode('utf-8'))
            data = self.wrappedSocket.recv()
            

            data_dic = json.loads(data.decode('utf-8'))

            ok = data_dic.get("OK", None)
            error = data_dic.get("Error", None)
            
            return (ok, error)
        else:
            return ("", None)

    def publish_service(self, service, params={}, multicast_groups=conf.MULTICAST_ADDRS, permanent=False, root=False):
        """
        Registers a service during execution time. See :doc:`/services/intro/`.
        
        :param string service: Indicates the unique identifier of the service.
        
            If `root` is true, the published service will have the same identifier as the value of the parameter. Otherwise, the name of the user will be prepended (`<user>:<service>`).
        
        :param set multicast_groups: Indicates the groups where the service shall be published.
        
            Note that the groups must be defined in the polo.conf file, or otherwise the method will throw an exception.
        
        :param bool permanent: If set to true a file will be created and the service will be permanently offered until the file is deleted.
        
        :param bool root: Stores the file in the marcopolo configuration directory.
        
            This feature is only available to privileged users, by default root and users in the marcopolo group.
        
        :raise:
            :PoloException: Raised if the input is not valid (the message of the exception describes where the problem is)

            :PoloInternalException: Raised when internal problems occur. Such problems may be communication timeouts, malformed request/responses, encoding errors...
        
        :returns: The name of the service as offered. In case of `root` services, the name will be the value of `service`. If the service is a user service, it will be published as `username:service`
        
        :rvalue: str
        """

        token = self.get_token()

        
        error = False
        if not isinstance(service, six.string_types):
            raise PoloException("The name of the service %s is invalid" % service)

        if service is None or len(service) < 1:
            error = True

        if error:
            raise PoloException("The name of the service %s is invalid" % service)
        
        error = False
        faulty_ip = ""
        reason = ""
        for ip in multicast_groups:
            
            if not isinstance(ip, six.string_types):
                error = True
                faulty_ip = ip
                reason = "IP must be a string"
                break
            try:
                socket.inet_aton(ip)
            except socket.error:
                error = True
                faulty_ip = ip
                reason = "Wrong IP format"
                break
            try:
                first_byte = int(re.search("\d{3}", ip).group(0))
                if first_byte < 224 or first_byte > 239:
                    error = True
                    faulty_ip = ip
            except (AttributeError, ValueError):
                error = True
                faulty_ip = ip
                reason = "IP is not of class D"
                break

        if error:
            raise PoloException("Invalid multicast group address '%s': %s" % (str(faulty_ip), reason))

        if type(permanent) is not bool:
            raise PoloException("permanent must be boolean")

        if type(root) is not bool:
            raise PoloException("root must be boolean")
        
        message_dict = {}
        message_dict["Command"]= "Register"
        message_dict["Args"] = {"token":token,
                                "service": service, 
                                "params": params,
                                "multicast_groups":[g for g in multicast_groups], 
                                "permanent": permanent, 
                                "root":root}
        
        error = False
        try:
            message_str = json.JSONEncoder(allow_nan=False).encode(message_dict) # https://docs.python.org/2/library/json.html#infinite-and-nan-number-values
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error in JSON Encoder")
        
        error = False
        try:
            unicode_msg = message_str.encode('utf-8')
        except UnicodeError:
            error = True
        
        if error:
            raise PoloInternalException("Error in codification")

        error = False
        try:
            if -1 == self.wrappedSocket.send(unicode_msg):
                error = True
                reason = "Error on sending"
        except Exception as e:
            error = True
            reason = e

        if error:
            raise PoloInternalException("Error during internal communication %s " % reason)

        error = False
        try:
            data = self.wrappedSocket.recv()
        except socket.timeout:
            error = True

        if error or data == -1:
            reason = "No data received"
            raise PoloInternalException("Error during internal communication. %s" % reason)
        error = False
        
        try:
            data_dec = data.decode('utf-8')
        except Exception:
            error = True

        if error:
            reason = "Error on decoding"
            raise PoloInternalException("Error during internal communication. %s" % reason)

        try:
            parsed_data = json.loads(data_dec)#json.JSONDecoder(parse_constant=False).decode(data)
        except ValueError:
            error = True

        if error:
            raise PoloInternalException("Error during internal communication")

        error = None
        try:
            if parsed_data.get("OK") is not None:
                return parsed_data.get("OK")

            elif parsed_data.get("Error") is not None:
                raise PoloException("Error in publishing %s: '%s'" % (service, parsed_data.get("Error")))
        
            else:
                reason = "No valid fields"
                raise PoloInternalException("Error during internal communication. %s" % reason)
        except PoloInternalException as e:
            error = e

        except AttributeError as a:
            reason = "AttributeError"
            error = PoloInternalException("Error during internal communication %s" % reason)

        if error is not None:
            raise error

    def verify_parameters(self, service, multicast_groups=[]):
        """
        Verifies that the parameters are compliant with the following rules:

        - The service must be a string.

        - The multicast_groups parameter must be a list of valid IPv4 addresses.

        :param str service: The service identifier.

        :param list multicast_groups: The list of IPv4 addresses. 
        """
        error = False
        if not isinstance(service, six.string_types):
            raise PoloException("The name of the service %s is invalid" % service)

        if service is None or len(service) < 1:
            error = True

        if error:
            raise PoloException("The name of the service %s is invalid" % service)

        error = False
        faulty_ip = ''

        for ip in multicast_groups:
            if not isinstance(ip, six.string_types):
                error = True
                faulty_ip = ip
                break
            try:
                socket.inet_aton(ip)
            except socket.error:
                error = True
                faulty_ip = ip
                break
            try:
                first_byte = int(re.search("\d{3}", ip).group(0))
                if first_byte < 224 or first_byte > 239:
                    error = True
                    faulty_ip = ip
            except (AttributeError, ValueError):
                error = True
                faulty_ip = ip
                break

        if error:
            raise PoloException("Invalid multicast group address '%s'" % str(faulty_ip))


    def unpublish_service(self, service, multicast_groups=conf.MULTICAST_ADDRS, delete_file=False):
        """
        Removes a service. If the service is permanent, the file is only deleted if `delete_file` is set to `True`.\
        Please note that it is required to have the "ownership" of the service (that is, the only user which can remove \
        a service is the user who created it or the Polo instance itself) for the function to be successful. 
        Otherwise, a PoloException will be raised.
        
        :param string service: Name of the service

        :param list multicast_groups: List of the groups where the service is to be deleted. By default deletes the service from all groups

        :param boolean delete_file: Removes the file service if the service is `permanent`. Otherwise it is ignored.
        
        """
        token = self.get_token()

        self.verify_parameters(service, multicast_groups)

        if type(delete_file) is not bool:
            raise PoloException("delete_file must be boolean")

        message_dict = {}
        message_dict["Command"]= "Unpublish"
        message_dict["Args"] = {"token":token,
                                "service": service, 
                                "multicast_groups":[g for g in multicast_groups], 
                                "delete_file": delete_file,
                                "uid": os.geteuid()}
        error = False
        try:
            message_str = json.JSONEncoder(allow_nan=False).encode(message_dict) # https://docs.python.org/2/library/json.html#infinite-and-nan-number-values
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error in JSON Encoder")
        error  = False
        try:
            unicode_msg = message_str.encode('utf-8')
        except UnicodeError:
            error = True

        if error:
            raise PoloInternalException("Error in codification")

        error = False
        
        try:
            if -1 == self.wrappedSocket.send(unicode_msg):
                error = True
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error during internal communication")

        error = False
        try:
            data = self.wrappedSocket.recv()
        except socket.timeout:
            error = True

        if error or data == -1:
            raise PoloInternalException("Error during internal communication")

        try:
            data_dec = data.decode('utf-8')
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error during internal communication")

        try:
            parsed_data = json.loads(data_dec)#json.JSONDecoder(parse_constant=False).decode(data)
        except ValueError:
            error = True

        if error:
            raise PoloInternalException("Error during internal communication")

        if parsed_data.get("OK") is not None:
            return parsed_data.get("OK")

        elif parsed_data.get("Error") is not None:
            raise PoloException("Error in unpublishing %s: '%s'" % (service, parsed_data.get("Error")))
        
        else:
            raise PoloInternalException("Error during internal communication")

        return 0


    def service_info(self, service):
        """
        Returns a dictionary with all the information from a service
        
        :param string service: The name of the service
        """

        self.verify_parameters(service)

        message_dict = {}
        message_dict["Command"] = "Service-info"
        message_dict["Args"] = {"service":service}
        encoder = json.JSONEncoder(allow_nan=False)
        
        error = False
        try:
            message_str = encoder.encode(message_dict) # https://docs.python.org/2/library/json.html#infinite-and-nan-number-values
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error in JSON Encoder")
        
        error  = False
        try:
            if -1 == self.wrappedSocket.send(unicode_msg):
                error = True
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error on send")

        error = False
        try:
            data = self.wrappedSocket.recv()
        except socket.timeout:
            error = True

        if error or data == -1:
            raise PoloInternalException("Timeout for reception")

        try:
            data_dec = data.decode('utf-8')
        except Exception:
            error = True

        if error:
            raise PoloInternalException("Error on decoding")

        try:
            parsed_data = json.loads(data_dec)
        except ValueError:
            error = True

        if error:
            raise PoloInternalException("Error during internal communication")


        if parsed_data.get("Error", None) is not None:
            return None

        elif parsed_data.get("OK", None) is not None:
            data = parsed_data.get("OK")
            service = Service()
            service.identifier = data.get("identifier", None)
            if service.identifier is None:
                raise PoloInternalException("identifier missing in return")

            service.params = data.get("params", None)

            service.multicast_groups = data.get("multicast_groups", [])

            service.disabled = data.get("disabled", False)

            return service

        else:

            raise PoloInternalException("The return value is not valid")

    def has_service(self, service):
        """
        Returns true if the requested service is set to be offered
        
        :param string service: The name of the service.

            Please note that in order to check for an user service, the user id has to be complete (user:service)


        """
        pass

    def set_permanent(self, service, permanent=True):
        """
        Changes the status of a service (permanent/not permanent)

        :param string service: The name of the service

        :param bool permanent: Indicates whether the service must be permanent or not

        """

    def reload_services(self):
        pass

class PoloInternalException(Exception):
    """An exception raised when an internal error occurred \
    (for example, an internal communication error)"""

class PoloException(Exception):
    """An exception raised when an error caused by a misuse of the binding \
    (for example, a bad service ID, an already published service, etc.)"""