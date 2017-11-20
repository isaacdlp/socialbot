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


from selenium import webdriver as web
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from time import sleep
from random import randrange
import requests as req
from bs4 import BeautifulSoup as bs
import logging as lg


class SocialBot():

    base_url = None

    def __init__(self, driver=None, log_name="social_bot"):
        self.log = None
        self.handler = None
        self.formatter = lg.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.pauses = {
            "action": lambda: randrange(3, 6),
            "post": lambda: randrange(100, 301),
            "follow": lambda: randrange(30, 91),
            "unfollow": lambda: randrange(15, 61)
        }
        self.times = {}

        log = lg.getLogger(log_name)
        log.setLevel(lg.DEBUG)
        self.log = log
        if driver is None:
            options = Options()
            options.add_argument("log-level=3")
            options.add_argument("--disable-notifications")
            driver = web.Chrome(chrome_options=options)
        self.browser = driver
        self.browser.set_window_size(1000, 1000)
        super().__init__()

    def record(self, on=True, filename="social_bot.log"):
        if self.handler is None:
            self.handler = lg.FileHandler(filename)
            self.handler.setLevel(lg.DEBUG)
            self.handler.setFormatter(self.formatter)
        if on:
            self.log.addHandler(self.handler)
        else:
            self.log.removeHandler(self.handler)

    def quit(self):
        self.browser.quit()

    def next_time(self, event):
        self.times[event] = None
        if event in self.pauses:
            secs = self.pauses[event]
            if callable(secs):
                secs = secs()
            self.times[event] = datetime.now() + timedelta(seconds=secs)
        return self.times[event]

    def secs_until(self, event):
        secs = 0
        if event in self.times:
            secs = (self.times[event] - datetime.now()).total_seconds()
            #secs += 1
            if secs < 0:
                secs = 0
        return secs

    def ready_to(self, event):
        return not self.secs_until(event) > 0

    def wait_until(self, event):
        secs = self.secs_until(event)
        if secs > 0:
            sleep(secs)
        if event == "action":
            self.next_time(event)

    def wait_for(self, css_sel, css_base=None, loops=5, complain=True):
        if css_base is None:
            css_base = self.browser
        result = None
        for i in range(loops):
            try:
                result = css_base.find_element_by_css_selector(css_sel)
            except:
                pass
            self.wait_until("action")
        if complain and result is None:
            raise BaseException("The wait time expired")
        return result

    def go_home(self):
        self.browser.get(self.base_url)

    def _login(self, url, username, password, css_form, css_username, css_password):
        self.log.info("logging in as %s in %s" % (username, url))
        self.browser.get(url)
        form = self.browser.find_element_by_css_selector(css_form)
        self.wait_until("action")
        input_username = form.find_element_by_css_selector(css_username)
        input_username.send_keys(username)
        self.wait_until("action")
        input_password = form.find_element_by_css_selector(css_password)
        input_password.send_keys(password)
        self.wait_until("action")
        form.find_element_by_tag_name("button").click()

    def _logged(self, css_selector):
        # html = self.browser.find_element_by_tag_name("html")
        # self.lang = html.get_attribute("lang")[0:2]
        try:
           self.wait_for(css_selector)
           return True
        except:
            return False

    def set_cookies(self, cookies, domain=None):
        self.go_home()
        for cookie in cookies:
            if domain is None or domain in cookie["domain"]:
                self.browser.add_cookie(cookie)
        self.go_home()

    def _get_cards(self, url, max, offset, css_deck, css_card, css_scroll="window.scrollTo(0, document.body.scrollHeight)"):
        cards = []
        if url is not None:
            self.browser.get(url)
        total = max + offset
        deck = self.wait_for(css_deck, complain=False)
        if deck is None:
            return cards    # account may be private
        prev_count = -1
        count = 0
        cards = []
        while (count > prev_count and (max == 0 or count < total)):
            prev_count = count
            self.browser.execute_script(css_scroll, deck)
            self.wait_until("action")
            cards = deck.find_elements_by_css_selector(css_card)
            count = len(cards)
            self.log.debug("%s %i cards" % (url, count))
        cards = cards[offset:-1]
        if max > 0 and len(cards) > max:
            cards = cards[0:max]
        return cards


