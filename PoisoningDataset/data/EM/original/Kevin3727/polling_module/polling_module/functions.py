#!/usr/bin/env python3

from __init__ import *


def init(file_name):
    if not os.path.exists(file_name):
        db = sqlite3.connect(file_name)
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE users(id INTEGER PRIMARY KEY,
                               user TEXT unique,
                               pwd_sha512 TEXT,
                               pwdChanged INTEGER,
                               email TEXT)
        ''')
        db.commit()
        email_ = input(bcolors.OKBLUE +
                       "Enter the email associated with admin: " + bcolors.ENDC)
        PWD_new_ = getpass.getpass(
            bcolors.OKBLUE + "Enter new admin password: " + bcolors.ENDC)
        PWD_new_repeat_ = getpass.getpass(
            bcolors.OKBLUE + "Repeat new admin password: " + bcolors.ENDC)
        if PWD_new_ == PWD_new_repeat_:
            PWD_new_sha512_ = hashlib.sha512(
                PWD_new_.encode('utf8')).hexdigest()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO users(user, pwd_sha512, pwdChanged, email)
                        VALUES(?,?,?,?)''', ('admin', PWD_new_sha512_, 1, email_))
        db.commit()
        db.close()
        print('Database is initialized!')
        print(bcolors.WARNING +
              "At this time 'admin' password is not recoverable! Do not loose your password!" +
              bcolors.ENDC)


def derive_key_and_iv(password, key_length=16, iv_length=16):
    """
    This function will give you a deterministic "key" and "iv" for a
    given password.
    """
    password_ = password.encode('utf8')
    d = hashlib.sha256(password_).digest()
    return d[:key_length], d[key_length:key_length + iv_length]


def encryptCredentials(text_, out_file_, PWD_):
    """
    Encrypts "text_" (with maximum length of 128) in "out_file" with
    password "PWD_"
    """
    bs_ = 128
    key_, iv_ = derive_key_and_iv(PWD_)
    aes_mode_ = AES.MODE_CBC
    encryptor = AES.new(key_, aes_mode_, iv_)
    with open(out_file_, 'wb') as File_:
        ending_ = b''
        for i in range(bs_ - len(text_)):
            ending_ += b'\x00'
        key_cred_ = text_.encode('utf8')
        File_.write(encryptor.encrypt(key_cred_ + ending_))


@try_except
def decryptCredentials(in_file_, PWD_):
    """
    Decrypts "in_file" using password "PWD_" and returns a text file
    of maximum 128 character long.
    """
    bs_ = 128
    key_, iv_ = derive_key_and_iv(PWD_)
    aes_mode_ = AES.MODE_CBC
    decryptor = AES.new(key_, aes_mode_, iv_)
    with open(in_file_, 'rb') as File_:
        chunk = decryptor.decrypt(File_.read(bs_))
        text_ = chunk.decode('utf8').replace('\x00', '')
    return text_


def addUser(file_name, admin, auto=False, user=None, email=None):
    if admin:
        if auto:
            user_ = user
        else:
            user_ = input(bcolors.OKBLUE +
                          "Enter the new username: " + bcolors.ENDC)
        userinfo_ = fetchUserInfo(file_name, user_)
        if userinfo_ is None:
            if auto:
                email_ = email
            else:
                email_ = input(bcolors.OKBLUE +
                               "Enter the email associated with the user: " + bcolors.ENDC)
            # generate random password
            PWD_new_ = ''.join(
                [random.choice(string.ascii_letters + string.digits) for n in range(8)])
            PWD_new_sha512_ = hashlib.sha512(
                PWD_new_.encode('utf8')).hexdigest()
            db = sqlite3.connect(file_name)
            cursor = db.cursor()
            cursor.execute('''INSERT INTO users(user, pwd_sha512, pwdChanged, email)
                        VALUES(?,?,?,?)''', (user_, PWD_new_sha512_, 0, email_))
            db.commit()
            db.close()
            if not auto:
                print("username" + '\t' + "email" + '\t' +
                      "temporary password", end='\n')
            print(str(user_) + '\t' + email_ + '\t' + PWD_new_, end='\n')
        else:
            print(bcolors.WARNING +
                  "User \"" + str(user_) + "\"  already exits." +
                  bcolors.ENDC)
            return 1
    else:
        print(
            bcolors.WARNING +
            "Only admin can add users." +
            bcolors.ENDC)
        return 1


