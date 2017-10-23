import json
from time import sleep
from selenium import webdriver as web


class Instagram:

    def __init__(self):
        self.browser = web.Chrome()
        self.browser.set_window_size(1000, 1000)
        super().__init__()

    def login(self, username, password):
        self.browser.get("https://www.instagram.com/accounts/login")
        form = self.browser.find_element_by_tag_name("form")
        fields = form.find_elements_by_tag_name("input")
        fields[0].send_keys(username)
        fields[1].send_keys(password)
        form.find_element_by_tag_name("button").click()
        proof = []
        for i in range(30):
            proof = self.browser.find_elements_by_class_name("coreSpriteSearchIcon")
            if len(proof) > 0:
                break
            sleep(2)
        if len(proof) == 0:
            raise Exception("Failure login in")

    def get_users(self, username, max=0, list="followers", action=None):
        followers = []
        pos = 1
        if list != "followers":
            pos = 2

        self.browser.get("https://www.instagram.com/%s" % username)
        links = self.browser.find_elements_by_class_name("_t98z6")
        links[pos].click()
        sleep(2)
        try:
            overlay = self.browser.find_element_by_class_name("_gs38e")
        except:
            # account is private
            return followers
        prev_count = -1
        count = 0
        points = []
        while (count > prev_count and (max == 0 or count < max)):
            prev_count = count
            self.browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', overlay)
            sleep(1)
            points = overlay.find_elements_by_tag_name("li")
            count = len(points)
        for point in points:
            name = point.find_elements_by_tag_name("a")[1].text
            followers.append(name)
            if action is not None:
                if callable(action):
                    action(point)
                else:
                    try:
                        button = point.find_element_by_tag_name("button")
                        status = button.text
                    except:
                        continue
                    if action == "follow" and status == "Follow":
                        print("Following %s" % name)
                        button.click()
                        sleep(30)
                    elif action == "unfollow" and status != "Follow":
                        print("Unfollowing %s" % name)
                        button.click()
                        sleep(30)
        return followers


with open("credentials.json", "r") as f:
    credentials = json.load(f)

insta = Instagram()
insta.login(credentials["username"], credentials["password"])
followers = insta.get_users("lunaelfica", max=50, action="follow")
