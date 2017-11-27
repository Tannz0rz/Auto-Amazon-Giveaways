import datetime
import time
import getpass
import colorama
import json
from random import randint
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class GiveawayBot(object):
    def __init__(self):
        self.giveaways = set()
        try:
            with open('state.json', 'r') as file:
                self.giveaways = set(json.loads(file.read()))
        except IOError:
            print('No file state.json, passing.')
        colorama.init(autoreset=True)
        self.chromedriver = webdriver.Chrome('/home/casey/amazon-giveaway/chromedriver')
        self.chromedriver.implicitly_wait(4)
        self.instant_box = 'box_click_target'
        self.enter_button = 'enterSubmitForm'
        self.enter_poll = 'enterPollButton'
        self.tweet_id = 'ln_tw_tweet'
        self.tweet_enter_id = 'ts_tw_tweet'
        self.twitter_follow_id = 'lu_fo_follow'
        self.twitter_follow_enter_id = 'ts_fo_follow'
        self.next_button = '.a-last'
        self.auth_error_message = 'auth-error-message-box'
        self.auth_warning_message = 'auth-warning-message-box'
        self.won_giveaways = 0
        self.lost_giveaways = 0
        self.entered_giveaways = 0
        self.completed_giveaways = 0
        self.time_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.user_email_input = None
        self.user_password_input = None
        self.url = None

    def __enter__(self):
        self._login()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # self.chromedriver.quit()
        with open('state.json', 'w') as file:
            file.write(json.dumps([x for x in self.giveaways]))
        print("Exiting...")

    def _login(self, init=True):
        if init:
            self.user_email_input = raw_input("Enter your Amazon email address: ")
            self.user_password_input = getpass.getpass("Enter your Amazon password: ")
            self.chromedriver.get(
                'https://www.amazon.com/ap/signin?_encoding=UTF8&openid.assoc_handle=usflex&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.ns.pape=http%3A%2F%2Fspecs.openid.net%2Fextensions%2Fpape%2F1.0&openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2Fga%2Fgiveaways'
            )
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "\nLogging into Amazon..."),
        email = self.chromedriver.find_element_by_name('email')
        email.send_keys(self.user_email_input)
        password = self.chromedriver.find_element_by_name('password')
        password.send_keys(self.user_password_input)
        keep_signed_in = self.chromedriver.find_element_by_name('rememberMe')
        keep_signed_in.click()
        sign_in_submit = self.chromedriver.find_element_by_id('signInSubmit')
        sign_in_submit.click()

        if self._check_for_element_id(self.auth_error_message):
            print(colorama.Fore.RED + colorama.Style.BRIGHT + "Login Unsuccessful!\nExiting...")
            self.chromedriver.quit()
            exit(1)
        elif self._check_for_element_id(self.auth_warning_message):
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + "Login Unsuccessful!\nEnter credentials with Captcha or script will exit in 60 seconds...")
            time.sleep(60)
            self.chromedriver.quit()
            exit(1)

        print(colorama.Fore.GREEN + colorama.Style.BRIGHT + "Login Successful!  Continuing...")

    def _prize_name(self):
        prize_name = self.chromedriver.find_element_by_id('prize-name').text
        return str(prize_name.encode('utf-8')).replace('"', "")

    def process_page(self):
        page_count = 1
        while self._check_for_css_selector(self.next_button):
            print(colorama.Fore.CYAN + colorama.Style.BRIGHT + '\nProcessing GiveAways for Page: {}'.format(page_count))
            self._process_no_req_giveaways()
            self._process_tweet_giveaways()
            self._process_twitter_follow_giveaways()
            self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])
            next_page = self.chromedriver.find_element_by_css_selector(self.next_button)
            next_page.click()
            page_count += 1

        self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])

        # derived totals from global counter variables
        instant_giveaways = self.won_giveaways + self.lost_giveaways
        all_giveaways = instant_giveaways + self.entered_giveaways + self.completed_giveaways

        print('**** Script completed ****')
        print('Total won: {}'.format(self.won_giveaways))
        print('Total lost: {}'.format(self.lost_giveaways))
        print('Total entry giveaways: {}'.format(self.entered_giveaways))
        print('Total instant giveaways: {}'.format(instant_giveaways))
        print('Already completed giveaways: {}'.format(self.completed_giveaways))
        print('ALL giveaways: {}'.format(all_giveaways))

    def _did_you_win(self, title, prize_name):
        if 'you didn\'t win' in title:
            self.lost_giveaways += 1
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + '**** You did not win: {}'.format(prize_name))
        elif 'you\'re a winner!' in title:
            self.won_giveaways += 1
            print(colorama.Fore.GREEN + colorama.Style.BRIGHT + '**** Winner Winner! Chicken Dinner!: {}'.format(prize_name))
        elif 'your entry has been received' in title:
            self.entered_giveaways += 1
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + '**** You already entered: {}'.format(prize_name))
        else:
            print(colorama.Fore.RED + colorama.Style.BRIGHT + '---- UNRECOGNIZED RESPONSE FOR: {}'.format(prize_name))
        self.chromedriver.close()
        self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])

    def _open_tab(self, url):
        self.url = url
        self.chromedriver.execute_script('window.open(\'\');')
        self.chromedriver.switch_to.window(self.chromedriver.window_handles[1])
        self.chromedriver.get(self.url)
        if 'https://www.amazon.com/ap/signin' in self.chromedriver.current_url:
            self._login(init=False)
            self.chromedriver.get(self.url)

    def _check_for_element_id(self, element_id):
        self.chromedriver.implicitly_wait(0)
        try:
            self.chromedriver.find_element_by_id(element_id)
            self.chromedriver.implicitly_wait(4)
            return True
        except:
            self.chromedriver.implicitly_wait(4)
            return False

    def _check_for_css_selector(self, css_selector):
        self.chromedriver.implicitly_wait(0)
        try:
            self.chromedriver.find_element_by_css_selector(css_selector)
            self.chromedriver.implicitly_wait(4)
            return True
        except:
            self.chromedriver.implicitly_wait(4)
            return False

    def _instant_or_enter(self, prize_name):
        if 'https://www.amazon.com/ap/signin' in self.chromedriver.current_url:
            self._login(init=False)
            self.chromedriver.get(self.url)
            return self._instant_or_enter(prize_name)
        if prize_name in self.giveaways:
            print('**** Skipping ' + prize_name)
            self.chromedriver.close()
            self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])
            return
        is_instant = self._check_for_element_id(self.instant_box)
        is_enter = self._check_for_element_id(self.enter_button)
        giveaway_ended = self._check_for_element_id('giveaway-ended-header')
        if giveaway_ended:
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + '**** Giveaway for {} has already ended.'.format(prize_name))
            self.chromedriver.close()
            self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])
        elif is_instant and not is_enter:
            self._instant_giveaway(prize_name)
        elif not is_instant and is_enter:
            self._enter_giveaway(prize_name)
        else:
            self._did_you_win(self.chromedriver.find_element_by_id('title').text, prize_name)
        self.giveaways.add(prize_name)
        # time.sleep(randint(1, 5))

    def _instant_giveaway(self, prize_name):
        giveaway_box = self.chromedriver.find_element_by_id(self.instant_box)
        giveaway_box.click()
        time.sleep(6)
        self._did_you_win(self.chromedriver.find_element_by_id('title').text, prize_name)
    
    def _enter_giveaway(self, prize_name):
        enter_give_away = self.chromedriver.find_element_by_id(self.enter_button)
        enter_give_away.click()
        get_result = self.chromedriver.find_element_by_id('title')
        if 'your entry has been received' in get_result.text:
            self.entered_giveaways += 1
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + '    **** You have entered the GiveAway for: {}. You will receive an email if you won.'.format(prize_name))
        else:
            print('This shouldn\'t happen.  RUN!')
        self.chromedriver.close()
        self.chromedriver.switch_to.window(self.chromedriver.window_handles[0])
 
    # #TODO: Update method to handle poll giveaways
    # def _process_poll_giveaways(self):
    #     poll_giveaways = self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"Answer a poll")]')
    #     number_of_polls = str(len(poll_giveaways))
    #     print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "\n#### Number of 'Answer a poll' Requirement GiveAways found on this page: {}".format(number_of_polls))
    #     for ga in self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"Answer a poll")]'):
    #         # root_give_away = ga.find_element_by_xpath('./../..')
    #         # get_url = root_give_away.find_element_by_class_name('giveAwayItemDetails')
    #         # href = get_url.get_attribute('href')
    #         # self._open_tab(href)
    #         self._open_tab(ga.find_element_by_xpath('./../..').find_element_by_class_name('giveAwayItemDetails').get_attribute('href'))
    #         prize_name = self._prize_name()
    #         print(colorama.Fore.WHITE + colorama.Style.BRIGHT + '\n**** Processing GiveAway for: {}'.format(prize_name))
    #         self._instant_or_enter(prize_name)

    # function to process the 'None' requirement giveaways.
    def _process_no_req_giveaways(self):
        no_req_giveaways = self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"No entry requirement")]')
        print('no_req_giveaways: {}'.format([x.text for x in no_req_giveaways]))
        number_of_no_req = str(len(no_req_giveaways))
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "\n#### Number of 'No entry requirement' GiveAways found on this page: {}".format(number_of_no_req))
        for ga in self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"No entry requirement")]'):
            # root_give_away = ga.find_element_by_xpath('./../..')
            # get_url = root_give_away.find_element_by_class_name('giveAwayItemDetails')
            # href = get_url.get_attribute('href')
            # self._open_tab(href)
            self._open_tab(ga.find_element_by_xpath('./../../../..').find_element_by_class_name('giveAwayItemDetails').get_attribute('href'))
            prize_name = self._prize_name()
            print(colorama.Fore.WHITE + colorama.Style.BRIGHT + '\n**** Processing GiveAway for: {}'.format(prize_name))
            self._instant_or_enter(prize_name)


    # function to process the 'Tweet' requirement giveaways.
    def _process_tweet_giveaways(self):
        tweet_giveaways = self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"Tweet a message")]')
        number_of_tweet_req = str(len(tweet_giveaways))
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + '\n#### Number of \'Tweet a message\' Requirement GiveAways found on this page: {}'.format(number_of_tweet_req))
        # print "\n#### Number of 'Tweet a message' Requirement GiveAways found on this page:  %s" % number_of_tweet_req
        for ga in self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"Tweet a message")]'):
            root_give_away = ga.find_element_by_xpath('./../../../..')
            get_url = root_give_away.find_element_by_class_name('giveAwayItemDetails')
            href = get_url.get_attribute('href')
            self._open_tab(href)

            prize_name = self._prize_name()

            print(colorama.Fore.WHITE + colorama.Style.BRIGHT + '\n**** Processing GiveAway for: {}'.format(prize_name))

            if self._check_for_element_id(self.tweet_id) or self._check_for_element_id(self.tweet_enter_id):
                self.chromedriver.find_element_by_name('tweet').click()
                time.sleep(2)
            self._instant_or_enter(prize_name)

    # function to process the 'Twitter Follow' requirement giveaways.
    def _process_twitter_follow_giveaways(self):
        twitter_follow_giveaways = self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"on Twitter")]')
        number_of_twitter_follow_req = str(len(twitter_follow_giveaways))
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + '\n#### Number of \'Follow on Twitter\' Requirement GiveAways found on this page: {}'.format(number_of_twitter_follow_req))
        for ga in self.chromedriver.find_elements_by_xpath('//div//span[contains(.,"on Twitter")]'):
            root_give_away = ga.find_element_by_xpath('./../../../..')
            get_url = root_give_away.find_element_by_class_name('giveAwayItemDetails')
            href = get_url.get_attribute('href')
            self._open_tab(href)

            prize_name = self._prize_name()

            print(colorama.Fore.WHITE + colorama.Style.BRIGHT + '\n**** Processing GiveAway for: {}'.format(prize_name))

            if self._check_for_element_id(self.twitter_follow_id) or self._check_for_element_id(self.twitter_follow_enter_id):
                self.chromedriver.find_element_by_name('follow').click()
                time.sleep(2)
            self._instant_or_enter(prize_name)

def main():
    with GiveawayBot() as bot:
        bot.process_page()
    exit(0)

if __name__ == '__main__':
    main()