def createUsersFromFile(file_name, admin):
    if admin:
        csv_file_ = input(bcolors.OKBLUE +
                          "Enter location of csv file which you want to load: " + bcolors.ENDC)
        if os.path.exists(csv_file_):
            with open(csv_file_, 'r') as fr:
                reader_ = csv.reader(fr)
                users_list_ = list(reader_)
            print("username" + '\t' + "email" + '\t' +
                  "temporary password", end='\n')
            for user_ in users_list_:
                addUser(file_name, admin,
                        auto=True,
                        user=user_[0],
                        email=user_[1])
        else:
            print(
                bcolors.WARNING +
                "File does not exists." +
                bcolors.ENDC)
            return 1
    else:
        print(
            bcolors.WARNING +
            "Only admin can add users." +
            bcolors.ENDC)
        return 1


def deleteUser(file_name, admin):
    if admin:
        delete_user_ = input(bcolors.OKBLUE +
                             "Enter the username to delete: " + bcolors.ENDC)
        userinfo_ = fetchUserInfo(file_name, delete_user_)
        if userinfo_ != None:
            db = sqlite3.connect(file_name)
            cursor = db.cursor()
            cursor.execute(
                '''DELETE FROM users WHERE user = ? ''', (delete_user_,))
            db.commit()
            db.close()
            print("User \"" + str(delete_user_) +
                  "\" has been deleted successfully!")
        else:
            print(bcolors.WARNING +
                  "Username does not exits." +
                  bcolors.ENDC)
            return 1
    else:
        print(
            bcolors.WARNING +
            "Only admin can delete users." +
            bcolors.ENDC)
        return 1


def fetchUserInfo(file_name, user):
    db = sqlite3.connect(file_name)
    cursor = db.cursor()
    cursor.execute(
        '''SELECT user, pwd_sha512, pwdChanged, email FROM users WHERE user=?''', (user,))
    userinfo_ = cursor.fetchone()
    db.close()
    return userinfo_


def fetchUserInfoPoll(file_name, user):
    db = sqlite3.connect(file_name)
    cursor = db.cursor()
    cursor.execute(
        '''SELECT user, eligibility, voted FROM users WHERE user=?''', (user,))
    userinfo_ = cursor.fetchone()
    db.close()
    return userinfo_


# changing password for users
def changePassword(file_name, user):
    userinfo_ = fetchUserInfo(file_name, user)
    trial_ = 0
    while(trial_ < 3):
        PWD_new_ = getpass.getpass(
            bcolors.OKBLUE + "Enter new password: " + bcolors.ENDC)
        PWD_new_repeat_ = getpass.getpass(
            bcolors.OKBLUE + "Repeat new password: " + bcolors.ENDC)
        if PWD_new_ == PWD_new_repeat_:
            PWD_new_sha512_ = hashlib.sha512(
                PWD_new_.encode('utf8')).hexdigest()
            if PWD_new_sha512_ != userinfo_[1]:
                db = sqlite3.connect(file_name)
                cursor = db.cursor()
                cursor.execute('''UPDATE users SET pwd_sha512 = ? WHERE user = ? ''',
                               (PWD_new_sha512_, user))
                cursor.execute('''UPDATE users SET pwdChanged = ? WHERE user = ? ''',
                               (1, user))
                db.commit()
                db.close()
                print("Password is changed successfuly!")
                return
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "you cannot use the temporary passwords, try again!" + bcolors.ENDC)
        else:
            trial_ += 1
            print(bcolors.WARNING +
                  "Passwords do not match, try again!" + bcolors.ENDC)


