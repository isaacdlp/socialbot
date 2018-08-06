# Copyright (c) 2017 Isaac de la Pena (isaacdlp@alum.mit.edu)
#
# Open-sourced according to the MIT LICENSE
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import sys, os, json
from random import shuffle, choice
import logging as lg
import socialbot
from random import randrange


chatter = ["like", "quote", "reply"]
bot_alias = "sample"
bot_type = "twitter"
action = "smart_unfollow"
param = None
msg = ""

action = "like"
param = "928739950828425217"

if len(sys.argv) > 1:
    bot_alias = sys.argv[1]
    bot_type = sys.argv[2]
    if len(sys.argv) > 3:
        action = sys.argv[3]
        if len(sys.argv) > 4:
            param = sys.argv[4]
            if len(sys.argv) > 5:
                msg = sys.argv[5]

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
        if action == "smart_whitelist":
            # Smart Update whitelist
            # python bot.py sample twitter smart_whitelist vip
            members, pos = bot.fast_get(username, deck="lists", list_name=param)

            with open("%s-whitelist.json" % basename, "w") as f:
                json.dump(members, f, indent=2)

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
                json.dump(targets, f, indent=2)
            print("%i total" % num_total)

        elif action == "smart_unfollow":
            # Smart Unfollow ("total" param will unfollow even if they follow you)
            # python bot.py sample twitter unfollow 300 total
            if param is None:
                param = 0
            else:
                param = int(param)
            no_followers = True
            if len(sys.argv) > 4:
                no_followers = False
            dumps, pos = bot.fast_get(username, deck="following")
            following = []
            for dump in reversed(dumps):
                if dump not in whitelist:
                    try:
                        bot.get_user(dump, action="unfollow", no_followers=no_followers)
                        following.append(dump)
                        if param > 0 and len(following) >= param:
                            break
                    except:
                        bot.log.warning("ERROR with %s" % dump)
            print("%i total" % len(following))
            blacklist += following
            with open("%s-blacklist.json" % basename, "w") as f:
                json.dump(list(set(blacklist)), f)

        if action == "whitelist":
            # Update whitelist
            # python bot.py sample twitter whitelist vip
            members = bot.get_list(username, param)
            with open("%s-whitelist.json" % basename, "w") as f:
                json.dump(members, f, indent=2)

        elif action == "follow":
            # Follow
            # python bot.py sample twitter follow 1000
            if param is None:
                param = 100
            with open("%s-targets.json" % basename, "r") as f:
                targets = json.load(f)
            num_total = 0
            for target in targets:
                followers = bot.get_users(target, max=int(param), action="follow", blacklist=blacklist)
                num = len(followers)
                print("%i from %s" % (num, target))
                num_total += num
            print("%i total" % num_total)

        elif action == "search_posts":
            # Search_posts
            # python bot.py sample twitter search_posts 1000 %23fintech%20near%3A%22Madrid%2C%20Spain%22%20within%3A300mi
            if param is None:
                param = 100
            if msg is None:
                raise BaseException("Search param cannot be empty")
            num = 0
            try:
                dumps = bot.search_posts(msg, max=int(param), deck="tweets")
                authors = []
                for dump in dumps:
                    if dump["author"] not in authors:
                       authors.append(dump["author"])
                shuffle(authors)
                for author in authors:
                    if author not in blacklist:
                        try:
                            bot.get_user(author, action="follow")
                            num += 1
                        except:
                            bot.log.warning("ERROR with %s" % author)
            except BaseException as ex:
                bot.log.warning("ERROR %s" % str(ex))
            print("%i total" % num)

        elif action == "search_people":
            # Search_people
            # python bot.py sample twitter search_people 1000 %23fintech%20near%3A%22Madrid%2C%20Spain%22%20within%3A300mi
            if param is None:
                param = 100
            if msg is None:
                raise BaseException("Search param cannot be empty")
            followers = bot.search_users(msg, max=int(param), action="follow", blacklist=blacklist)
            num = len(followers)
            print("%i discovered" % num)

        elif action == "unfollow":
            # Unfollow (note that the param is the offset)
            # python bot.py sample twitter unfollow 300
            if param is None:
                param = 0
            following = bot.get_users(username, max=1000, offset=int(param), deck="following", action="unfollow", blacklist=whitelist)
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

        elif action == "post":
            # Post a message
            # python bot.py sample twitter post "Your twitter message"
            bot.post(param)

        elif action == "chatter" or action in chatter or action == "unlike" or action == "unquote":
            # Actions on a message
            # python bot.py sample twitter quote 937285136240074752 "A message worth a retweet"
            act = action
            if action == "chatter":
                act = choice(chatter)
            bot.get_post(param, act, msg)

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
        raise ex
        #print(ex)

# Save cookie

cookies = bot.browser.get_cookies()
with open("%s-cookies.json" % basename, "w") as f:
    json.dump(cookies, f, indent=2)

# Quit

bot.quit()
print("Done")