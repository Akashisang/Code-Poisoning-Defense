#! /usr/bin/env python2.7

"""A Secure Password GENerator (aspgen)

aspgen is a password generation and analysis program. It both generates
secure passwords using cryptographically secure methods and secure the
Python interpreter environment as much as possible to mitigate password
acquisition by malicious software.

Full details are available in README.md available on GitHub at:

https://github.com/TheOneHyer/aspgen

or via:

aspgen readme

A brief synopsis of each function is provided here:

generator: generate secure password

analyzer: analyze user-given password

dict_generator: generate secure dictionary password

dict_analyzer: analyze user-given dictionary password

decrypter: decrypt encrypted report file

readme: print README.md and exit

Copyright:
    aspgen.py Generate and analyze secure passwords in a secure manner
    Copyright (C) 2016  Alex Hyer

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division
from __future__ import print_function
from __future__ import with_statement

import argparse
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from getpass import getpass
from math import log
import os
from pkg_resources import resource_stream
from prettytable import PrettyTable
import random
import re
import resource
from SecureString import clearmem
import cStringIO
import struct
import sys
import textwrap
from time import sleep

__author__ = 'Alex Hyer'
__email__ = 'theonehyer@gmail.com'
__license__ = 'GPLv3'
__maintainer__ = 'Alex Hyer'
__credits__ = 'Eli Bendersky, Generic Human'
__status__ = 'Stable'
__version__ = '1.1.1'


# http://eli.thegreenplace.net/2010/06/25/
# aes-encryption-of-files-in-python-with-pycrypto
# Alex Hyer modified the code for readability
def decrypt_file(key, in_file, chunksize=24*1024):
    """Decrypts a file using AES (CBC mode) with the given key

    Args:
        key (str): decryption key, a 16, 24 or 32 byte long string, Longer keys
                   are more secure.

        in_file (str): encrypted file to read

        chunksize (int): size of the chunk which the function uses to read
                         and decrypt the file. Larger chunk sizes can be
                         faster for some files and machines.
                         chunksize must be divisible by 16.

    Returns:
        str: decrypted data from file
    """

    with open(in_file, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        out = ''
        while True:
            chunk = infile.read(chunksize)
            if len(chunk) == 0:
                break
            out += decryptor.decrypt(chunk)

        return out[0:origsize]


def dict_stats(password, dictionary, guess_speeds=None, verbose=False):
    """Analyze various dictionary password statistics

    Important Note to Develoeprs: dict_stats uses Zipf's Law to tease apart
        the words in the password and thus determine password length. In
        order to do this, the dictionary must be sorted from the greatest
        usage frequency in the given language to lowest word frequency. If a
        frequency-sorted dictionary is unavailable, this function is useless
        and will provide incorrect results. This function also assumes the
        password was constructed by concatenating words at random from the
        given dictionary.

    Args:
        password (str): password to analyze

        dictionary (list): list of str containing word list used to generate
                           password ordered by frequency in language

        guess_speeds (list): list of ints representing the guesses/sec a hacker
                             can perform when attempting to crack the
                             password, else None. Returns a table.

        verbose (bool): If True, prints progress messages

    Returns:
        dict: dictionary of password stats. All password stats not calculated
              have value of None. Dictionary keys are (in YAML format):

              combinations <int of password combinations>
              entropy <float of password entropy>
              combinations_raw <if dict_pass is provided, int of password
                                combinations if password generated from ASCII
                                characters>
              entropy_raw <if dict_pass is provided, float of password
                           entropy if password generated from ASCII
                           characters>
              words <if dict_pass and dictionary provided, list of str
                     containing words in password>
              guess_table <if guess_speeds provided, PrettyTable of password
                           guessing speeds>
    """

    output = {
        'combinations': None,
        'entropy': None,
        'combinations_raw': None,
        'entropy_raw': None,
        'words': None,
        'guess_table': None
    }

    if verbose is True:
        print('Calculating dictionary statistics')
        print('Inferring words comprising password')
    output['words'] = infer_spaces(password, dictionary)
    output['combinations'] = len(dictionary) ** len(output['words'])
    output['entropy'] = log(output['combinations'], 2)
    if verbose is True:
        print('Words in Password: {0}'.format(' '.join(output['words'])))

    if verbose is True:
        print('Determining characters in password')

    # Generate password sets for analysis
    lower_letters = password_characters(all=False, lower_letters=True)
    upper_letters = password_characters(all=False, upper_letters=True)
    numbers = password_characters(all=False, numbers=True)
    special_chars = password_characters(all=False, special_chars=True)
    pass_set = set(password)

    # Detect characters in password
    num_parts = 0
    if len(pass_set.intersection(lower_letters)) != 0:
        if verbose is True:
            print('Detected lowercase letters in password')
        num_parts += len(lower_letters)
    if len(pass_set.intersection(upper_letters)) != 0:
        if verbose is True:
            print('Detected uppercase letters in password')
        num_parts += len(upper_letters)
    if len(pass_set.intersection(numbers)) != 0:
        if verbose is True:
            print('Detected numbers in password')
        num_parts += len(numbers)
    if len(pass_set.intersection(special_chars)) != 0:
        if verbose is True:
            print('Detected special characters in password')
        num_parts += len(special_chars)

    if verbose:
        print('Calculating basic stats for dictionary password')
    pass_len = len(password)
    output['combinations_raw'] = num_parts ** pass_len
    output['entropy_raw'] = log(output['combinations_raw'], 2)

    if guess_speeds is not None:
        output['guess_table'] = guess_table(output['combinations'],
                                            guess_speeds)

    return output


# http://eli.thegreenplace.net/2010/06/25/
# aes-encryption-of-files-in-python-with-pycrypto
# Alex Hyer modified the code for readability
def encrypt_file(key, stringio_file, outfile, chunksize=64*1024):
    """Encrypts an in-memory file using AES (CBC mode) with the given key

    Args:
        key (str): encryption key, a 16, 24 or 32 byte long string, Longer keys
                   are more secure.

        stringio_file (StringIO): StringIO memory file to encrypt

        out_filename (File): out file handle to write encrypted data

        chunksize (int): size of the chunk which the function uses to read
                         and encrypt the file. Larger chunk sizes can be
                         faster for some files and machines.
                         chunksize must be divisible by 16.
    """

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = sys.getsizeof(stringio_file.getvalue())

    outfile.write(struct.pack('<Q', filesize))
    outfile.write(iv)

    # "read" and chunk StringIO contents
    contents = stringio_file.getvalue()
    content_list = []
    last_position = 0
    for i in range(len(contents) % chunksize + 1):
        if last_position + chunksize > len(contents):
            content_list.append(contents[last_position:-1])
        else:
            content_list.append(content_list[
                                last_position:last_position + chunksize])
        last_position += chunksize
    content_list = filter(None, content_list)

    # Pad small chunks and encrypt them
    for chunk in content_list:
        if len(chunk) == 0:
            break
        elif len(chunk) % 16 != 0:
            chunk += ' ' * (16 - len(chunk) % 16)

        outfile.write(encryptor.encrypt(chunk))


def generate_password(chars, length, get_parts=False, secure=True):
    """Generate a string by randomly concatenating strings from a list

    Args:
        chars (list): list of str to generate password from

        length (int): length of password

        get_parts (bool): return strings password is made from, these strings
                          will not be deleted by secure flag

        secure (bool): delete strings in character list from memory after
                       generating password. WARNING: will yield individual
                       strings inaccessible, e.g. if one string is 'a'
                       and secure is enabled, the rest of the program
                       calling this function cannot access the char 'a'
                       anymore. Also, the actual password will remain in
                       memory, only chars are deleted.

    Returns:
        tuple: (password (str), parts (list)), password and strings
               constituting passwords. parts in tuple is None if get_parts
               flag is False

    Example:
        Note: Will not pass docstring test

        >>> generate_password(['a', 'b', 'c'], 5)
        ('abcba', None)
    """

    max_char = len(chars) - 1

    # Construct Password
    parts = []
    for i in range(0, length):
        parts.append(chars[random.SystemRandom().randint(0, max_char)])
    password = ''.join(parts)

    # Erase each password character from memory if not part of password
    if secure is True:
        for i in chars:
            if get_parts is False or i not in parts:
                # Don't clear only part because it clears password
                if length == 1 and i in parts:
                    continue
                clearmem(i)

    if get_parts is False:
        parts = None

    return password, parts


def guess_table(combinations, guess_speeds):
    """Generate PrettyTable of average password cracking speeds

    Args:
         combinations (int): number of possible

         guess_speeds (list): list of ints or floats representative
                              passwords/sec guessing speeds applied against
                              password

    Return:
        PrettyTable: PrettyTable of password cracking speeds
    """

    times = [(combinations / 2 / speed) for speed in guess_speeds]
    times = ['{0:.2e}'.format(time) for time in times]
    times.insert(0, 'Time to Guess (sec)')
    guess_speeds = ['{0:.2e}'.format(speed) for speed in guess_speeds]
    guess_speeds.insert(0, 'Guess Speeds (passwords/sec)')
    table = PrettyTable(guess_speeds)
    table.add_row(times)

    return table


# Credit: Generic Human on StackOverflow: http://stackoverflow.com/questions/
# 8870261/how-to-split-text-without-spaces-into-list-of-words
# Alex Hyer modified the code for readability and minor speed improvements
def infer_spaces(string, words):
    """Infer space locations in a string without spaces

    Args:
        string (str): string to infer spaces of

        words (list): list of str containing all possible words

    Returns:
        list: list of words in string

    Example:
        >>> from pkg_resources import resource_string
        >>> dict_words = resource_string('aspgen', 'common_words.txt').split()
        >>> infer_spaces('thecatinthehat', dict_words)
        ['the', 'cat', 'in', 'the', 'hat']
    """

    def best_match(i):
        """Find best match for first i characters in string

        This function makes numerous naughty assumptions about nonlocal
        variables that only work/are made because this function is inside
        another function.

        Args:
            i (int): position of current letter in string

        Returns:
            int, int: cost and length of match
        """

        candidates = enumerate(reversed(cost[max(0, i - max_length):i]))
        return min((c + word_cost.get(string[i - l - 1:i], 9e999), l + 1)
                   for l, c in candidates)

    # Build cost dict assuming Zipf's law and cost = -math.log(probability)
    words_len = len(words)
    word_cost = dict((word, log((i + 1) * log(words_len)))
                     for i, word in enumerate(words))
    max_length = max(len(i) for i in words)

    # Build the cost array
    cost = [0]
    for i in range(1, len(string) + 1):
        c, l = best_match(i)
        cost.append(c)

    # Backtrack to recover the minimal-cost string
    out = []
    i = len(string)
    while i > 0:
        c, l = best_match(i)
        assert c == cost[i]  # Throw error if values don't match last iter
        out.append(string[i - l:i])
        i -= l

    return [i for i in reversed(out)]


def par(message, to_print=False, report=None):
    """Print And Report, convenience wrapper for printing to screen and file

    Args:
        message (str): message to print or write

        to_print (bool): Whether or not to print message to screen

        report (File): file handle to write output to
    """

    if report is not None:
        report.write(message)
    if to_print is True:
        if message.endswith(os.linesep):  # Remove os.linesep at end of message
            message = re.sub(os.linesep + '$', '', message)
        print(message)


def password_characters(all=True, lower_letters=False, upper_letters=False,
                        numbers=False, special_chars=False):
    """Create a list of possible characters for a password

    Args:
        all (bool): same as setting lower_letters, upper_letters, and
                    special_chars all to True

        lower_letters (bool): add lower-case letters to character list

        upper_letters (bool): add upper-case letters to character list

        numbers (bool): add numbers to character list

        special_chars (bool): add special characters to character list

    Returns:
        list: List of str characters for password

    Example:
        >>> password_characters(all=False, special_chars=True)
        [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-',
        '.', ':', ';', '<', '=', '>', '?', '[', '\\', ']', '^', '_', '{', '|',
        '}']
    """

    characters = []

    if lower_letters or all:
        characters += [chr(char) for char in range(97, 123)]

    if upper_letters or all:
        characters += [chr(char) for char in range(65, 91)]

    if numbers or all:
        characters += [chr(char) for char in range(48, 58)]

    if special_chars or all:
        characters += [chr(char) for char in range(32, 48)]
        characters += [chr(char) for char in range(58, 65)]
        characters += [chr(char) for char in range(91, 97)]
        characters += [chr(char) for char in range(123, 127)]

    return characters


def password_stats(pass_len, num_parts, guess_speeds=None, verbose=False):
    """Analyze various password statistics

    Important Note to Developers: This function assumes the password was
        generated by randomly concatenating characters together.

    Args:
        pass_len (int): length of password

        num_parts (int): number of characters password was picked from

        guess_speeds (list): list of ints representing the guesses/sec a hacker
                             can perform when attempting to crack the
                             password, else None. Returns a table.

        verbose (bool): If True, prints progress messages

    Returns:
        dict: dictionary of password stats. All password stats not calculated
              have value of None. Dictionary keys are (in YAML format):

              combinations <int of password combinations>
              entropy <float of password entropy>
              guess_table <if guess_speeds provided, PrettyTable of password
                           guessing speeds>
    """

    output = {
        'combinations': None,
        'entropy': None,
        'guess_table': None
    }

    if verbose is True:
        print('Calculating basic password stats')
    output['combinations'] = num_parts ** pass_len
    output['entropy'] = log(output['combinations'], 2)

    if guess_speeds is not None:
        output['guess_table'] = guess_table(output['combinations'],
                                            guess_speeds)

    return output


def print_stats(combinations, entropy):
    """Convenience wrapper to format basic password stats

    Return formatted combination and entropy of password

    Args:
        combinations (int): number of combinations of password

        entropy (float): entropy of password

    Returns:
        tuple: two strings holding formatted output ready for printing

    Example:
        >>> a, b = print_stats(10000, 97.235)
        >>> print(a)
        Passwords Combinations: 1.00e+4
        >>> print(b)
        Password Entropy: 97.24
    """

    comb = 'Password Combinations: {0:.2e}'.format(combinations)
    ent = 'Password Entropy: {0:.2f}'.format(entropy)

    return comb, ent


def main(args):
    """Control program flow based on arguments. See --help and README for args

    Args:
        args (ArgumentParser): argparse ArgumentParser class
    """

    # Print README.md and exit
    if args.tool == 'readme':
        with resource_stream('aspgen', 'README.md') as in_handle:
            to_print = True if args.header is None else False
            if args.list_headers is True:  # Don't print non-headers
                to_print = False
            header_depth = None
            for line in in_handle:
                if line[0] == '#' and args.header is not None:
                    header = line.split(' ', 1)[-1]
                    # Start printing at matching header
                    if header.strip().lower() == args.header.lower():
                        to_print = True
                        header_depth = line.count('#')
                    # Stop reading and printing at next header of equal depth
                    elif header_depth is not None and \
                                    line.count('#') == header_depth:
                        break
                if args.list_headers is True and line[0] == '#':
                    print(line.strip())
                if to_print is True:
                    print(line.strip())
        sys.exit(0)

    # Decrypt file and exit
    if args.tool == 'decrypter':
        key = args.key_file.read()
        args.key_file.close()
        print(decrypt_file(key, args.report_file))
        sys.exit(0)

    # Begin actual password generation and analysis portion of program

    # Check flags
    if hasattr(args, 'guess_speeds') and hasattr(args, 'stats'):
        if args.guess_speeds is not None and args.stats is False:
            raise AttributeError('--guess_speeds requires --stats')

    # Open memory file for report
    setattr(args, 'mem_report_file', cStringIO.StringIO())

    if hasattr(args, 'encrypt') and args.encrypt is not None:
        try:
            assert args.report is not None
        except AssertionError:
            raise AssertionError('--encrypt requires --report')

    # Secure Environment
    resource.RLIMIT_CORE = 0  # Prevent core dumps
    if args.tool == 'generator' or args.tool == 'dict_generator':
        entropy = 'Unavailable'
        try:
            entropy = open('/proc/sys/kernel/random/entropy_avail', 'r').read()
            entropy = int(entropy.strip())
        except IOError:
            print('Cannot read entropy from '
                  '/proc/sys/kernel/random/entropy_avail')
            entropy = 'Unavailable'
        if entropy < args.system_entropy:
            print('System entropy is below {0}'
                  .format(str(args.system_entropy)))
            print('Type commands, open applications, read files, etc. to ')
            print('raise system entropy. (Type Ctrl+C to end program)')
        if entropy != 'Unavailable':
            while entropy < args.system_entropy:
                sleep(1)
                entropy = open('/proc/sys/kernel/random/entropy_avail', 'r') \
                    .read()
                entropy = int(entropy.strip())

    # Easter Egg
    # 3.5e+8: gizmodo/5966169/the-hardware-hackers-use-to-crack-your-passwords
    # 4.0+12 AntMiner S7
    # 1.0e+16 NSA?
    if hasattr(args, 'guess_speeds') is True and args.guess_speeds == [0]:
        args.guess_speeds = [3.4e+8, 4.0e+12, 1.0e+16]

    # Print fanciful output to record password generation information
    if args.report is not None:
        par('-' * 79 + os.linesep, report=args.mem_report_file)
        par('aspgen V{0}'.format(__version__).center(79) + os.linesep,
            report=args.mem_report_file)
        par('-' * 79 + os.linesep, report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)
        par('Parameters' + os.linesep, report=args.mem_report_file)
        par('----------' + os.linesep, report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)
        lines = textwrap.wrap('Command: {0}'.format(
            os.linesep.join(sys.argv[:])), 79)
        for line in lines:
            par(line + os.linesep, report=args.mem_report_file)
        for arg in vars(args):
            par('{0}: {1}'.format(arg, getattr(args, arg)) + os.linesep,
                report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)
        par('Environmental Data' + os.linesep, report=args.mem_report_file)
        par('------------------' + os.linesep, report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)
        par('Core Dumps: Disabled' + os.linesep, report=args.mem_report_file)
        par('System Entropy: ' + str(entropy) + os.linesep,
            report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)
        par('Password' + os.linesep, report=args.mem_report_file)
        par('--------' + os.linesep, report=args.mem_report_file)
        par(os.linesep, report=args.mem_report_file)

    if args.tool == 'generator' or args.tool == 'analyzer':

        if args.tool == 'generator':

            # Disable --all if any other flag is given
            if args.lower_letters is True or args.upper_letters is True or \
                    args.special_characters is True or args.numbers is True:
                args.all = False

            # Modify flags to make --alphanumeric work, overrides all flags
            if args.alphanumeric is True:
                args.all = False
                args.lower_letters = True
                args.upper_letters = True
                args.numbers = True
                args.special_characters = False

            chars = password_characters(all=args.all,
                                        lower_letters=args.lower_letters,
                                        upper_letters=args.upper_letters,
                                        numbers=args.numbers,
                                        special_chars=args.special_characters)
            num_chars = len(chars)

            password = generate_password(chars, args.length, secure=False)[0]

            message = 'Password: {0}'.format(password)
            par(message + os.linesep, to_print=True,
                report=args.mem_report_file)
            clearmem(message)  # Obliterate password
            par(os.linesep, report=args.mem_report_file)

        elif args.tool == 'analyzer':

            password = getpass()
            par('Password: ' + password, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)

            # Generate password sets for analysis
            lower_letters = password_characters(all=False, lower_letters=True)
            upper_letters = password_characters(all=False, upper_letters=True)
            numbers = password_characters(all=False, numbers=True)
            special_chars = password_characters(all=False, special_chars=True)
            pass_set = set(password)

            # Detect characters in password
            num_chars = 0
            if len(pass_set.intersection(lower_letters)) != 0:
                par('Detected lowercase letters in password' + os.linesep,
                    report=args.mem_report_file)
                num_chars += len(lower_letters)
            if len(pass_set.intersection(upper_letters)) != 0:
                par('Detected uppercase letters in password' + os.linesep,
                    report=args.mem_report_file)
                num_chars += len(upper_letters)
            if len(pass_set.intersection(numbers)) != 0:
                par('Detected numbers in password' + os.linesep,
                    report=args.mem_report_file)
                num_chars += len(numbers)
            if len(pass_set.intersection(special_chars)) != 0:
                par('Detected special characters in password' + os.linesep,
                    report=args.mem_report_file)
                num_chars += len(special_chars)
            par(os.linesep, report=args.mem_report_file)

        # Analyze password and par stats
        if args.tool == 'analyzer' or args.stats is True:
            par('Password Stats' + os.linesep, report=args.mem_report_file)
            par('--------------' + os.linesep, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)
            stats = password_stats(len(password), num_chars,
                                   guess_speeds=args.guess_speeds)
            c, e = print_stats(stats['combinations'], stats['entropy'])
            par(c + os.linesep, to_print=True, report=args.mem_report_file)
            par(e + os.linesep, to_print=True, report=args.mem_report_file)
            if stats['guess_table'] is not None:
                par('{0}Average Time to Cracked Password'.format(os.linesep)
                    + os.linesep, to_print=True, report=args.mem_report_file)
                par(str(stats['guess_table']), to_print=True,
                    report=args.mem_report_file)
                par(os.linesep, report=args.mem_report_file)

            par(os.linesep, report=args.mem_report_file)

        clearmem(password)  # Obliterate password

    elif args.tool == 'dict_analyzer' or args.tool == 'dict_generator':

        if args.tool == 'dict_generator':

            # Raise error if lengths would produce zero words to choose from
            if args.max_length < args.min_length:
                raise ValueError('Max word length is less than min word '
                                 'length')

            # Obtain words matching user requirements
            dict_words = []
            if args.uncommon is True:
                with resource_stream('aspgen', 'words.txt') as in_handle:
                    for word in in_handle:
                        word = word.strip()
                        if args.min_length <= len(word) <= args.max_length:
                            dict_words.append(word)
            else:
                with resource_stream('aspgen', 'common_words.txt') as \
                        in_handle:
                    for word in in_handle:
                        word = word.strip()
                        if args.min_length <= len(word) <= args.max_length:
                            dict_words.append(word)

            password, words = generate_password(dict_words, args.length,
                                                get_parts=True)

            message = 'Words in Password: {0}'.format(' '.join(words))
            par(message + os.linesep, to_print=True, report=args.mem_report_file)
            clearmem(message)  # Obliterate words in password
            if args.length > 1:  # clearmem will clear password if one word
                for word in words:
                    clearmem(word)  # Obliterate words in password

            message = 'Password: {0}'.format(password)
            par(message + os.linesep, to_print=True,
                report=args.mem_report_file)
            clearmem(message)  # Obliterate password
            par(os.linesep, report=args.mem_report_file)

        elif args.tool == 'dict_analyzer':

            # Obtain common words
            dict_words = []
            with resource_stream('aspgen', 'common_words.txt') as in_handle:
                for word in in_handle:
                    word = word.strip()
                    dict_words.append(word)

            password = getpass()

            par('Password: ' + password, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)

        stats = None

        # Calculate stats and par them
        if args.tool == 'dict_generator' and args.stats is True:
            par('Password Stats' + os.linesep, report=args.mem_report_file)
            par('--------------' + os.linesep, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)
            stats = password_stats(args.length, len(dict_words),
                                   guess_speeds=args.guess_speeds)
            stats['combinations_raw'] = 26 ** len(password)
            stats['entropy_raw'] = log(stats['combinations_raw'], 2)

        elif args.tool == 'dict_analyzer':
            par('Password Stats' + os.linesep, report=args.mem_report_file)
            par('--------------' + os.linesep, report=args.mem_report_file)
            par(os.linesep, report=args.mem_report_file)
            stats = dict_stats(password, dict_words,
                               guess_speeds=args.guess_speeds)
            par('Words in Password: {0}{1}'
                .format(' '.join(stats['words']), os.linesep),
                to_print=True, report=args.mem_report_file)

        if args.tool == 'dict_analyzer' or args.stats is True:
            c, e = print_stats(stats['combinations'], stats['entropy'])
            par(c + os.linesep, to_print=True, report=args.mem_report_file)
            par(e + os.linesep, to_print=True, report=args.mem_report_file)
            if args.guess_speeds is not None:
                par('{0}Average Time to Cracked Password'.format(os.linesep)
                    + os.linesep, to_print=True, report=args.mem_report_file)
                par(str(stats['guess_table']), to_print=True,
                    report=args.mem_report_file)
                par(os.linesep, report=args.mem_report_file)

        # Warn user if password is more vulnerable to brute force attacks
        if stats is not None and stats['entropy_raw'] < stats['entropy']:
            par(os.linesep, to_print=True, report=args.mem_report_file)
            par('!' * 79 + os.linesep, to_print=True, report=args.mem_report_file)
            par('!' + 'WARNING'.center(77) + '!' + os.linesep,
                to_print=True, report=args.mem_report_file)
            par('!' * 79 + os.linesep, to_print=True, report=args.mem_report_file)
            par(os.linesep, to_print=True, report=args.mem_report_file)
            par('Your password is more vulnerable to brute force '
                + os.linesep, to_print=True, report=args.mem_report_file)
            par('attacks than dictionary attacks. Consider generating '
                + os.linesep, to_print=True, report=args.mem_report_file)
            par('a dictionary password with more words or longer words.'
                + os.linesep, to_print=True, report=args.mem_report_file)
            par(os.linesep, to_print=True, report=args.mem_report_file)
            par('Brute Force Stats' + os.linesep, to_print=True,
                report=args.mem_report_file)
            par('-----------------' + os.linesep, to_print=True,
                report=args.mem_report_file)
            par(os.linesep, to_print=True, report=args.mem_report_file)
            c, e = print_stats(stats['combinations_raw'], stats['entropy_raw'])
            par(c + os.linesep, to_print=True, report=args.mem_report_file)
            par(e + os.linesep, to_print=True, report=args.mem_report_file)

        par(os.linesep, report=args.mem_report_file)

        for word in dict_words:
            clearmem(word)  # Obliterate words in password

        clearmem(password)  # Obliterate password

    # Print end of report
    par('-' * 79 + os.linesep, report=args.mem_report_file)
    par('Exiting aspgen V{0}'.format(__version__).center(
        79) + os.linesep,
        report=args.mem_report_file)
    par('-' * 79 + os.linesep, report=args.mem_report_file)

    # Securely encrypt report file
    if args.encrypt is not None:
        chars = password_characters()
        encrypt_password = generate_password(chars, 32)[0]
        hash = SHA256.new()
        hash.update(encrypt_password)
        key = hash.digest()
        args.encrypt.write(key)
        args.encrypt.close()
        encrypt_file(key, args.mem_report_file, args.report)
        args.report.close()

    # Write report file to disk if not encrypted
    if args.report is not None and args.encrypt is None:
        args.report.write(args.mem_report_file.getvalue())
        args.report.close()


def entry():
    """Entry point for console_scripts and called if __name__ == __main__

    This function parses the command line and calls main(). The logic here is
    that main() contains the actually program and function calls ad entry()
    acts as an entry for command-line based use and parses arguments.
    """

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.
                                     RawDescriptionHelpFormatter)
    parser.add_argument('-e', '--encrypt',
                        default=None,
                        type=argparse.FileType('wb'),
                        help='encrypt file and save key to file')
    parser.add_argument('-r', '--report',
                        default=None,
                        type=argparse.FileType('wb'),
                        help='generate runtime report, contains sensitive '
                             'data')
    parser.add_argument('-s', '--system_entropy',
                        default=100,
                        type=int,
                        help='minimum system entropy required before '
                             'proceeding with program')
    subparsers = parser.add_subparsers(title='Tools',
                                       dest='tool')

    analyzer = subparsers.add_parser('analyzer',
                                     help='Analyze a given password')
    analyzer.add_argument('-g', '--guess_speeds',
                          nargs='+',
                          type=float,
                          help='password guesses per second by hacker')

    decoder = subparsers.add_parser('decrypter',
                                    help='Decrypt encrypted report file')
    decoder.add_argument('report_file',
                         type=str,
                         help='aspgen encrypted report file')
    decoder.add_argument('key_file',
                         type=argparse.FileType('rb'),
                         help='key file to unlock report file')

    dict_analyzer = subparsers.add_parser('dict_analyzer',
                                          help='Analyze a dictionary-based '
                                               'password')
    dict_analyzer.add_argument('-g', '--guess_speeds',
                               default=None,
                               nargs='+',
                               type=float,
                               help='password guesses per second by hacker')

    dict_generator = subparsers.add_parser('dict_generator',
                                           help='Securely generate a '
                                                'dictionary-based password')
    dict_generator.add_argument('-g', '--guess_speeds',
                                default=None,
                                nargs='+',
                                type=float,
                                help='password guesses per second by hacker')
    dict_generator.add_argument('-l', '--length',
                                default=6,
                                type=int,
                                help='number of words in password')
    dict_generator.add_argument('-m', '--min_length',
                                default=5,
                                type=int,
                                help='minimum length word to use in password')
    dict_generator.add_argument('-t', '--stats',
                                action='store_true',
                                help='print stats on password')
    dict_generator.add_argument('-u', '--uncommon',
                                action='store_true',
                                help='permit uncommon words in password')
    dict_generator.add_argument('-x', '--max_length',
                                default=999,
                                type=int,
                                help='maximum length word to use in password')

    generator = subparsers.add_parser('generator',
                                      help='Securely generate a password')
    generator.add_argument('-a', '--all',
                           default=True,
                           action='store_true',
                           help='permit all characters in password [Default]')
    generator.add_argument('-g', '--guess_speeds',
                           default=None,
                           nargs='+',
                           type=float,
                           help='password guesses per second by hacker')
    generator.add_argument('-l', '--length',
                           default=12,
                           type=int,
                           help='length of password')
    generator.add_argument('-n', '--numbers',
                           action='store_true',
                           help='permit numbers in password')
    generator.add_argument('-o', '--lower_letters',
                           action='store_true',
                           help='permit lowercase letters in password')
    generator.add_argument('-p', '--alphanumeric',
                           action='store_true',
                           help='permit all letters and numbers in password, '
                                'same as -l, -n, and -u')
    generator.add_argument('-s', '--special_characters',
                           action='store_true',
                           help='permit special characters in password')
    generator.add_argument('-t', '--stats',
                           action='store_true',
                           help='print stats on password')
    generator.add_argument('-u', '--upper_letters',
                           action='store_true',
                           help='permit uppercase letters in password')

    readme = subparsers.add_parser('readme',
                                   help='print README.md and exit')
    readme.add_argument('-e', '--header',
                        default=None,
                        type=str,
                        help='only print README section defined by header')
    readme.add_argument('-l', '--list_headers',
                        default=None,
                        action='store_true',
                        help='print README headers and exit')

    args = parser.parse_args()

    main(args)

    sys.exit(0)


if __name__ == '__main__':
    entry()