def resetPassword(file_name, admin, user=None):
    if(admin):
        if not user:
            user = input(bcolors.OKBLUE +
                         "Enter the username to reset password: " + bcolors.ENDC)
        userinfo_ = fetchUserInfo(file_name, user)
        if userinfo_ != None:
            # generate random password
            PWD_new_ = ''.join(
                [random.choice(string.ascii_letters + string.digits) for n in range(8)])
            PWD_new_sha512_ = hashlib.sha512(
                PWD_new_.encode('utf8')).hexdigest()
            db = sqlite3.connect(file_name)
            cursor = db.cursor()
            cursor.execute('''UPDATE users SET pwd_sha512 = ? WHERE user = ? ''',
                           (PWD_new_sha512_, user))
            cursor.execute('''UPDATE users SET pwdChanged = ? WHERE user = ? ''',
                           (0, user))
            db.commit()
            db.close()
            print("Password is reset. Temporary password is: " +
                  PWD_new_)

        else:
            print(bcolors.WARNING +
                  "Username does not exit." +
                  bcolors.ENDC)
            return 1
    else:
        print(bcolors.WARNING +
              "Only admin can resert password." +
              bcolors.ENDC)
        return 1


def printUsers(file_name, admin):
    if admin:
        users_list_ = np.array([])
        db = sqlite3.connect(file_name)
        cursor = db.cursor()
        cursor = db.cursor()
        cursor.execute('''SELECT user FROM users''')
        for row in cursor:
            users_list_ = np.append(users_list_, row[0])
        db.commit()
        db.close()
        users_list_.sort()
        for user_ in users_list_:
            print(user_, end=', ')
        print('\n')
    else:
        print(bcolors.WARNING +
              "Only admin can print users." +
              bcolors.ENDC)
        return 1


def Login(file_name):
    '''reruns: master, admin, user, username'''
    master_ = False
    admin_ = False
    user_ = False
    username_ = input(bcolors.OKBLUE + "Username: " + bcolors.ENDC)
    if username_ == 'master':
        print('Master function is not activated!')
        pass
    elif username_ == 'admin':
        userinfo_ = fetchUserInfo(file_name, 'admin')
        trial_ = 0
        while trial_ < 3:
            PWD_admin_ = getpass.getpass(
                bcolors.OKBLUE + "enter admin password: " + bcolors.ENDC)
            PWD_admin_sha512_ = hashlib.sha512(
                PWD_admin_.encode('utf8')).hexdigest()
            if PWD_admin_sha512_ == userinfo_[1]:
                admin_ = True
                return False, admin_, False, 'admin'
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "Password is wrong, try again!" + bcolors.ENDC)
    else:
        userinfo_ = fetchUserInfo(file_name, username_)
        trial_ = 0
        while trial_ < 3:
            PWD_ = getpass.getpass(
                bcolors.OKBLUE + "Password: " + bcolors.ENDC)
            PWD_sha512_ = hashlib.sha512(
                PWD_.encode('utf8')).hexdigest()
            if userinfo_ != None:
                if PWD_sha512_ == userinfo_[1]:
                    if userinfo_[2] == 0:
                        changePassword(file_name, username_)
                        user_ = True
                        return False, False, user_, username_
                    else:
                        user_ = True
                        return False, False, user_, username_
                else:
                    trial_ += 1
                    print(bcolors.WARNING +
                          "Username or Password is wrong, try again!" + bcolors.ENDC)
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "Username or Password is wrong, try again!" + bcolors.ENDC)
    return False, False, False, None


