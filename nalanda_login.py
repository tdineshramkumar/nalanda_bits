"""
    Author: drk
    Automate Nalanda Login Using Selenium
"""
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from getpass import getpass
import os


WAIT_TIMEOUT = 100   # seconds
# Enter G-MAIL Login Details for Nalanda

# Get the USERNAME and PASSWORD either from environment variables or from command line
username = os.getenv("EMAIL_USERNAME")
if not username:
    username = input("USERNAME:")
password = os.getenv("EMAIL_PASSWORD")
if not password:
    password = getpass("PASSWORD:")

# Open Firefox
driver = webdriver.Firefox()

# Go to Nalanda Login Website
driver.get("http://nalanda.bits-pilani.ac.in/login/index.php")
driver.find_element_by_partial_link_text("BITS Email").click()

# Wait for GMAIL Page and Enter Username and Click Next
WebDriverWait(driver, WAIT_TIMEOUT).until(EC.visibility_of_element_located((By.ID, "identifierId")))
driver.find_element_by_id("identifierId").send_keys(username)
driver.find_element_by_id("identifierId").send_keys(Keys.ENTER)
# driver.find_element_by_id('identifierNext').click()

# Wait for password page and Enter Password and Click Next
WebDriverWait(driver, WAIT_TIMEOUT).until(EC.visibility_of_element_located((By.NAME, "password")))
driver.find_element_by_name("password").send_keys(password)
driver.find_element_by_name("password").send_keys(Keys.ENTER)
# driver.find_element_by_id("passwordNext").click()

# Now you have logged in into Nalanda
