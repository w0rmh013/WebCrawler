# this module implements the website scanner
import os
from multiprocessing import Queue
import re
import requests
import time

from scraper import Scraper


class Spider:
    def __init__(self, url, domain, log_dir, sema):
        """
        Create instance of Spider.

        :param url: website url
        :param domain: domain of website
        :param log_dir: directory path to store log and result
        :param sema: semaphore (used for release action)
        """
        self._sema = sema  # a semaphore

        self._url = url
        self._domain = domain

        # create links-to-visit queue
        self._to_visit = Queue()
        self._to_visit.put(self._url)

        self._scraper = Scraper(self._domain, url)  # spider's links scraper
        self._emails = list()  # list of emails already found (no need to use hash list since emails are usually short)

        # current page content
        self._current_content = ""  # we save current content to reduce memory usage when passing the content to functions

        # create log dir
        self._log_dir = log_dir
        os.mkdir(self._log_dir)
        self._log_file_path = os.path.join(self._log_dir, "scan_log.txt")
        self._emails_file_path = os.path.join(self._log_dir, "emails.txt")

        self._finished = False  # check if crawler finished

    # @staticmethod
    # def get_domain(u):
    #     """
    #     Get domain from url (the method is static since we'll use it in WebCrawler to check for duplicate domains).
    #
    #     :param u: url
    #     :return: domain associated with the url
    #     """
    #     domain = urlsplit(u).netloc
    #     if domain == "":
    #         print("[-] Could not get a valid domain from {}".format(u))
    #         raise ValueError
    #     return domain

    def _get_emails(self):
        """
        Find all email addresses in the current data with regex pattern.
        """
        # emails that match the regex pattern
        emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", self._current_content))

        with open(self._emails_file_path, "a") as emails_file:
            for email in emails:
                # we want to avoid duplicate email addresses
                if email not in self._emails:
                    self._emails.append(email)
                    emails_file.write(email+"\n")

    def _scan(self, link):
        """
        Scan a page to get emails and new links.

        :param link: link to web page
        :return: list of new links to scan
        """
        # send HTTP HEAD request to check that content-type is text
        # this should save bandwidth and time since we won't waste get requests on images, etc.
        try:
            check_head = requests.head(link)
        except requests.ConnectionError:
            # log connection failure
            with open(self._log_file_path, "a") as log_file:
                log_file.writelines("[-] Failure to request: {} | Connection Error.\n".format(link))
            self._finished = True
            return list()

        m = re.match(r"^text/", check_head.headers.get("Content-Type", ""))
        if not m:
            return list()

        # log the scanning
        with open(self._log_file_path, "a") as log_file:
            log_file.writelines("[*] Scanning {}\n".format(link))

        try:
            r = requests.get(link)
        except requests.ConnectionError:
            # log connection failure
            with open(self._log_file_path, "a") as log_file:
                log_file.writelines("[-] Failure to request: {} | Connection Error.\n".format(link))
            self._finished = True
            return list()

        self._current_content = r.text
        self._get_emails()
        return self._scraper.get_hyperlinks(self._current_content)

    def _crawl(self):
        """
        Start crawling in the domain.
        """
        # start scanning website
        while not self._finished and not self._to_visit.empty():
            link = self._to_visit.get()

            # the new links are unvisited links
            for new_link in self._scan(link):
                self._to_visit.put(new_link)

    def crawl(self):
        """
        Wrapper for _crawl method.
        """
        self._finished = False
        # write initial log
        with open(self._log_file_path, "a") as log_file:
            log_file.write("[+][{}] Crawling started at domain: {}\n".format(time.strftime("%H:%M:%S %d/%m/%Y"), self._domain))

        self._crawl()

        self._finished = True
        # write final log
        with open(self._log_file_path, "a") as log_file:
            log_file.write("[+][{}] Crawling ended.\n".format(time.strftime("%H:%M:%S %d/%m/%Y")))

        # the acquiring is done in the WebCrawler class before spawning the new process
        self._sema.release()