def createPoll(file_name, admin):
    if admin:
        if not os.path.isdir("../bin/polls/"):
            os.makedirs("../bin/polls/")

        trial_ = 0
        success_ = False
        while(trial_ < 3):
            Number_ = input(bcolors.OKBLUE +
                            "Enter poll number: " + bcolors.ENDC)
            poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
            poll_db_file_ = '../bin/polls/poll_' + Number_ + '.db'
            poll_result_file_ = '../bin/polls/poll_' + Number_ + '.result'
            poll_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.poll'
            poll_db_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.db'
            poll_result_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.result'
            if not (os.path.exists(poll_file_)
                    or os.path.exists(poll_db_file_)
                    or os.path.exists(poll_result_file_)
                    or os.path.exists(poll_file_archived_)
                    or os.path.exists(poll_db_file_archived_)
                    or os.path.exists(poll_result_file_archived_)):
                success_ = True
                break
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "Poll already exists. Try again!" +
                      bcolors.ENDC)
        if not success_:
            print(bcolors.WARNING + "Poll was not created!" + bcolors.ENDC)
            return 1

        success_ = False
        Question_ = input(
            bcolors.OKBLUE + "Enter the poll questoin: " + bcolors.ENDC)
        trial_ = 0
        while(trial_ < 3):
            Num_answer_ = input(
                bcolors.OKBLUE + "How many choices there are= " + bcolors.ENDC)
            try:
                Num_answer_ = int(Num_answer_)
                success_ = True
                break
            except BaseException:
                trial_ += 1
                print(bcolors.WARNING +
                      "Please enter an integer number." +
                      bcolors.ENDC)
        if not success_:
            print(bcolors.WARNING + "Poll was not created!" + bcolors.ENDC)
            return 1

        Answers_ = []
        for i in range(Num_answer_):
            Answer_ = input(bcolors.OKBLUE + "Enter choice " +
                            str(i + 1) + ": " + bcolors.ENDC)
            Answers_.append(Answer_)

        with open(poll_file_, 'w') as File_:
            File_.write(Question_ + '\n')
            for i in range(Num_answer_):
                File_.write(Answers_[i] + '\n')

        # create user database
        db_poll = sqlite3.connect(poll_db_file_)
        cursor_poll = db_poll.cursor()
        cursor_poll.execute('''CREATE TABLE users(id INTEGER PRIMARY KEY,
                            user TEXT unique,
                            eligibility INTEGER,
                            voted INTEGER)''')
        db_poll.commit()

        db = sqlite3.connect(file_name)
        cursor = db.cursor()
        cursor_poll = db_poll.cursor()
        cursor.execute('''SELECT user FROM users''')
        for row in cursor:
            cursor_poll.execute('''INSERT INTO users(user, eligibility, voted)
                    VALUES(?,?,?)''', (row[0], 1, 0))
        db_poll.commit()
        db_poll.close()
        db.close()

        # result db
        db_result = sqlite3.connect(poll_result_file_)
        cursor_result = db_result.cursor()
        cursor_result.execute('''CREATE TABLE users(id INTEGER PRIMARY KEY,
                            hash TEXT unique,
                            vote TEXT)''')
        db_result.commit()
        db_result.close()

        print("Poll number " + Number_ + " is created, successfully!")
        return 0
    else:
        print(bcolors.WARNING +
              "Only admin can create polls." +
              bcolors.ENDC)
        return 1

# Voting


