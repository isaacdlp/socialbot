import sys, os, json
import socialbot
import logging as lg

basename = os.path.splitext(os.path.basename(sys.argv[0]))[0]
bot_type = basename.split("-")[1]

action = "unfollow"
if len(sys.argv) > 1:
    action = sys.argv[1]

with open("%s-targets.json" % basename, "r") as f:
    targets = json.load(f)

with open("%s-credentials.json" % basename, "r") as f:
    credentials = json.load(f)

cookies = None
try:
    with open("%s-cookies.json" % basename, "r") as f:
        cookies = json.load(f)
except:
    print("No cookie found")

whitelist = []
try:
    with open("%s-whitelist.json" % basename, "r") as f:
        whitelist = json.load(f)
except:
    print("No whitelist found")

blacklist = []
try:
    with open("%s-blacklist.json" % basename, "r") as f:
        blacklist = json.load(f)
except:
    print("No blacklist found")

# Instance bot

if bot_type == "twitter":
    bot = socialbot.Twitter(log_name=basename)
elif bot_type == "instagram":
    bot = socialbot.Instagram(log_name=basename)
else:
    bot = socialbot.Facebook(log_name=basename)

# Login or use cookie

username = credentials["username"]

if cookies is not None:
    bot.set_cookies(cookies, bot_type)
else:
    bot.login(username, credentials["password"])

bot.record(True, "%s.log" % basename)

# Actions

if bot.logged():
    try:
        if action == "follow":
            # Follow
            num_total = 0
            for target in targets:
                followers = bot.get_users(target, max=100, action="follow", blacklist=blacklist)
                num = len(followers)
                print("%i from %s" % (num, target))
                num_total += num
            print("%i total" % num_total)

        elif action == "posts":
            # Display posts
            username = sys.argv[2]
            posts = bot.get_posts(username, max=1000)
            print(posts)

        elif action == "search":
            # List by Search Term
            term = sys.argv[2]
            followers = bot.search_users(term, max=1000, blacklist=blacklist)
            print("%i total" % len(followers))

        elif action == "unfollow":
            # Unfollow
            following = bot.get_users(username, max=1000, offset=1000, deck="following", action="unfollow", blacklist=whitelist)
            print("%i total" % len(following))
            blacklist += following
            with open("%s-blacklist.json" % basename, "w") as f:
                json.dump(blacklist, f)
    except Exception as ex:
        print(ex)

# Save cookie

cookies = bot.browser.get_cookies()
with open("%s-cookies.json" % basename, "w") as f:
    json.dump(cookies, f)

# Quit

bot.quit()
print("Done")