import time
import random
import csv
import os
import urllib2
import json
from dis import dis
from shutil import copyfile
import ssl
import sys

# Parameter "mode"
# define if you want to use the skript for scramble or unscramble
# can be either "scramble" or "unscramble"
from unicodedata import numeric

mode = "scramble"

##############################
# configuration for scramble #
##############################

# Parameter distractor_file
# this is the path to the file that contains distractors. One line per distractor.
distractor_file = "distractor.txt"

# Parameter test_items_file
# this is the path to the file that contains the test items with one test item in each line.
# All test items will be used.
test_items_file = "test-items.txt"

# Parameter number_of_distractors
# how many distractors should be used?
number_of_distractors = 10

# parameter translate_test_items
# Set to True when test items should be enabled, otherwise False
translate_test_items = True

# parameter translate_distractors
# Set to True when distractors should be enabled, otherwise False
translate_distractors = True

# Parameter source_lang
# the source language for translation. only used when translate_test_items=True or translate_distractors=True
source_lang = "en"

# Parameter target_lang
# the target language for translation. only used when translate_test_items=True or translate_distractors=True
target_lang = "de"

# Parameter google_api_key
# The Google API key used for Google translate. only used when translate_test_items=True or translate_distractors=True
google_api_key = '???'


# Settings for output files and directories - does not need to be changed
output_dir = "output/"
time = (time.strftime("%Y-%m-%d---%H-%M-%S"))
scramble_outfile = output_dir + "scramble-" + time + ".txt"
secret_outfile = output_dir + "secret-" + time + ".csv"
test_items_copy_filename = output_dir + "test-items-" + time + ".txt"

################################
# configuration for unscramble #
################################

# parameter secret_file
# this is the path to the secret file used as input for unscramble
secret_file = "output/secret-2016-06-07---10-09-00.csv"

# parameter translation_file
# this is the path to the translation file used as input for unscramble
translation_file = "output/translation-2016-06-07---10-09-00.txt"

# parameter outfile
# this is the path of the output file of unscramble
outfile = "output/uncramble-2016-06-07---10-09-00.csv"

##########################
# configuration finished #
##########################

# create output dir if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# helper function: call google translate for
# q (string to translate), sourceLang and targetLand
def translate(str, sourceLang, targetLang):
    q = urllib2.quote(str)
    url = "https://www.googleapis.com/language/translate/v2?key=" + google_api_key + "&source=" + sourceLang + "&target=" + targetLang + "&q=" + q
    req = urllib2.Request(url)
    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    response = urllib2.urlopen(req, context=gcontext).read()
    data = json.loads(response)
    return data["data"]["translations"][0]["translatedText"]

############
# scramble #
############

def scramble():

    print "start scramble"

    # create copy of test items file in output dir
    copyfile(test_items_file, test_items_copy_filename)

    # read test items and distractors in memory
    with open(test_items_file, 'r') as file:
        test_items = file.read().split("\n")
        file.close()

    with open(distractor_file, 'r') as file:
        distractors = file.read().split("\n")
        file.close()

    if number_of_distractors > len(distractors):
        print "Need more data in distractor file"

    # shuffle distractors
    random.shuffle(distractors)

    # generate array that keeps all data with columns
    # 0: sentence,
    # 1: position in test-items if it is a test item or None if it is a distractor,
    # 2: test item or distractor,
    # 3: google translation
    n_lines = number_of_distractors + len(test_items)

    data = [[None]*4] * n_lines

    # add test items array
    test_items_indizes = random.sample(range(1,n_lines), len(test_items))
    for i in range(0,len(test_items_indizes)):
        trans = None
        data[test_items_indizes[i]] = [test_items[i], i, "test item", trans]

    # add distractors to array

    distractorIndizes = random.sample(range(0, len(distractors)), number_of_distractors)
    distractorCounter=0
    for i in range(0,len(data)):
        if data[i][1] == None:

            distIndex = distractorIndizes[distractorCounter]
            distractorCounter+=1
            distractor = distractors[distIndex]

            data[i] = [distractor, distIndex, "distractor", trans]

    # write scramble file
    file = open(scramble_outfile, "w")
    for i in range(0, len(data)):
        file.write(data[i][0])
        file.write("\n")
    file.close()

    # collect data to translate
    translations = []
    for i in range(0, len(data)):
        if(translate_test_items and data[i][2] == "test item") or (translate_distractors and data[i][2] == "distractor"):
            translations.append({
                "txt": data[i][0],
                "index": i
            })

    # write scramble file
    file = open(scramble_outfile, "w")
    for i in range(0, len(data)):
        file.write(data[i][0])
        file.write("\n")
    file.close()

    # write csv file
    with open(secret_outfile, 'wb') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="\t", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(["sentence", "original index", "type", "google translation"])
        for i in range(0, len(data)):

            # translate if necessary
            if (translate_test_items and data[i][2] == "test item") or (
                        translate_distractors and data[i][2] == "distractor"):

                trans = translate(data[i][0], source_lang, target_lang)
                trans = trans.encode("utf-8")
                data[i][3] = trans

            csvwriter.writerow(data[i])

            if i > 0 and i % 20 == 0:
                print "wrote " + str(i) + " rows"
        csvfile.close()

    print "finished scramble"

##############
# unscramble #
##############

def uncramble(secret_file, translation_file, outfile):

    print "start unscramble"

    translations = []
    with open(translation_file, 'r') as file:
        for line in file:
            translations.append(line[0:-1])
        file.close()

    csvout = open(outfile, "w")
    csvwriter = csv.writer(csvout, delimiter="\t", quotechar='"', quoting=csv.QUOTE_MINIMAL)

    with open(secret_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t', quotechar='"')
        count=0
        csvwriter.writerow(["sentence", "original index", "type", "google translation", "given translation"])
        for row in reader:
            #skip first line
            if count==0:
                count+=1
                continue
            row.append(translations[count-1])
            count+=1
            csvwriter.writerow(row)
        csvfile.close()
    csvout.close()

    print "finish unscramble"

if mode == "scramble":
    scramble()
elif mode == "unscramble":
    uncramble(secret_file, translation_file, outfile)
else:
    print "error: mode needs to be either scramble or unscramble"
