from selenium import webdriver as web
from datetime import datetime, timedelta
from time import sleep


class SocialBot():

    pauses = {
        "action": 2,
        "follow": 60,
        "unfollow": 30
    }

    times = {}

    lang = "en"

    actions = {}

    login_url, login_form, login_username, login_password, login_proof, user_url, user_pos, user_lists, user_deck, \
    user_scroll, user_card = [None] * 11

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
            secs += 1
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

    def login(self, username, password):
        self.browser.get(self.login_url)
        form = self.browser.find_element_by_css_selector(self.login_form)
        self.wait_until("action")
        input_username = form.find_element_by_css_selector(self.login_username)
        input_username.send_keys(username)
        self.wait_until("action")
        input_password = form.find_element_by_css_selector(self.login_password)
        input_password.send_keys(password)
        self.wait_until("action")
        form.find_element_by_tag_name("button").click()
        self.wait_for(lambda: self.browser.find_element_by_css_selector(self.login_proof))
        html = self.browser.find_element_by_tag_name("html")
        self.lang = html.get_attribute("lang")[0:2]

    def get_cards(self, username, max=0, list="followers"):
        cards = []
        pos = None
        if list in self.user_pos:
            pos = self.user_pos[list]
        self.browser.get(self.user_url % username)
        self.wait_until("action")
        links = self.browser.find_elements_by_css_selector(self.user_lists)
        links[pos].click()
        deck = self.wait_for(lambda: self.browser.find_element_by_css_selector(self.user_deck), complain=False)
        if deck is None:
            return cards    # account may be private
        prev_count = -1
        count = 0
        cards = []
        while (count > prev_count and (max == 0 or count < max)):
            prev_count = count
            self.browser.execute_script(self.user_scroll, deck)
            self.wait_until("action")
            cards = deck.find_elements_by_css_selector(self.user_card)
            count = len(cards)
        if max > 0 and len(cards) > max:
            cards = cards[0:max]
        return cards


class Twitter(SocialBot):

    login_url = "https://twitter.com/login"
    login_form = "form.signin"
    login_username = "input[name='session[username_or_email]']"
    login_password = "input[name='session[password]'"
    login_proof = "a#user-dropdown-toggle"

    user_url = "https://www.twitter.com/%s"
    user_pos = {
        "following": 1,
        "followers": 2
    }
    user_lists = "a.ProfileNav-stat--link"
    user_deck = "div.GridTimeline"
    user_scroll = "window.scrollTo(0, document.body.scrollHeight)"
    user_card = "div.ProfileCard"

    buttons = {
        "follow" : "button.follow-text",
        "unfollow" : "button.following-text"
    }

    def get_users(self, username, max=0, list="followers", action=None):
        names = []
        cards = self.get_cards(username, max, list)
        for card in cards:
            name = card.find_element_by_css_selector("b.u-linkComplex-target").text
            names.append(name)
            if action is not None:
                if callable(action):
                    action(card)
                else:
                    button = card.find_element_by_css_selector(self.buttons[action])
                    if button.is_displayed():
                        self.wait_until(action)
                        self.browser.execute_script("arguments[0].click();", button)
                        self.next_time(action)
                        print("%s %s" % (action, name))
        return names


class Instagram(SocialBot):

    login_url = "https://www.instagram.com/accounts/login"
    login_form = "form._3jvtb"
    login_username = "input[name='username']"
    login_password = "input[name='password'"
    login_proof = "span.coreSpriteSearchIcon"

    user_url = "https://www.instagram.com/%s"
    user_pos = {
        "following": 1,
        "followers": 0
    }
    user_lists = "a._t98z6"
    user_deck = "div._gs38e"
    user_scroll = "arguments[0].scrollTop = arguments[0].scrollHeight"
    user_card = "li._6e4x5"

    buttons = {
        "follow" : "_gexxb",
        "unfollow" : "_t78yp"
    }

    def get_users(self, username, max=0, list="followers", action=None):
        names = []
        cards = self.get_cards(username, max, list)
        for card in cards:
            name = card.find_element_by_css_selector("a._2g7d5").text
            names.append(name)
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
                        print("%s %s" % (action, name))
        return names