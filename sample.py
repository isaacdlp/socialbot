import json
import socialbot
from random import shuffle

bot_type = "twitter"

with open("credentials.json", "r") as f:
    credentials = json.load(f)[bot_type]

if bot_type == "twitter":
    bot = socialbot.Twitter()
elif bot_type == "instagram":
    bot = socialbot.Instagram()
else:
    bot = socialbot.Facebook()

# Login

bot.login(credentials["username"], credentials["password"])

# Follow

targets = ["carlosdoblado"]
while len(targets) > 0:
    target = targets.pop()
    followers = bot.get_users(target, max=1000, action="follow")
    if len(targets) == 0:
        targets += followers
        shuffle(targets)
bot.quit()

# Unfollow

bot.get_users("isaacdlp", max=1000, action="unfollow")

# Quit

bot.quit()