#!/usr/bin/env python
"""
Problem description.
"""

from __future__ import division
import socket
import sys


# class ManInTheMiddleSolver(object):
#     def __init__(self, output_file=sys.stdout):
#         self.__output_file = output_file
#
#     def solve(self, instances):
#         solutions = []
#         for instance in instances:
#             solutions.append(self.solve_instance(instance))
#
#         for i, solution in enumerate(solutions, start=1):
#             newline_needed = True if i != len(solutions) else False
#             self.__output_file.write("Case #{0}: {1}{2}".format(i, solution, "\n" if newline_needed else ""))
#
#     def solve_instance(self, instance):
#         """
#         Where the magic happens.
#         This method should return the solution (as a string) of the given instance.
#         """
#         return "Not Done!!!"
#
#
# class ManInTheMiddleInstance(object):
#     def __init__(self):
#         pass
#
#
# class ManInTheMiddleParser(object):
#     def __init__(self):
#         data = sys.stdin.readlines()
#         data = map(lambda s: s.strip(), data)
#
#         self.amount_samples = int(data[0][0])
#         self.data = data[1:]
#         self.instances = []
#
#         self.parse()
#
#     def parse(self):
#         """
#         This method should populate the instances list.
#         """
#         for line in self.data:
#             row = line.strip()
#             instance = ManInTheMiddleInstance()
#             self.instances.append(instance)
#
#     def get_data_as_type(self, type_):
#         return map(lambda row: map(lambda element: type_(element), row), self.data)
from Crypto.Cipher import AES
import requests


def strip_message(received):
    skip_len = len("CLIENT->SERVER:")
    return received[skip_len:]


if __name__ == "__main__":
    # parser = ManInTheMiddleParser()
    # solver = ManInTheMiddleSolver()
    # solver.solve(parser.instances)

    # 256 factorized = 2, 2, 2, 2, 2, 2, 2, 2 [8 times]


    s = socket.socket()

    host = "54.83.207.90"
    port = 6969

    s.connect((host, port))

    # Step 1: Handshake - Client says 'Hello?', server then answers with 'Hello!'
    print "Step 1 - Handshake"

    # Get message CLIENT->SERVER:Hello? and send it back.
    received = s.recv(1024)
    received_message = strip_message(received)
    s.send(received_message)

    # Get message SERVER->CLIENT:Hello! and send it back.
    received = s.recv(2014)
    received_message = strip_message(received)
    s.send(received_message)

    # Step 2:
    # Client creates a DiffieHellman instance.
    # Next message CLIENT->SERVER is formatted as key|diffie_hellman_prime|diffie_hellman_public_key.
    # Both prime and public_key are in hexadecimal format.

    received = s.recv(2014)
    message = strip_message(received)

    key_string, client_prime, client_public_key = message.split("|")

    print "C Prime: {0}".format(client_prime)
    print "C Public Key: {0}".format(client_public_key)

    new_key = ("0"*(len(client_public_key)//2)).encode("hex")
    new_message = "|".join([key_string, client_prime, new_key])

    s.send(message)

    # key = b'Sixteen byte key'
<target>
    # print key, len(key), len(new_key)
    # cipher = AES.new(new_key, AES.MODE_ECB)
    # msg = cipher.encrypt('YOUR KEYPHRASE00')
</target>
    # print msg

    # Server uses this info to create it's own DH instance and then writes it's public key.
    # Server also creates it's secret using server dh instance and client public_key.
    received = s.recv(2014)
    message = strip_message(received)
    key_string, server_public_key = message.split("|")

    print "S Public Key: {0}".format(server_public_key)

    new_key = ("0"*(len(client_public_key)//2)).encode("hex")
    new_message = "|".join([key_string, new_key])

    s.send(new_message)

    # Step 3:
    # Client computes secret using client DH and server public_key.
    # Then, Client ciphers KEYPHRASE using aes-256-ecb and client secret.
    received = s.recv(2014)
    message = strip_message(received)
    print message
    key_string, keyphrase = message.split("|")

    print "Keyphrase: {0}".format(keyphrase)

    s.send(message)

    # Servers deciphers keyphrase, uses it as key to a dict and then
    # returns the value corresponding to that dict, ciphered as well.
    received = s.recv(2014)
    message = strip_message(received)

    print message

    s.send(message)

    # Client then ends the connection.

    print s.recv(2014)




    s.close()