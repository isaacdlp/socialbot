from selenium import webdriver as web
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from time import sleep
from random import randrange


class SocialBot():

    base_url = None

    pauses = {
        "action": lambda: randrange(1, 4),
        "post": lambda: randrange(100, 301),
        "follow": lambda: randrange(30, 91),
        "unfollow": lambda: randrange(10,31)
     }

    times = {}

    actions = {}

    def __init__(self, driver=None):
        if driver is None:
            options = Options()
            options.add_argument("--disable-notifications")
            driver = web.Chrome(chrome_options=options)
        self.browser = driver
        self.browser.set_window_size(1000, 1000)
        super().__init__()

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

    def wait_until(self, event):
        secs = self.secs_until(event)
        if secs > 0:
            sleep(secs)
        if event == "action":
            self.next_time(event)

    def wait_for(self, css_sel, loops=5, complain=True):
        result = None
        for i in range(loops):
            self.wait_until("action")
            try:
                result = self.browser.find_element_by_css_selector(css_sel)
            except:
                pass
        if complain and result is None:
            raise BaseException("The wait time expired")
        return result

    def go_home(self):
        self.browser.get(self.base_url)

    def _login(self, url, username, password, css_form, css_username, css_password):
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

    def get_posts(self, username, max=0, offset=0, action=None):
        cards = self._get_cards("%s/%s" % (self.base_url, username), max, offset,
                                "div#recent_capsule_container", "div.userContentWrapper")
        return self._clean_posts(cards, "span.fwb a", "div.userContent", action)

    def get_users(self, username, max=0, offset=0, action=None, blacklist=[]):
        cards = self._get_cards("%s/%s/friends" % (self.base_url, username), max, offset,
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
        except:
            pass
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
        except:
            pass
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
    def get_posts(self, username, max=0, offset=0, deck="", action=None):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, username, deck), max, offset,
                                "div.stream-container", "div.js-actionable-tweet")
        return self._clean_posts(cards, action)

    # deck options are "following" and "followers"
    def get_users(self, username, max=0, offset=0, deck="followers", action=None, blacklist=[], no_followers=True):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, username, deck), max, offset,
                                "div.GridTimeline-items", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, no_followers)

    # deck options are "members" and "subscribers"
    def get_list(self, username, listname, max=0, offset=0, deck="members", action=None, blacklist=[]):
        cards = self._get_cards("%s/%s/lists/%s/%s" % (self.base_url, username, listname, deck), max, offset,
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
                if action is not None:
                    if callable(action):
                        action(card, items)
                    else:
                        try:
                            button = card.find_element_by_css_selector(self.buttons[action])
                        except:
                            print("No button! Me?")
                            continue
                        if button.is_displayed():
                            if no_followers:
                                follower = card.find_elements_by_css_selector("span.FollowStatus")
                                if len(follower) > 0:
                                    continue
                            self.wait_until(action)
                            self.browser.execute_script("arguments[0].click();", button)
                            self.next_time(action)
                            items.append(name)
                            print("%s %s" % (action, name))
                else:
                    items.append(name)
        except:
            pass
        return items

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
        except:
            pass
        return items


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
        except:
            pass
        return items

    def get_posts(self, username, max=0, offset=0, action=None):
        cards = self._get_cards("%s/%s" % (self.base_url, username), max, offset, "div._cmdpi", "div._mck9w")
        return self._clean_posts(cards, action)

    # deck options are "following" and "followers" | action options "follow" and "unfollow"
    def get_users(self, username, max=0, offset=0, deck="followers", action=None, blacklist=[]):
        self.browser.get("%s/%s" % (self.base_url, username))
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
                if action is not None:
                    if callable(action):
                        action(card, items)
                    else:
                        try:
                            button = card.find_element_by_css_selector("button")
                        except:
                            print("No button! Me?")
                            continue
                        classes = button.get_attribute("class")
                        if self.buttons[action] in classes:
                            self.wait_until(action)
                            button.click()
                            self.next_time(action)
                            items.append(name)
                            print("%s %s" % (action, name))
                else:
                    items.append(name)
        except:
            pass
        return items

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
        except:
            pass
        return items