from selenium import webdriver as web
from datetime import datetime, timedelta
from time import sleep
from random import randrange


class SocialBot():

    base_url = None

    pauses = {
        "action": lambda: randrange(1, 4),
        "follow": lambda: randrange(30, 91),
        "unfollow": lambda: randrange(10,31)
    }

    times = {}

    actions = {}

    def __init__(self, driver=None):
        if driver is None:
            driver = web.Chrome()
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

    def wait_for(self, function, loops=5, complain=True):
        result = None
        for i in range(loops):
            self.wait_until("action")
            try:
                result = function()
            except:
                pass
        if complain and result is None:
            raise BaseException("The wait time expired")
        return result

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
           self.wait_for(lambda: self.browser.find_element_by_css_selector(css_selector))
           return True
        except:
            return False

    def set_cookies(self, cookies):
        self.browser.get(self.base_url)
        for cookie in cookies:
            self.browser.add_cookie(cookie)

    def _get_cards(self, url, max, css_deck, css_card, css_decks=None, pos=0, css_scroll="window.scrollTo(0, document.body.scrollHeight)"):
        cards = []
        self.browser.get(url)
        self.wait_until("action")
        if css_decks is not None:
            links = self.browser.find_elements_by_css_selector(css_decks)
            links[pos].click()
        deck = self.wait_for(lambda: self.browser.find_element_by_css_selector(css_deck), complain=False)
        if deck is None:
            return cards    # account may be private
        prev_count = -1
        count = 0
        cards = []
        while (count > prev_count and (max == 0 or count < max)):
            prev_count = count
            self.browser.execute_script(css_scroll, deck)
            self.wait_until("action")
            cards = deck.find_elements_by_css_selector(css_card)
            count = len(cards)
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


class Twitter(SocialBot):

    base_url = "https://twitter.com"

    user_pos = {
        "following": 1,
        "followers": 2
    }

    buttons = {
        "follow" : "button.follow-text",
        "unfollow" : "button.following-text"
    }

    def login(self, username, password):
        self._login("%s/login" % self.base_url, username, password,
                     "form.signin", "input[name='session[username_or_email]']", "input[name='session[password]'")

    def logged(self):
        return self._logged("a#user-dropdown-toggle")

    # deck options are "top" and "tweets" (latest)
    def search_tweets(self, terms, max=0, deck="top"):
        q = "%s/search?q=%s" % (self.base_url, terms)
        if deck != "top":
            q = "%s&f=%s" % (q, deck)
        cards = self._get_cards(q, max, "div.stream-container","li.js-stream-item")
        return cards

    def search_users(self, terms, max=0, action=None, blacklist=[], no_followers=True):
        cards = self._get_cards("%s/search?q=%s&f=users" % (self.base_url, terms), max,
                                "div.GridTimeline-items", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, no_followers)

    # deck options are "" (tweets), "with_replies" and "media"
    def get_tweets(self, username, max=0, deck=""):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, username, deck), max,
                                "div.stream-container", "li.js-stream-item")
        return cards

    # deck options are "following" and "followers"
    def get_users(self, username, max=0, deck="followers", action=None, blacklist=[], no_followers=True):
        cards = self._get_cards("%s/%s/%s" % (self.base_url, username, deck), max,
                                "div.GridTimeline-items", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, no_followers)

    # deck options are "members" and "subscribers"
    def get_list(self, username, listname, max=0, deck="members", action=None, blacklist=[]):
        cards = self._get_cards("%s/%s/lists/%s/%s" % (self.base_url, username, listname, deck), max,
                                "div.stream-container", "div.js-actionable-user")
        return self._clean_users(cards, action, blacklist, False)

    def _clean_users(self, cards, action=None, blacklist=[], no_followers=True):
        names = []
        try:
            for card in cards:
                name = card.get_attribute("data-screen-name")
                if name in blacklist:
                    continue
                if action is not None:
                    if callable(action):
                        action(card)
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
                            names.append(name)
                            print("%s %s" % (action, name))
                else:
                    names.append(name)
        except:
            pass
        return names


class Instagram(SocialBot):

    base_url = "https://www.instagram.com"

    user_pos = {
        "following": 1,
        "followers": 0
    }

    buttons = {
        "follow" : "_gexxb",
        "unfollow" : "_t78yp"
    }

    def login(self, username, password):
        self._login("%s/accounts/login" % self.base_url, username, password,
                     "form._3jvtb", "input[name='username']", "input[name='password'")

    def logged(self):
        return self._logged("span.coreSpriteSearchIcon")

    # deck options are "following" and "followers"
    def get_users(self, username, max=0, deck="followers", action=None, blacklist=[]):
        names = []
        try:
            cards = self._get_cards("%s/%s" % (self.base_url, username), max,
                                    "div._gs38e", "li._6e4x5",
                                    "a._t98z6", self.user_pos[deck], "arguments[0].scrollTop = arguments[0].scrollHeight")
            for card in cards:
                name = card.find_element_by_css_selector("a._2g7d5").text
                if name in blacklist:
                    continue
                if action is not None:
                    if callable(action):
                        action(card)
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
                            names.append(name)
                            print("%s %s" % (action, name))
                else:
                    names.append(name)
        except Exception as ex:
            print(ex)
        return names