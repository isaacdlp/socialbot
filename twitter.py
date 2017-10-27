import json
import socialbot

with open("credentials.json", "r") as f:
    credentials = json.load(f)["twitter"]

twitter = socialbot.Twitter()
twitter.login(credentials["username"], credentials["password"])
#followers = twitter.get_users("carlosdoblado", max=10, action="follow")
#twitter.get_users("captruno", list="following", max=10, action="unfollow")
twitter.quit()