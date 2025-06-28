from stravalib.client import Client
from stravalib import unithelper
from inspect import getmembers
import json

REAUTH = False
ClientId = "<ClientId_int_here>"
ClientSecret = "<ClientSecret_string_here>"
AccessToken = "<AccessToken_here_if_available>"
clientCode = "<ClientCodeHere>"
meterToMile = 0.000621371

if(REAUTH):
	AccessToken = client.exchange_code_for_token(client_id=ClientId,
		client_secret=ClientSecret,
		code=clientCode)
	print(AccessToken)

client = Client(access_token=AccessToken)
athlete = client.get_athlete()

r = open('data.json', 'r')
data = json.load(r)
activities = list(d["id"] for d in data)
r.close()

stravaActivities = client.get_activities()
for activity in stravaActivities:
	if (activity.id in activities):
		print("Already have this activity!")
		continue

	a = client.get_activity(activity.id)
	if (a.type != "Run"):
		print("Activity was a run")
		continue
	print("Found a new activity!", activity.id)
	act = {}
	act["date"] = a.start_date_local.strftime("%y-%m-%d")
	act["id"] = a.id
	act["distance"] = unithelper.miles(a.distance).num
	act["duration"] = a.moving_time.seconds
	act["speed"] = a.average_speed.num * meterToMile * 3600
	act["pace"] = float(1 / (meterToMile*a.average_speed))
	act["name"] = a.name
	act["splits"] = list({"time":split.elapsed_time.total_seconds() , "distance": unithelper.miles(split.distance).num } for split in a.splits_standard)

	data.append(act)

f = open('data.json', 'w')
print(json.dumps(data, indent=4), file=f);