def vote(user, admin):
    Casted_ = False
    if admin:
        print("Admin cannot vote. Please log in as a user.")
        return 1

    trial_ = 0
    Poll_assigned_ = False
    while(trial_ < 3):
        Number_ = input(bcolors.OKBLUE + "Enter poll number: " + bcolors.ENDC)
        poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
        if os.path.exists(poll_file_):
            Poll_assigned_ = True
            break
        else:
            trial_ += 1
            print(bcolors.WARNING +
                  "Poll does not exist. Try again!" +
                  bcolors.ENDC)
    if not Poll_assigned_:
        return 1

    poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
    poll_db_file_ = '../bin/polls/poll_' + Number_ + '.db'
    poll_result_file_ = '../bin/polls/poll_' + Number_ + '.result'

    with open(poll_file_, 'r') as f:
        lines_ = f.readlines()

    print(bcolors.BOLD + lines_[0][:-1] + bcolors.ENDC)
    for i in range(1, len(lines_)):
        print(bcolors.BOLD + str(i) + ') ' + bcolors.ENDC + lines_[i][:-1])

    userInfoPoll_ = fetchUserInfoPoll(poll_db_file_, user)
    if userInfoPoll_[1] == '0':
        print(bcolors.WARNING +
              "You are not an eligible voter!\n" +
              "If you think this is a mistake please contact administrator!" +
              bcolors.ENDC)
        return 1
    if userInfoPoll_[2] != '0':
        print(bcolors.WARNING +
              "You have already voted!" +
              bcolors.ENDC)
        return 1

    trial_ = 0
    while(trial_ < 3):
        try:
            Vote_ = int(input(bcolors.OKBLUE + "Enter your vote (as a number between 1 and "
                              + str(len(lines_) - 1) + "): " + bcolors.ENDC))
            if((Vote_ > 0) & (Vote_ < len(lines_))):
                Casted_ = True
                break
            else:
                trial_ += 1
                print(bcolors.WARNING + "Error! Enter a number between 1 and " +
                      str(len(lines_) - 1) + bcolors.ENDC)
        except BaseException:
            trial_ += 1
            print(bcolors.WARNING + "Error! Enter a number between 1 and " +
                  str(len(lines_) - 1) + bcolors.ENDC)
    if Casted_:
        Casted_ = False
        db_poll = sqlite3.connect(poll_db_file_)
        cursor_poll = db_poll.cursor()
        cursor_poll.execute('''UPDATE users SET voted = ? WHERE user = ? ''',
                            (1, user))
        db_poll.commit()
        db_poll.close()
        Casted_ = True

    if not Casted_:
        print(
            bcolors.WARNING +
            "Vote has not been casted. Try again!" +
            bcolors.ENDC)
        return 1

    salt_ = Random.new().read(16)
    receipt_ = hashlib.sha256(
        (UserName_.encode('utf8') + salt_)).hexdigest()[:32]

    db_result = sqlite3.connect(poll_result_file_)
    cursor_result = db_result.cursor()
    cursor_result.execute('''INSERT INTO users(hash, vote)
                        VALUES(?,?)''', (receipt_, Vote_))
    db_result.commit()
    db_result.close()

    # with open('../bin/polls/poll_' + Number_ + '.results', 'a') as f:
    #    fcntl.flock(f, fcntl.LOCK_EX)
    #    f.write(str(Vote_) + '\t' + str(receipt_) + '\n')
    #    fcntl.flock(f, fcntl.LOCK_UN)

    print("Thank you! Your vote has been casted anonymously!")
    print("Your receipt number is: " + bcolors.BOLD + receipt_ + bcolors.ENDC)
    print("Keep your receipt in order to validate your vote later.")
    print("Receipt numbers are public but not traceable by anyone!")
    return 0


def closePolling(admin):
    if admin():
        if not os.path.isdir("../bin/polls/archive/"):
            os.makedirs("../bin/polls/archive/")

        Poll_assigned_ = False
        trial_ = 0
        while trial_ < 3:
            Number_ = input(
                bcolors.OKBLUE + "Enter the poll number you want to end: " + bcolors.ENDC)
            poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
            if os.path.exists(poll_file_):
                Poll_assigned_ = True
                break
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "This poll does not exist or is already closed. Try again!" +
                      bcolors.ENDC)
        if not Poll_assigned_:
            return 1

        # double check
        print(bcolors.OKBLUE +
              "After ending the poll, no one can vote anymore!" +
              bcolors.ENDC)
        archive_ = input(bcolors.OKBLUE +
                         "Are you sure you want to end poll \"" +
                         str(Number_) + "\"? [y/N]" + bcolors.ENDC)
        if archive_ in ['y', 'Y']:
            pass
        else:
            print(bcolors.WARNING +
                  "Poll has not been ended and will remain active!" +
                  bcolors.ENDC)
            return 1

        # move files to archive
        poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
        poll_db_file_ = '../bin/polls/poll_' + Number_ + '.db'
        poll_result_file_ = '../bin/polls/poll_' + Number_ + '.result'
        poll_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.poll'
        poll_db_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.db'
        poll_result_file_archived_ = '../bin/polls/archive/poll_' + Number_ + '.result'
        os.rename(poll_file_, poll_file_archived_)
        os.rename(poll_db_file_, poll_db_file_archived_)
        os.rename(poll_result_file_, poll_result_file_archived_)

        publishResults('../bin/polls/',
                       poll_file_archived_,
                       poll_db_file_archived_,
                       poll_result_file_archived_)

        print("Poll is archived you can find the results in: ../bin/polls/")

    else:
        print(bcolors.WARNING +
              "Only admin can create polls." +
              bcolors.ENDC)
        return 1