class Facebook(SocialBot):

    base_url = "https://facebook.com"

    def login(self, username, password):
        self._login("%s/login" % self.base_url, username, password,
                    "form#login_form", "input#email", "input#pass")

    def logged(self):
        return self._logged("a._606w")

    def search_posts(self, terms, max=0, offset=0, action=None):
        cards = self._get_cards("%s/search/str/%s/stories-keyword/stories-public" % (self.base_url, terms), max, offset,
                                "div#browse_result_area", "div._401d")
        return self._clean_posts(cards, "a._3084", "span._5-jo", action)

    def search_users(self, terms, max=0, offset=0, action=None):
        cards = self._get_cards("%s/search/people/?q=%s" % (self.base_url, terms), max, offset, "div#browse_result_area", "div._3u1")
        return self._clean_users(cards, action)

    def get_posts(self, handle, max=0, offset=0, action=None):
        cards = self._get_cards("%s/%s" % (self.base_url, handle), max, offset,
                                "div#recent_capsule_container", "div.userContentWrapper")
        return self._clean_posts(cards, "span.fwb a", "div.userContent", action)

    def get_users(self, handle, max=0, offset=0, action=None, blacklist=[]):
        cards = self._get_cards("%s/%s/friends" % (self.base_url, handle), max, offset,
                                "div._3i9", "li._698")
        return self._clean_users(cards, action, blacklist)

    def _clean_users(self, cards, action=None, blacklist=[]):
        items = []
        try:
            for card in cards:
                name = card.find_element_by_css_selector("a._ohe").get_attribute("href")
                name = name[25:name.index("?")].lower()
                if name in blacklist:
                    continue
                if callable(action):
                    action(card, items)
                else:
                    items.append(name)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items

    def _clean_posts(self, cards, css_link, css_msg, action=None):
        items = []
        try:
            for card in cards:
                post = {}
                post["link"] = card.find_element_by_css_selector(css_link).get_attribute("href")
                post["msg"] = card.find_element_by_css_selector(css_msg).text
                if callable(action):
                   action(card, items)
                else:
                    items.append(post)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items


