from selenium import webdriver as web
from datetime import datetime, timedelta
from time import sleep
from random import randrange


class SocialBot():

    pauses = {
        "action": lambda: randrange(1, 4),
        "follow": lambda: randrange(30, 91),
        "unfollow": lambda: randrange(15,46)
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
            raise ("The wait time expired")
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

    def _get_cards(self, url, max, list, css_pos, css_decks, css_deck, css_scroll, css_card):
        cards = []
        pos = None
        if list in css_pos:
            pos = css_pos[list]
        self.browser.get(url)
        self.wait_until("action")
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
        self.wait_for(lambda: self.browser.find_element_by_css_selector("a._606w"))
        #html = self.browser.find_element_by_tag_name("html")
        #self.lang = html.get_attribute("lang")[0:2]


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
        self.wait_for(lambda: self.browser.find_element_by_css_selector("a#user-dropdown-toggle"))

    def get_users(self, username, max=0, list="followers", action=None, blacklist=None, no_followers=True):
        names = []
        try:
            cards = self._get_cards("%s/%s" % (self.base_url, username), max, list,
                                    self.user_pos, "a.ProfileNav-stat--link", "div.GridTimeline",
                                     "window.scrollTo(0, document.body.scrollHeight)", "div.ProfileCard")
            for card in cards:
                name = card.find_element_by_css_selector("b.u-linkComplex-target").text
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
        except Exception as ex:
            print(ex)
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
        self.wait_for(lambda: self.browser.find_element_by_css_selector("span.coreSpriteSearchIcon"))

    def get_users(self, username, max=0, list="followers", action=None, blacklist=None):
        names = []
        try:
            cards = self._get_cards("%s/%s" % (self.base_url, username), max, list,
                                    self.user_pos, "a._t98z6", "div._gs38e",
                                     "arguments[0].scrollTop = arguments[0].scrollHeight", "li._6e4x5")
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