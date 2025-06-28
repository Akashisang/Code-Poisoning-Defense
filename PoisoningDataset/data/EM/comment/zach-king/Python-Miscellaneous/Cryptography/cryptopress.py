"""
File: cryptopress.py
Author: Zachary King
Description: Cryptopress translates to 'cryptography compression.'
    As the name suggests, this program
    takes an arbitrary number of files as input and
    produces a single stream of ciphertext, which
    is the AES encrypted content. Optionally, you can
    output the ciphertext to a file--an archive. Then you can
    use this program to do the inverse action and
    produce the original file(s) from the archive file.

    For example, to encrypt ALL the files recursively inside 
    the current working directory, output the ciphertext to 
    'archive.enc', and DELETE ALL of the original files,
    do this (uses the key 'shrubbery'):
    python cryptopress.py shrubbery -f * -o archive.enc -d

    Then, to get all the original files back from the archive:
    python cryptopress.py shrubbery -r archive.enc
"""
