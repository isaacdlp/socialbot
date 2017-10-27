import json
import socialbot

with open("credentials.json", "r") as f:
    credentials = json.load(f)["instagram"]

instagram = socialbot.Instagram()
instagram.login(credentials["username"], credentials["password"])
followers = instagram.get_users("lunaelfica", max=50, action="follow")
instagram.quit()