class Twitter(SocialBot):

    base_url = "https://twitter.com"

    buttons = {
        "follow" : "button.follow-text",
        "unfollow" : "button.following-text"
    }

    def login(self, username, password):
        self._login("%s/login" % self.base_url, username, password,
                     "form.signin", "input[name='session[username_or_email]']", "input[name='session[password]'")

    def logged(self):
        return self._logged("a#user-dropdown-toggle")

    def post(self, msg):
        self.go_home()
        button = self.wait_for("button#global-new-tweet-button")
        self.browser.execute_script("arguments[0].click();", button)
        panel = self.wait_for("div.modal-tweet-form-container")
        panel.find_element_by_css_selector("div#tweet-box-global").send_keys(msg)
        self.wait_until("post")
        button = panel.find_element_by_css_selector("button.js-tweet-btn")
        self.browser.execute_script("arguments[0].click();", button)
        self.log.info("Posted %s" % msg)
        self.next_time("post")
        self.wait_until("action")

    # deck options are "top" and "tweets" (latest)
    def search_posts(self, terms, max=0, offset=0, deck="top", action=None):
        q = "%s/search?q=%s" % (self.base_url, terms)
        if deck != "top":
            q = "%s&f=%s" % (q, deck)
        cards = self._get_cards(q, max, offset, "div.stream-container", "li.js-stream-item")
        return self._clean_posts(cards, action)

    def search_users(self, terms, max=0, offset=0, action=None, blacklist=[], no_followers=True):
        cards = self._get_cards("%s/search?q=%s&f=users" % (self.base_url, terms), max, offset,
                                "div.GridTimeline-items", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, no_followers)

    # deck options are "" (tweets), "with_replies" and "media"
    def get_posts(self, handle, max=0, offset=0, deck="", action=None):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, handle, deck), max, offset,
                                "div.stream-container", "div.js-actionable-tweet")
        return self._clean_posts(cards, action)

    # deck options are "following" and "followers"
    def get_users(self, handle, max=0, offset=0, deck="followers", action=None, blacklist=[], no_followers=True):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, handle, deck), max, offset,
                                "div.GridTimeline-items", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, no_followers)

    def get_user(self, handle, action=None, no_followers=True):
        self.browser.get("%s/%s" % (self.base_url, handle))
        card = self.wait_for("div.ProfileHeaderCard")
        follows_you = len(card.find_elements_by_css_selector("span.FollowStatus")) > 0
        nav = self.browser.find_element_by_css_selector("div.ProfileNav")
        if not (no_followers and follows_you):
            self._user_actions(handle, nav, action)
        user = {"handle": handle, "follows_you": follows_you, "id": nav.get_attribute("data-user-id")}
        user["username"] = card.find_element_by_css_selector("a.ProfileHeaderCard-nameLink").text
        bio = self.wait_for("p.ProfileHeaderCard-bio", card, 1, False)
        if bio is not None:
            user["blocked"] = False
            user["bio"] = bio.text
            follow = self.wait_for(self.buttons["follow"], nav, 1, False)
            if follow is not None:
                user["you_follow"] = not follow.is_displayed()
        else:
            user["blocked"] = True
            self.log.warning("No profile for %s! Blocked?" % handle)
        return user

    # deck options are "members" and "subscribers"
    def get_list(self, handle, list_name, max=0, offset=0, deck="members", action=None, blacklist=[]):
        cards = self._get_cards("%s/%s/lists/%s/%s" % (self.base_url, handle, list_name, deck), max, offset,
                                "div.stream-container", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, False)

    # action options "follow" and "unfollow"
    def _clean_users(self, cards, action=None, blacklist=[], no_followers=True):
        items = []
        try:
            for card in cards:
                name = card.get_attribute("data-screen-name").lower()
                if name in blacklist:
                    continue
                follows_you = len(card.find_elements_by_css_selector("span.FollowStatus")) > 0
                if not (no_followers and follows_you):
                    self._user_actions(name, card, action, items)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items

    def _user_actions(self, name, card, action, items=[]):
        if action is not None:
            if callable(action):
                action(card, items)
            else:
                button = self.wait_for(self.buttons[action], card, 1, False)
                if button is None:
                    self.log.warning("No button for %s! Me?" % name)
                elif button.is_displayed():
                    self.wait_until(action)
                    self.browser.execute_script("arguments[0].click();", button)
                    self.next_time(action)
                    items.append(name)
                    self.log.info("%s %s" % (action, name))
        else:
            items.append(name)

    def _clean_posts(self, cards, action=None):
        items = []
        try:
            for card in cards:
                post = {}
                post["id"] = card.get_attribute("data-tweet-id")
                post["author"] = card.get_attribute("data-screen-name").lower()
                post["retweet"] = card.get_attribute("data-retweet-id")
                retweeter = card.get_attribute("data-retweeter")
                if retweeter is not None:
                    retweeter = retweeter.lower()
                post["retweeter"] = retweeter
                post["msg"] = card.find_element_by_css_selector("p.tweet-text").text
                post["pinned"] = len(card.find_elements_by_css_selector("span.js-pinned-text")) > 0
                post["media"] = len(card.find_elements_by_css_selector("div.js-media-container")) > 0 or \
                                 len(card.find_elements_by_css_selector("div.AdaptiveMediaOuterContainer")) > 0
                if callable(action):
                    action(post, items)
                else:
                    items.append(post)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items

    # deck options are "followers", "following", "likes", "lists"
    def fast_get(self, handle, position=None, max=0, deck="followers", list_name=None):
        items = []
        session = req.Session()
        session.headers["User-Agent"] = self.browser.execute_script('return navigator.userAgent')
        for cookie in self.browser.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])
        initial_url = "%s/%s/%s" % (self.base_url, handle, deck)
        stream_url = "%s/users" % initial_url
        style_data = "div.GridTimeline-items"
        if deck == "likes" or deck == "lists":
            if deck == "lists":
                initial_url = "%s/%s/%s/%s/members" % (self.base_url, handle, deck, list_name)
            stream_url = "%s/timeline" % initial_url
            style_data = "div#timeline div.stream-container"
        res = session.get(initial_url)
        html = bs(res.content, "html.parser")
        min_position = int(html.select(style_data)[0]["data-min-position"])
        init_position = min_position
        try:
            count = 0
            do_end = False
            cards = None
            while True:
                if cards is not None:
                    self.wait_until("action")
                    res = session.get("%s?include_available_features=1&include_entities=1&max_position=%i" % (stream_url, min_position))
                    html = bs(res.json()["items_html"], "html.parser")
                    min_position = int(res.json()["min_position"])
                cards = html.select(".js-stream-item")
                for card in cards:
                    if deck == "likes":
                        items.append(card["data-item-id"])
                    else:
                        items.append(card.select(".js-actionable-user")[0]["data-screen-name"].lower())
                    count += 1
                    if max > 0 and count >= max:
                        do_end = True
                        break
                self.log.debug("Items %i cursor %i for %s %s" % (count, min_position, handle, deck))
                if do_end or min_position == 0 or (position is not None and min_position <= position):
                    break
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items, init_position