def publishResults(publish_dir,
                   poll_file,
                   poll_db_file,
                   poll_result_file):

    # users voted
    users_voted_ = np.array([])
    users_not_voted_ = np.array([])
    db = sqlite3.connect(poll_db_file_)
    cursor = db.cursor()
    cursor.execute('''SELECT user, eligibility, voted FROM users''')
    for row in cursor:
        if row[1] == '1' and row[2] == '1':
            users_voted_ = np.append(users_voted_, row[0])
        elif row[1] == '1' and row[2] == '0':
            users_not_voted_ = np.append(users_not_voted_, row[0])
    db.commit()
    db.close()
    users_voted_.sort()
    users_not_voted_.sort()

    # results
    hash_votes_ = np.array([]).reshape(0, 2)
    db_result = sqlite3.connect(poll_result_file_)
    cursor_result = db_result.cursor()
    cursor_result.execute('''SELECT hash, vote FROM users''')
    for row in cursor_result:
        hash_votes_ = np.vstack([hash_votes_, [row[0], row[1]]])
    db_result.commit()
    db_result.close()

    # counting votes
    hash_votes_ = hash_votes_[hash_votes_[:, 0].argsort()]
    unique_, counts_ = np.unique(hash_votes_[:, 1], return_counts=True)
    vote_dict_ = dict(zip(unique_, counts_))

    # write results
    with open(poll_file_, 'r') as f:
        lines_ = f.readlines()

    pub_file_ = publish_dir + '/poll_' + Number_ + '_results.txt'
    with open(pub_file_, 'w') as fw:
        fw.write('Poll ' + Number_ + ' results:\n\n')
        fw.write(lines_[0])
        fw.write('Votes:\n')
        for item in unique_[counts_.argsort()[::-1]]:
            fw.write(vote_dict_[item] + '\t')
            fw.write(lines_[int(item)].strip() + '\n')
        fw.write('\n\n')
        fw.write('Eligible users who have voted (alphabetically):\n')
        for item in users_voted_:
            fw.write(item + '\n')

        fw.write('\n')
        fw.write('Eligible users who have NOT voted (alphabetically):\n')
        for item in users_not_voted_:
            fw.write(item + '\n')

        fw.write('\n')
        fw.write('Hash reciepts (alphabetically):\n')
        fw.write('Hash\t\t\t\t Vote')
        for hash_, vote_ in hash_votes_:
            fw.write(hash_ + '\t' + vote_ + '\n')

    print('Results successfully published in: ' + pub_file_)


