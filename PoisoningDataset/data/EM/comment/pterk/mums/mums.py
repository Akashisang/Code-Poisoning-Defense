#!/usr/bin/env python3
"""Simple encrypted enviroment variables

Inspired by ansible's vault but simpler and with fewer dependencies
(though not as featureful), mums encrypts environment variables to a
file that you can store in your repository. The only thing you *have
to* keep a secret ("mum's the word") is the keyfile.

A keyfile can be any kind of textfile, its content is used as a
(hashed) password. By default is uses ~/.ssh/id_rsa but that is not
advisable in a team environment. Whatever it is though, don't store it
in the repository.

I like to keep the confs in a directory, in this case I called it .mums:

    $ mkdir .mums
    $ mums .mums/prod store DATABASE_URK "postgres://username:password@hostname:5432/dbname"
    $ mums .mums/prod show
    DATABASE_URK=postgres://username:password@hostname:5432/dbname
    $ mums .mums/prod run -- env | grep DATABASE
    DATABASE_URK=postgres://username:password@hostname:5432/dbname

Look like I made a typo. Let's add another key:

    $ mums .mums/prod store DATABASE_URL "postgres://username:password@hostname:5432/dbname"
    $ mums .mums/prod run -- env | grep DATABASE
    DATABASE_URK=postgres://username:password@hostname:5432/dbname
    DATABASE_URL=postgres://username:password@hostname:5432/dbname

Verify that is not in the environment by default:

    $ env | grep DATABASE # shows no output

Let's remove that typo:

    $ mums .mums/prod remove DATABASE_URK
    $ mums .mums/prod show
    DATABASE_URL=postgres://username:password@hostname:5432/dbname

To avoid typing too much I create a little shell-script 'prod' (or 'dev'):

    #!/usr/bin/env bash
    if [ $# -eq 0 ]
       then
       echo "No arguments supplied";
       exit 1;
    fi
    mums .mums/prod run -- "$@"

Then prefix any command with the desired environment name

    $ chmod 755 prod
    $ ./prod env | grep DATABASE

"""