class Instagram(SocialBot):

    base_url = "https://www.instagram.com"

    buttons = {
        "follow" : "_gexxb",
        "unfollow" : "_t78yp"
    }

    def login(self, username, password):
        self._login("%s/accounts/login" % self.base_url, username, password,
                     "form._3jvtb", "input[name='username']", "input[name='password'")

    def logged(self):
        return self._logged("span.coreSpriteSearchIcon")

    def search_posts(self, term, max=0, offset=0, action=None):
        cards = self._get_cards("%s/explore/tags/%s" % (self.base_url, term), max, offset, "div._cmdpi", "div._mck9w")
        return self._clean_posts(cards, action)

    # max 100 users
    def search_users(self, term, max=0, offset=0, action=None, blacklist=[]):
        self.go_home()
        self.wait_until("action")
        input = self.browser.find_element_by_css_selector("input._avvq0")
        input.send_keys(term)
        cards = self._get_cards(None, max, offset, "div._etpgz", "a._gimca", "arguments[0].scrollTop = arguments[0].scrollHeight")
        items = []
        try:
            for card in cards:
                if not "/explore/tags/" in card.get_attribute("href"):
                    name = card.find_element_by_css_selector("span._sgi9z").text.lower()
                    if name in blacklist:
                        continue
                    if callable(action):
                        action(card, items)
                    else:
                        items.append(name)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items

    def get_posts(self, handle, max=0, offset=0, action=None):
        cards = self._get_cards("%s/%s" % (self.base_url, handle), max, offset, "div._cmdpi", "div._mck9w")
        return self._clean_posts(cards, action)

    # deck options are "following" and "followers" | action options "follow" and "unfollow"
    def get_users(self, handle, max=0, offset=0, deck="followers", action=None, blacklist=[]):
        self.browser.get("%s/%s" % (self.base_url, handle))
        self.wait_until("action")
        links = self.browser.find_elements_by_css_selector("a._t98z6")
        pos = 0
        if deck == "following":
            pos = 1
        links[pos].click()
        cards = self._get_cards(None, max, offset, "div._gs38e", "li._6e4x5", "arguments[0].scrollTop = arguments[0].scrollHeight")
        items = []
        try:
            for card in cards:
                name = card.find_element_by_css_selector("a._2g7d5").text.lower()
                if name in blacklist:
                    continue
                self._user_action(name, card, action, items)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items

    def get_user(self, handle, action=None):
        self.browser.get("%s/%s" % (self.base_url, handle))
        card = self.wait_for("header._mainc")
        self._user_action(handle, card, action)
        user = {"handle": handle}
        user["username"] = card.find_element_by_css_selector("h2._kc4z2").text
        return user

    def _user_action(self, name, card, action, items=[]):
        if action is not None:
            if callable(action):
                action(card, items)
            else:
                button = self.wait_for("button", card, 1, False)
                if button is None:
                    self.log.warning("No button for %s! Me?" % name)
                else:
                    classes = button.get_attribute("class")
                    if self.buttons[action] in classes:
                        self.wait_until(action)
                        button.click()
                        self.next_time(action)
                        items.append(name)
                        self.log.info("%s %s" % (action, name))
        else:
            items.append(name)

    def _clean_posts(self, cards, action):
        items = []
        try:

            for card in cards:
                post = {}
                post["link"] = card.find_element_by_css_selector("a").get_attribute("href")
                img = card.find_element_by_css_selector("img")
                post["msg"] = img.get_attribute("alt")
                post["img"] = img.get_attribute("src")
                if callable(action):
                    action(post, items)
                else:
                    items.append(post)
        except BaseException as ex:
            self.log.error("%s" % str(ex))
        return items