def viewResults(finished=True, Number=None):
    if Finished:
        Poll_assigned_ = False
        trial_ = 0
        while trial_ < 3:
            Number_ = input(
                bcolors.OKBLUE + "Enter the poll number which results you want to view: " + bcolors.ENDC)
            poll_file_ = '../bin/polls/archive/poll_' + Number_ + '.poll'
            poll_db_file_ = '../bin/polls/archive/poll_' + Number_ + '.db'
            poll_result_file_ = '../bin/polls/archive/poll_' + Number_ + '.result'
            if os.path.exists(poll_file_)\
                    and os.path.exists(poll_db_file_)\
                    and os.path.exists(poll_result_file_):
                Poll_assigned_ = True
            else:
                trial_ += 1
                print(bcolors.WARNING +
                      "This poll does not exist or is still open. Try again!" +
                      bcolors.ENDC)
        if not Poll_assigned_:
            return 1
    else:
        Number_ = Number
        poll_file_ = '../bin/polls/poll_' + Number_ + '.poll'
        poll_db_file_ = '../bin/polls/poll_' + Number_ + '.db'
        poll_result_file_ = '../bin/polls/poll_' + Number_ + '.result'

    # users voted
    if Finished:
        users_voted_ = np.array([])
        users_not_voted_ = np.array([])
        db = sqlite3.connect(poll_db_file_)
        cursor = db.cursor()
        cursor.execute('''SELECT user, eligibility, voted FROM users''')
        for row in cursor:
            if row[1] == '1' and row[2] == '1':
                users_voted_.append(row[0])
            elif row[1] == '1' and row[2] == '0':
                users_not_voted_.append(row[0])
        db.commit()
        db.close()
        users_voted_.sort()
        users_not_voted_.sort()

    # results
    hash_votes_ = np.array([]).reshape(0, 2)
    db_result = sqlite3.connect(poll_result_file_)
    cursor_result = db_result.cursor()
    cursor_result.execute('''SELECT hash, vote FROM users''')
    for row in cursor_result:
        hash_votes_ = np.vstack([hash_votes_, [row[0], row[1]]])
    db_result.commit()
    db_result.close()

    # counting votes
    hash_votes_ = hash_votes_[hash_votes_[:, 0].argsort()]
    unique_, counts_ = np.unique(hash_votes_[:, 1], return_counts=True)
    vote_dict_ = dict(zip(unique_, counts_))

    # write results
    with open(poll_file_, 'r') as f:
        lines_ = f.readlines()

    pub_file_ = publish_dir + '/poll_' + Number_ + '_results.txt'
    print('Poll ' + Number_ + ' results:\n', end='\n')
    print(lines_[0])
    print('Votes:', end='\n')
    for item in unique_[counts_.argsort()[::-1]]:
        print(vote_dict_[item], end='\t')
        print(lines_[int(item)].strip(), end='\n')
    print('\n', end='')
    if Finished:
        print('Eligible users who have voted (alphabetically):', end='\n')
        for item in users_voted_:
            print(item, end='\n')

        print('\n')
        print('Eligible users who have NOT voted (alphabetically):', end='\n')
        for item in users_not_voted_:
            print(item, end='\n')

    print('\n')
    print('Hash reciepts (alphabetically):', end='\n')
    print('Hash\t\t\t\t Vote', end='\n')
    for hash_, vote_ in hash_votes_:
        print(hash_ + '\t' + vote_, end='\n')


def viewOpenPollResults(user):
    Poll_assigned_ = False
    trial_ = 0
    while trial_ < 3:
        Number_ = input(
            bcolors.OKBLUE + "Enter the poll number which results you want to view: " + bcolors.ENDC)
        poll_file_archived_ = '../bin/polls/poll_' + Number_ + '.poll'
        poll_db_file_archived_ = '../bin/polls/poll_' + Number_ + '.db'
        poll_result_file_archived_ = '../bin/polls/poll_' + Number_ + '.result'
        if os.path.exists(poll_file_archived_)\
                and os.path.exists(poll_db_file_archived_)\
                and os.path.exists(poll_result_file_archived_):
            Poll_assigned_ = True
        else:
            trial_ += 1
            print(bcolors.WARNING +
                  "This poll does not exist or is closed. Try again!" +
                  bcolors.ENDC)
    if not Poll_assigned_:
        return 1

    # check if the user has voted
    db = sqlite3.connect(poll_db_file_archived_)
    cursor = db.cursor()
    cursor.execute('''SELECT voted FROM users WHERE user=?''', (user,))
    voted_ = cursor.fetchone()[0]
    db.commit()
    db.close()

    if voted_ == '1':
        viewResults(finished=False, Number=Number_)
    else:
        print(bcolors.WARNING +
              "You cannot view open polls' results if you have not voted!" + bcolors.ENDC)
