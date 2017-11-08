import sys, os, json
from random import shuffle
import logging as lg
import socialbot
from random import randrange


# basename = os.path.splitext(os.path.basename(sys.argv[0]))[0]
bot_alias = "sample"
bot_type = "twitter"
action = "fast_dump"

if len(sys.argv) > 1:
    bot_alias = sys.argv[1]
    bot_type = sys.argv[2]
    if len(sys.argv) > 3:
        action = sys.argv[3]
        if len(sys.argv) > 4:
            param = sys.argv[4]

basename = "%s-%s" % (bot_alias, bot_type)

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
handler = lg.StreamHandler()
handler.setFormatter(bot.formatter)
handler.setLevel(lg.DEBUG)
bot.log.addHandler(handler)

# Actions

if bot.logged():
    try:
        if action == "whitelist":
            # Update whitelist
            # python bot.py sample twitter whitelist vip
            members = bot.get_list(username, param)
            with open("%s-whitelist.json" % basename, "w") as f:
                json.dump(members, f)

        elif action == "smart_follow":
            # Smart Follow (note that the param is the alternative max)
            # python bot.py sample twitter smart_follow 300
            if param is None:
                param = 0
            else:
                param = int(param)
            with open("%s-smtargets.json" % basename, "r") as f:
                targets = json.load(f)
            num_total = 0
            try:
                for target in targets:
                    num = 0
                    dumps, pos = bot.fast_get(target["@handle"], target["@pos"], param)
                    target["@pos"] = pos
                    shuffle(dumps)
                    for dump in dumps:
                        if dump not in blacklist:
                            try:
                                bot.get_user(dump, action="follow")
                                num += 1
                            except:
                                bot.log.warning("ERROR with %s" % dump)
                    num_total += num
            except BaseException as ex:
                bot.log.warning("ERROR %s" % str(ex))
            with open("%s-smtargets.json" % basename, "w") as f:
                json.dump(targets, f)
            print("%i total" % num_total)

        elif action == "smart_unfollow":
            # Smart Unfollow (note that the param is the max)
            # python bot.py sample twitter unfollow 300
            if param is None:
                param = 0
            else:
                param = int(param)
            dumps = bot.fast_get(username, max=param, deck="following")
            following = []
            for dump in reversed(dumps):
                if dump not in whitelist:
                    try:
                        bot.get_user(dump, action="unfollow", no_followers=False)
                        following.append(dump)
                    except:
                        bot.log.warning("ERROR with %s" % dump)
            print("%i total" % len(following))
            blacklist += following
            with open("%s-blacklist.json" % basename, "w") as f:
                json.dump(list(set(blacklist)), f)

        elif action == "follow":
            # Follow
            # python bot.py sample twitter follow
            with open("%s-targets.json" % basename, "r") as f:
                targets = json.load(f)
            num_total = 0
            for target in targets:
                followers = bot.get_users(target, max=100, action="follow", blacklist=blacklist)
                num = len(followers)
                print("%i from %s" % (num, target))
                num_total += num
            print("%i total" % num_total)

        elif action == "unfollow":
            # Unfollow (note that the param is the offset)
            # python bot.py sample twitter unfollow 300
            if param is None:
                param = 0
            else:
                param = int(param)
            following = bot.get_users(username, max=1000, offset=param, deck="following", action="unfollow", blacklist=whitelist)
            print("%i total" % len(following))
            blacklist += following
            with open("%s-blacklist.json" % basename, "w") as f:
                json.dump(list(set(blacklist)), f)

        elif action == "dump":
            # Dump a Deck
            # python bot.py sample twitter dump carlosdoblado
            members = bot.get_users(param)
            with open("%s-%s.json" % (bot_type, param), "w") as f:
                json.dump(members, f)

        elif action == "smart_dump":
            # Fast Dump a Deck (using HTTP API)
            # python bot.py sample twitter smart_dump carlosdoblado
            bot.pauses["action"] = lambda: randrange(1, 3)
            prev_pos = None
            prev_deck = []
            if os.path.isfile("%s-%s.json" % (bot_type, param)):
                with open("%s-%s.json" % (bot_type, param), "r") as f:
                    obj = json.load(f)
                    if "@pos" in obj:
                        prev_post = obj["@pos"]
                    if "@deck" in obj:
                        prev_deck = obj["@deck"]
            deck, pos = bot.fast_get(param, prev_pos)
            with open("%s-%s.json" % (bot_type, param), "w") as f:
                json.dump({
                    "@pos": pos,
                    "@deck": list(set(prev_deck + deck))
                }, f)

        elif action == "dump_follow":
            # Follow from a dumped (normal or smart) Deck
            # python bot.py sample twitter dump_follow carlosdoblado
            with open("%s-%s.json" % (bot_type, param), "r") as f:
                dumps = json.load(f)
                if "@deck" in dumps:
                    dumps = dumps["@deck"]
            shuffle(dumps)
            for dump in dumps:
                if dump not in blacklist:
                    try:
                        bot.get_user(dump, action="follow")
                    except:
                        bot.log.warning("ERROR with %s" % dump)

        elif action == "posts":
            # Display posts by Search Term
            # python bot.py sample twitter posts finanzas
            posts = bot.get_posts(param, max=1000)
            print(posts)

        elif action == "users":
            # Display users by Search Term
            # python bot.py sample twitter users finanzas
            followers = bot.search_users(param, max=1000, blacklist=blacklist)
            print("%i total" % len(followers))
    except Exception as ex:
        print(ex)

# Save cookie

cookies = bot.browser.get_cookies()
with open("%s-cookies.json" % basename, "w") as f:
    json.dump(cookies, f)

# Quit

bot.quit()
print("Done")