from datetime import datetime
from random import randint, shuffle
from sys import argv, exit
from threading import Thread, currentThread

from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver


def parse_arguments():
    if "--help" in argv:
        print("usage: python -m szkolneblogi-bot [arguments]\n")
        print("arguments:")
        print("--url        -u      url of the blog")
        print(
            "--likes      -l      determines how many times will the bot like each article"
        )
        print("--threads    -t      the number of browser windows used by the bot")
        print("--headless   -h      start the program without browser gui")
        print("--log-file   -f      determine a file to which save all log outputs")
        print("--help               display this help message")
        exit()

    parsed = {
        "url": "",
        "likes-per-article": 5,
        "threads": 1,
        "log_filename": None,
        "headless": False,
    }

    for argument in range(len(argv)):
        if "--url" == argv[argument] or "-u" == argv[argument]:
            parsed["url"] = argv[argument + 1]
        if "--likes" == argv[argument] or "-l" == argv[argument]:
            parsed["likes-per-article"] = int(argv[argument + 1])
        if "--log-file" == argv[argument] or "-f" == argv[argument]:
            parsed["log_filename"] = argv[argument + 1]
        if "--threads" == argv[argument] or "-t" == argv[argument]:
            parsed["threads"] = int(argv[argument + 1])
        if "--headless" == argv[argument] or "-h" == argv[argument]:
            parsed["headless"] = True

    if parsed["url"] == "":
        parsed["url"] = ask_input("URL of the blog: ", log_file=parsed["log_filename"])
    return parsed


def current_time():
    return str(datetime.now().strftime("%H:%M:%S"))


def log_info(message, log_file=None):
    print("<" + currentThread().name + "> " + current_time() + " [INFO] " + message)
    if log_file:
        open(log_file, "a").write(
            "<"
            + currentThread().name
            + "> "
            + current_time()
            + " [INFO] "
            + message
            + "\n"
        )


def log_warning(message, log_file=None):
    print("<" + currentThread().name + "> " + current_time() + " [WARNING] " + message)
    if log_file:
        open(log_file, "a").write(
            "<"
            + currentThread().name
            + "> "
            + current_time()
            + " [WARNING] "
            + message
            + "\n"
        )


def log_error(message, log_file=None):
    print("<" + currentThread().name + "> " + current_time() + " [ERROR] " + message)
    if log_file:
        open(log_file, "a").write(
            "<"
            + currentThread().name
            + "> "
            + current_time()
            + " [ERROR] "
            + message
            + "\n"
        )


def ask_input(message, log_file=None):
    typed = input(
        "<" + currentThread().name + "> " + current_time() + " [INPUT] " + message
    )
    if log_file:
        open(log_file, "a").write(
            "<"
            + currentThread().name
            + "> "
            + current_time()
            + " [INPUT] "
            + message
            + typed
            + "\n"
        )
    return typed


def generate_webdriver(headless=False, log_file=None):
    options = webdriver.FirefoxOptions()
    if headless:
        log_info("Started in headless mode", log_file=log_file)
        options.add_argument("-headless")
    return webdriver.Firefox(firefox_options=options)


def generate_fake_ip():
    return (
        str(randint(1, 100))
        + "."
        + str(randint(0, 255))
        + "."
        + str(randint(0, 255))
        + "."
        + str(randint(0, 255))
    )


def interceptor(request):
    bad_scripts = [
        "/static/js/gemius.js",
        "/static/external/select2/select2.min.js",
        "/static/external/jquery.datetimepicker.js",
        "/static/external/select2/select2_locale_pl.js",
        "/static/external/jquery-selectbox.js",
        "/static/external/slick.min.js",
        "/static/js/home.js",
        "/static/js/slick.init.js",
        "/static/js/tagging.js",
        "/static/js/cookie-banner.js",
        "/static/js/commentaries.js" "/static/js/common.js",
        "/static/js/utils.js",
    ]
    # blocks all unnecessary elements to speed up the load times
    if (
        "szkolneblogi.pl" not in request.url
        or request.path.endswith((".png", ".jpg", ".gif", ".ico", ".css"))
        or request.path in bad_scripts
    ):
        request.abort()
    # Spoofs the ip so that you can like the articles from the same ip multiple times
    fake_ip = generate_fake_ip()
    request.headers["X-Forwarded-For"] = fake_ip
    request.headers["Via"] = "1.1 " + fake_ip


def get_last_blog_page(driver, current_url):
    driver.get(current_url + "?page=last")
    return int(driver.find_element_by_class_name("current").text)


def get_articles(driver):
    # iterates through all articles on the current page, deletes the one that's an ad and shuffles the rest
    current_page_articles = []
    for goto_comments_link in driver.find_elements_by_class_name("goto-comments"):
        current_page_articles.append(goto_comments_link.get_attribute("href")[:-9])
    del current_page_articles[0]
    shuffle(current_page_articles)
    return current_page_articles


def like(driver, log_file=None):
    while True:
        # tries to click the like button
        # If this fail due to a timeout, this means that this article has already been liked from this ip
        try:
            WebDriverWait(driver, 5).until(
                ec.presence_of_element_located((By.CLASS_NAME, "like-it"))
            )
            likes = int(driver.find_element_by_class_name("like-it").text) + 1
            driver.find_element_by_class_name("like-it").click()
            WebDriverWait(driver, 5).until(
                ec.presence_of_element_located((By.ID, "id_answer"))
            )
        except TimeoutException:
            log_warning("Already liked this article from this ip", log_file=log_file)
            return
        # while the captcha is present try one of the 3 possible answers
        try:
            while driver.find_element_by_class_name("captcha-answer").is_displayed():
                try:
                    possible_answer = driver.find_elements_by_class_name(
                        "captcha-answer"
                    )[randint(3, 5)].text
                    driver.find_elements_by_id("id_answer")[1].send_keys(
                        possible_answer
                    )
                    driver.find_element_by_id("form.actions.submit").click()
                except (
                    StaleElementReferenceException,
                    ElementNotInteractableException,
                    NoSuchElementException,
                ):
                    return
        except IndexError:
            log_info("Liked the article (" + str(likes) + " likes)", log_file=log_file)
            return


def worker(settings):
    driver = generate_webdriver(
        headless=settings["headless"], log_file=settings["log_filename"]
    )
    driver.request_interceptor = interceptor
    last_blog_page = get_last_blog_page(driver, settings["url"])

    while True:
        try:
            page_number = str(randint(1, last_blog_page))
            page_url = settings["url"] + "?page=" + page_number
            driver.get(page_url)
            articles = get_articles(driver)
            log_info(
                "Loaded " + str(len(articles)) + " articles from page " + page_number,
                log_file=settings["log_filename"],
            )

            for article in articles:
                driver.get(article)
                log_info(
                    'Article "' + article + '" loaded',
                    log_file=settings["log_filename"],
                )
                for i in range(settings["likes-per-article"]):
                    like(driver, log_file=settings["log_filename"])
                    driver.refresh()
        except:
            driver.quit()
            return


if __name__ == "__main__":
    settings = parse_arguments()

    threads = []
    for thread in range(settings["threads"]):
        threads.append(Thread(target=worker, args=[settings]))

    for t in threads:
        t.start()
