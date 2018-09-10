# this module implements the website scanner
import os
from multiprocessing import Queue
import re
import requests
import time
from urllib.parse import urlsplit

from scraper import Scraper


class Spider:
    def __init__(self, url, domain, limit, limit_param, log_dir, sema):
        """
        Create instance of Spider.

        :param url: website url
        :param domain: domain of website
        :param limit: crawling limit type ("depth" or "count")
        :param limit_param: limit parameter (max depth or max number of pages)
        :param log_dir: directory path to store log and result
        :param sema: semaphore (used for release action)
        """
        self._sema = sema  # a semaphore

        self._url = url
        self._domain = domain

        # set limit properties
        self.limit = limit
        self.limit_param = limit_param

        # pages scanned count
        self.count = 0

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

    def _check_depth(self, u):
        """
        Check if depth of path exceeded limit.

        :param u: url
        :return: True if depth exceeded limit, else False
        """
        path = urlsplit(u).path
        return path.count("/") > self.limit_param

    def _check_count(self):
        """
        Check if pages scanned count reached limit.

        :return: True if count reached, else False
        """
        return self.count >= self.limit_param

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
                log_file.write("\t[-] Failure to request: {} | Connection Error.\n".format(link))
            self._finished = True
            return list()

        m = re.match(r"^text/", check_head.headers.get("Content-Type", ""))
        if not m:
            return list()

        # log the scanning
        with open(self._log_file_path, "a") as log_file:
            log_file.write("\t[*] Scanning {}\n".format(link))

        # increase page scanned count
        self.count += 1

        try:
            r = requests.get(link)
        except requests.ConnectionError:
            # log connection failure
            with open(self._log_file_path, "a") as log_file:
                log_file.write("\t[-] Failure to request: {} | Connection Error.\n".format(link))
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

            # check if link crossed crawling limit
            if self.limit == "depth":
                if self._check_depth(link):
                    self._finished = True
                    continue
            if self.limit == "count":
                if self._check_count():
                    self._finished = True
                    continue

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
            log_file.write("[*] Pages Scanned: {}\n".format(self.count))

        # the acquiring is done in the WebCrawler class before spawning the new process
        self._sema.release()
