import json
import socialbot
from random import shuffle

with open("credentials.json", "r") as f:
    credentials = json.load(f)["twitter"]

bot = socialbot.Twitter()
bot.login(credentials["username"], credentials["password"])

targets = ["carlosdoblado"]
while len(targets) > 0:
    target = targets.pop()
    followers = bot.get_users(target, max=100, action="follow")
    if len(targets) == 0:
        targets += followers
        shuffle(targets)
bot.quit()