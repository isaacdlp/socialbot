import json, os
from random import shuffle
import socialbot

basename = os.path.splitext(os.path.basename(__file__))[0]
bot_type = basename.split("-")[0]

with open("%s-credentials.json" % basename, "r") as f:
    credentials = json.load(f)

with open("%s-targets" % basename, "r") as f:
    targets = json.load(f)

with open("%s-blacklist.json" % basename, "r") as f:
    blacklist = json.load(f)

# Login

if bot_type == "twitter":
    bot = socialbot.Twitter()
elif bot_type == "instagram":
    bot = socialbot.Instagram()
else:
    bot = socialbot.Facebook()

bot.login(credentials["username"], credentials["password"])

# Follow

if False:
    targets = ["carlosdoblado"]
    while len(targets) > 0:
        target = targets.pop()
        followers = bot.get_users(target, max=1000, action="follow")
        if len(targets) == 0:
            targets += followers
            shuffle(targets)

# Unfollow

if False:
    bot.get_users("isaacdlp", max=1000, action="unfollow")

# Quit

bot.quit()