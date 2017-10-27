import json
import socialbot

with open("credentials.json", "r") as f:
    credentials = json.load(f)["instagram"]

bot = socialbot.Instagram()
bot.login(credentials["username"], credentials["password"])
followers = bot.get_users("lunaelfica", max=50, action="follow")
bot.quit()