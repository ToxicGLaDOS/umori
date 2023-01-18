import requests, unittest, subprocess, psycopg, os
from selenium import webdriver
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
import config
import convert_scryfall_to_sql
from flask import Flask
from flask_testing import LiveServerTestCase

USERNAME = 'test'
PASSWORD = 'password'
SIGNUP_PATH = '/signup'
COLLECTION_PATH = f'/{USERNAME}/collection'
COLLECTION_ADD_PATH = f'/{USERNAME}/collection/add'

def get_style_subattribute(attr:str, element: WebElement) -> str|None:
    style = element.get_attribute('style')
    for setting in style.split(';'):
        if attr in setting:
            name, value = [setting.strip() for setting in setting.split(':')]
            if name == attr:
                return value

    return None


# These tests can be done without a pre-existing user
class UserlessTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        delete_dynamic_data()

    def setUp(self):
        self.driver = webdriver.Chrome()

    def create_app(self):
        import main

        app = main.app
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = 8943
        # Default timeout is 5 seconds
        app.config['LIVESERVER_TIMEOUT'] = 10
        return app

    def test_create_user(self):
        self.driver.get(self.get_server_url() + SIGNUP_PATH)
        username_input = self.driver.find_element(By.ID, "username")
        password_input = self.driver.find_element(By.ID, "password")

        wait = WebDriverWait(self.driver, 3)

        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.RETURN)

        # Make sure we get redirected to our collection
        wait.until(EC.url_contains(COLLECTION_PATH))

class UserTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        delete_dynamic_data()

    def setUp(self):
        self.driver = webdriver.Chrome()

        # Create a user
        self.driver.get(self.get_server_url() + SIGNUP_PATH)
        username_input = self.driver.find_element(By.ID, "username")
        password_input = self.driver.find_element(By.ID, "password")

        wait = WebDriverWait(self.driver, 3)

        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.RETURN)

        # Make sure we get redirected to our collection
        wait.until(EC.url_contains(COLLECTION_PATH))

    def create_app(self):
        import main

        app = main.app
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = 8943
        # Default timeout is 5 seconds
        app.config['LIVESERVER_TIMEOUT'] = 10
        return app

    # This test is basically a comprehensive test
    # for the whole system end to end.
    def test_add_card(self):
        self.driver.get(self.get_server_url() + COLLECTION_ADD_PATH)

        wait = WebDriverWait(self.driver, 3)
        wait.until(EC.url_contains(COLLECTION_ADD_PATH))

        search = self.driver.find_element(By.ID, "search")
        fine_filter = self.driver.find_element(By.ID, "fine-filter")
        card_display = self.driver.find_element(By.ID, "card-display")
        first_card_xpath = '//*[@id="card-display"]/div[1]'

        wait.until(
            EC.presence_of_element_located((By.XPATH, first_card_xpath))
        )
        first_card = self.driver.find_element(By.XPATH, first_card_xpath)
        # We use professor onyx because she's unlikely to be reprinted
        # which might break some tests that depend assume a certain count
        # TODO: Fix bug where professor of symbology appears instead sometimes
        # this is probably a race condition with the abort controller stuff
        # that comes up when you type really fast.
        # This means that this test doesn't work 100% of the time,
        # but this seems to only happen ~10% of the time or so
        search.send_keys("professor onyx")
        wait.until(
            EC.staleness_of(first_card)
        )
        wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "card-div"))
        )
        wait.until(
            EC.text_to_be_present_in_element((By.XPATH, first_card_xpath + '/div[1]'), 'Professor Onyx')
        )
        cards = card_display.find_elements(By.XPATH, "child::node()")

        self.assertEqual(len(cards), 5)

        # Filter down to the promo one
        fine_filter.send_keys('stx:276')

        hidden_cards = [card for card in cards if get_style_subattribute('display', card) == 'none']
        visible_cards = [card for card in cards if get_style_subattribute('display', card) != 'none']

        self.assertEqual(len(hidden_cards), len(cards) - 1)

        self.assertEqual(len(visible_cards), 1)

        selected_card = visible_cards[0]

        selected_card_text = selected_card.find_element(By.TAG_NAME, "div").text

        self.assertEqual(selected_card_text, 'Professor Onyx (stx:276)')

        fine_filter.send_keys(Keys.RETURN)

        modal = self.driver.find_element(By.XPATH, '//*[@id="myModal"]')
        wait.until(
            EC.visibility_of(modal)
        )

        quantity = self.driver.find_element(By.XPATH, '//*[@id="quantity-input"]')
        finish = Select(self.driver.find_element(By.XPATH, '//*[@id="finish-select"]'))
        condition = Select(self.driver.find_element(By.XPATH, '//*[@id="condition-select"]'))
        lang = Select(self.driver.find_element(By.XPATH, '//*[@id="lang-select"]'))
        signed = self.driver.find_element(By.XPATH, '//*[@id="signed-input"]')
        altered = self.driver.find_element(By.XPATH, '//*[@id="alter-input"]')
        notes = self.driver.find_element(By.XPATH, '//*[@id="notes"]')
        add_card = self.driver.find_element(By.XPATH, '//*[@id="commit-button"]')

        # Assert defaults are correct
        self.assertEqual(quantity.get_attribute('value'), '1')
        self.assertEqual(finish.first_selected_option.text, 'nonfoil')
        self.assertEqual(condition.first_selected_option.text, 'Near Mint')
        self.assertEqual(lang.first_selected_option.text, 'en')
        self.assertEqual(signed.get_property('checked'), False)
        self.assertEqual(altered.get_property('checked'), False)
        self.assertEqual(notes.get_property('value'), '')

        quantity.clear()
        quantity.send_keys('4')

        finish.select_by_visible_text('foil')
        condition.select_by_visible_text('Lightly Played')
        lang.select_by_visible_text('ja')

        signed.click()
        altered.click()

        notes.send_keys('Some text to test if this data is saved')
        add_card.click()

        wait.until(
            EC.invisibility_of_element(modal)
        )
        wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="notification-container"]/div[1]'))
        )

        notification = self.driver.find_element(By.XPATH, '//*[@id="notification-container"]/div[1]')

        self.assertIn('Success', notification.get_attribute('innerHTML'))

        # ******** AFTER THIS ANY VARIABLES THAT REFERENCE ELEMENTS ARE NO GOOD ********
        self.driver.get(self.get_server_url() + COLLECTION_PATH)


        card_display = self.driver.find_element(By.ID, "card-display")

        wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="card-display"]/child::node()'))
        )

        cards = card_display.find_elements(By.XPATH, "child::node()")

        self.assertEqual(len(cards), 1)

        card = cards[0]
        card_text = card.find_element(By.TAG_NAME, "div")
        self.assertEqual(card_text.text, 'Professor Onyx (4)')

        modal_open_button = card.find_element(By.XPATH, 'div[2]/div[1]/button[3]')

        modal_open_button.click()
        modal = self.driver.find_element(By.XPATH, '//*[@id="myModal"]')

        wait.until(
            EC.visibility_of(modal)
        )

        quantity = self.driver.find_element(By.XPATH, '//*[@id="quantity-input"]')
        finish = Select(self.driver.find_element(By.XPATH, '//*[@id="finish-select"]'))
        condition = Select(self.driver.find_element(By.XPATH, '//*[@id="condition-select"]'))
        lang = Select(self.driver.find_element(By.XPATH, '//*[@id="lang-select"]'))
        signed = self.driver.find_element(By.XPATH, '//*[@id="signed-input"]')
        altered = self.driver.find_element(By.XPATH, '//*[@id="alter-input"]')
        notes = self.driver.find_element(By.XPATH, '//*[@id="notes"]')
        save_button = self.driver.find_element(By.XPATH, '//*[@id="commit-button"]')

        # Assert data is correct and populated into the modal
        self.assertEqual(quantity.get_attribute('value'), '4')
        self.assertEqual(finish.first_selected_option.text, 'foil')
        self.assertEqual(condition.first_selected_option.text, 'Lightly Played')
        self.assertEqual(lang.first_selected_option.text, 'ja')
        self.assertEqual(signed.get_property('checked'), True)
        self.assertEqual(altered.get_property('checked'), True)
        self.assertEqual(notes.get_property('value'), 'Some text to test if this data is saved')

        quantity.clear()
        quantity.send_keys('7')

        finish.select_by_visible_text('nonfoil')
        condition.select_by_visible_text('Moderately Played')
        lang.select_by_visible_text('ko')

        signed.click()
        altered.click()

        notes.clear()
        notes.send_keys('Different text')
        save_button.click()

        wait.until(
            EC.invisibility_of_element(modal)
        )
        wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="notification-container"]/div[1]'))
        )

        notification = self.driver.find_element(By.XPATH, '//*[@id="notification-container"]/div[1]')

        self.assertIn('Updated', notification.get_attribute('innerHTML'))

        # Check that our changes were saved and update properly
        modal_open_button.click()

        wait.until(
            EC.visibility_of(modal)
        )

        # This seems like it should be unnecessary because we haven't changed pages
        # but without this, we get errors about stale HTML elements.
        # I'm not sure why though
        quantity = self.driver.find_element(By.XPATH, '//*[@id="quantity-input"]')
        finish = Select(self.driver.find_element(By.XPATH, '//*[@id="finish-select"]'))
        condition = Select(self.driver.find_element(By.XPATH, '//*[@id="condition-select"]'))
        lang = Select(self.driver.find_element(By.XPATH, '//*[@id="lang-select"]'))
        signed = self.driver.find_element(By.XPATH, '//*[@id="signed-input"]')
        altered = self.driver.find_element(By.XPATH, '//*[@id="alter-input"]')
        notes = self.driver.find_element(By.XPATH, '//*[@id="notes"]')

        # Assert data is updated and populated into the modal
        self.assertEqual(quantity.get_attribute('value'), '7')
        self.assertEqual(finish.first_selected_option.text, 'nonfoil')
        self.assertEqual(condition.first_selected_option.text, 'Moderately Played')
        self.assertEqual(lang.first_selected_option.text, 'ko')
        self.assertEqual(signed.get_property('checked'), False)
        self.assertEqual(altered.get_property('checked'), False)
        self.assertEqual(notes.get_property('value'), 'Different text')

    #TODO: Write tests for:
    # Make sure card appears in modal
    # Make sure card in modal changes when you change language
    # Generating api tokens
    # Using api tokens
    # Failures (not passing data, passing incorrect data, etc.)
    # Plus and minus buttons on cards in collection

    def tearDown(self):
        self.driver.close()

# Deletes data in the database that changes
# (so basically everything but the cards)
def delete_dynamic_data():
    with get_database_connection() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM Collections')
        cur.execute('DELETE FROM Users')
        con.commit()


def get_database_connection():
    con = psycopg.connect(user = config.get('DB_USER'), password = config.get('DB_PASSWORD'), host = config.get('DB_HOST'), port = config.get('DB_PORT'))
    return con

if __name__ == '__main__':
    # TODO: Move initial database setup tasks to a function
    # so we don't have to do this
    # Import to do initial setup
    import main
    unittest.main()
