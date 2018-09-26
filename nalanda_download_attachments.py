"""
Author: drk
Used to download attachments from Nalanda 
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs
import os
from getpass import getpass

session = requests.session()


def status(result_status):
    """This just for status"""
    if result_status:
        return "Ok."
    return "Fail."


def get_oauth_url():
    """Extract the OAUTH2 URL with Session key."""
    # GET Request to Nalanda Login Page
    r = session.get("http://nalanda.bits-pilani.ac.in/login/index.php")
    # Use BS and extract the URL (identified by the class)
    return BeautifulSoup(r.text, 'html.parser').find('a', class_="btn").get('href')


def extract_form(html):
    """Extract the form from given HTML page using BS and
    return the FORM ACTION URL and the INPUT PORT PARAMETERS"""
    user_form = BeautifulSoup(html, 'html.parser').find('form')
    action = user_form.get('action')
    payload = {input_.get('name'): input_.get('value') for input_ in user_form.find_all('input', {'name': True})}
    return action, payload


def oauth_authenticate(oauth_url, username, password):
    """OAUTH Authentication with GOOGLE"""

    r = session.get(oauth_url)  # GET the Google Authentication URL
    print('Nalanda ..', status(r.ok))

    action, payload = extract_form(r.text)  # Extract the form from Google Login Page (Username Page)
    payload['Email'] = username     # Fill in the EMAIL address
    r = session.post(action, data=payload)  # Post the form
    print('Username ..', status(r.ok))

    action, payload = extract_form(r.text)  # Extract the form from Google Login Page (Password Page)
    payload['Passwd'] = password         # Fill in the PASSWORD
    r = session.post(action, data=payload)      # Authenticate with Google .. if successful, will forward to Nalanda
    print("Authenticating. ", status(r.ok))

    print("\n\nRegistered Courses: ")       # Just Print the Registered Courses extracted using BS
    courses_registered = {a.text for a in BeautifulSoup(r.text, 'html.parser').select('.media-heading > a')}
    for course_registered in courses_registered:
        print("\t\t%s" % course_registered)


def get_course_details(course_box):
    """Takes a div with class 'coursebox' in Nalanda which contains
    the course details and extracts relevant fields"""
    url = course_box.find("a").get("href")  # Extract the course page url
    course_id = parse_qs(urlparse(url).query)['id']     # Extract the course id (a number) useful for further requests
    teacher = ''    # This is to display teachers of a course
    if course_box.find("ul", class_='teachers'):    # Some courses don't have a teacher field
        teacher = course_box.find("ul", class_='teachers').find('a').text   # update where ever present
    # return the course details of each course
    return {
        "title": course_box.find("a").text.replace("/", "|").strip(),   # get the course title
        "url": url,                 # return a dictionary with relevant details extracted
        "course_id": course_id,     # COURSE ID, TEACHER, URL, TITLE
        "teacher": teacher
    }


def search_courses(search_string):
    """Searches for courses on Nalanda with contains the search string"""
    # Send a get request to Nalanda with search string as parameter
    payload = {"search": search_string, "perpage": "all"}
    r = session.get("http://nalanda.bits-pilani.ac.in/course/search.php", params=payload)
    # Extract all the courses matching the search string
    course_boxes = BeautifulSoup(r.text, "html.parser").select(".coursebox")
    # Construct a list of courses details of courses matching the search string
    return [get_course_details(course_box)
            for course_box in course_boxes]


def request_course_input():
    """Requests input search string from user and
        obtains the course for with user interested to download attachments"""
    while True:
        print("\nJust press ENTER to exit.")
        search_string = input("\nEnter Course Name:")     # Input the search string
        if not search_string:  # If no input string logout
            return None
        courses = search_courses(search_string)         # Get the matching courses
        if not courses:     # if no matching courses
            print("No courses were found with words '%s'" % search_string)  # Inform
            continue
        # Display the matching courses
        for index, course in enumerate(courses, 1):
            print("%3d] %50s (%s)" % (index, course["title"], course["teacher"]))
        # Just a while loop to make sure user selects a valid course
        while True:
            print("Enter 'G' to go back.")
            print("Enter 'X' to exit.")
            input_string = input("Enter Course Number:")
            if input_string == 'G':     # if want to search some other search string
                break
            elif input_string == 'X':   # if no more searching
                return None
            elif not str.isnumeric(input_string):   # Check if input is a number
                print("\033[031;1mERROR:\033[0m\033[031m ENTER A NUMBER.\033[0m")
            elif not 0 < int(input_string) <= len(courses):
                print("\033[031;1mERROR:\033[0m\033[031m NUMBER `NOT IN RANGE`.\033[0m")
            else:
                return courses[int(input_string)-1]     # Return the requested course


def fetch_attachments(course_id):
    """Fetch all attachment urls for a given course id.
    Note: This only explores Attachment resources from Resource Page Documents and Folders"""
    # Go the resources page of course in Nalanda
    r = session.get("http://nalanda.bits-pilani.ac.in/course/resources.php", params={"id": course_id})
    attachment_urls = {}    # This will contain all Attachment URLS
    for a in BeautifulSoup(r.text, 'html.parser').find_all('a'):    # Get all a tags in page
        link = a.get('href')    # Get the url
        folder_name = a.text.strip()    # Construct the folder name to download to
        if '/mod/resource/view.php' in link:    # Check if url is pointing to document
            if folder_name not in attachment_urls:
                attachment_urls[folder_name] = []
            attachment_urls[folder_name].append(link)   # Append it the folder to which it will be downloaded
        elif '/mod/folder/view.php' in link:    # Check if url pointing to folder
            if folder_name not in attachment_urls:
                attachment_urls[folder_name] = []
            attachment_urls[folder_name].extend(get_attachments_from_folder(link))  # extract all links from folder

    return attachment_urls      # return all urls found along with folders to download to


def get_attachments_from_folder(folder_link):
    """Gets the attachment urls from given folder url"""
    r = session.get(folder_link)    # GET the folder url
    links = [a.get('href') for a in BeautifulSoup(r.text, 'html.parser').find_all('a')]     # Get all links
    attachment_links = [link for link in links if '/mod_folder/content/' in link]       # Filter for attachments
    return attachment_links


def download_attachment(attachment_url, filepath):
    """Saves the attachment pointed by url to a file in the specified directory"""
    r = session.get(attachment_url)
    if 'Content-Disposition' in r.headers:
        # Get the filename from Content=Disposition Header
        filename = re.findall("filename=(.+)", r.headers['Content-Disposition'])[0].replace('"', '')
        # Write bytes of content to file
        with open(os.path.join(filepath, filename), 'wb') as f:
            f.write(r.content)
        return filename


def download_attachments(course_title, attachment_urls):
    """Downloads the attachments to corresponding folder structure"""
    if attachment_urls:
        os.makedirs(course_title, exist_ok=True)    # Make the folder structure if not exists
        for folder_name in attachment_urls:
            folder_path = os.path.join(course_title, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            for attachment_url in attachment_urls[folder_name]:   # Download attachment to corresponding folder
                filename = download_attachment(attachment_url, folder_path)
                if filename:        # Print the location of download
                    print("Downloaded '%s' To '%s'" % (filename, folder_path))
    else:   # if nothing to download
        print("Nothing to Download ..")


def nalanda_logout():
    """Logout from nalanda"""
    r = session.get("http://nalanda.bits-pilani.ac.in/my/")
    # Get the logout url with session key
    logout_url = [a.get('href') for a in BeautifulSoup(r.text, 'html.parser').find_all('a')
                  if '/login/logout.php' in a.get('href')][0]
    r = session.get(logout_url)
    print("Logout .. ", status(r.ok))


# Get the OAUTH Url
oauth = get_oauth_url()

# Get the USERNAME and PASSWORD either from environment variables or from command line
username = os.getenv("EMAIL_USERNAME")
if not username:
    username = input("USERNAME:")
password = os.getenv("EMAIL_PASSWORD")
if not password:
    password = getpass("PASSWORD:")

# Authenticate with google oauth
oauth_authenticate(oauth, username, password)

while True:
    # request for input course
    course = request_course_input()
    if course is None:
        # If no more course to search
        nalanda_logout()
        session.close()
        exit(0)
    # fetch all attachments
    attachment_urls = fetch_attachments(course['course_id'])

    # download the attachments
    download_attachments(course['title'], attachment_urls)
