'''simplifing data encryption.

Example::

    password_text = 'super secret'
    plain_text = 'Hello, world'
    encrypted_text = encrypt(plain_text, password_text)
    print plain_text, encrypted_text
    decrypted_text = decrypt(encrypted_text, password_text)
    print decrypted_text

    # Generate some password-like strings and verify encryption/decryption

    import string, random
    chars = string.letters + string.digits
    for i in range(0,100):
        length = random.randint(8,40)
        testdata = ''.join([random.choice(chars) for _ in range(length)])
        if testdata == decrypt(encrypt(testdata, password_text),
                               password_text):
            print i,
        else:
            print testdata, "failed!"
            break


'''