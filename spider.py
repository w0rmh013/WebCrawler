# this module implements the website scanner
from multiprocessing import Lock, Queue
import re
import requests
from time import time
from threading import Thread
from urllib.parse import urlsplit

from scraper import Scraper


class Spider:
    def __init__(self, url, domain, limit, limit_param, result_file_name, max_threads, sema, verbose):
        """
        Create instance of Spider.

        :param url: website url
        :param domain: domain of website
        :param limit: crawling limit type ("depth" or "count")
        :param limit_param: limit parameter (max depth or max number of pages)
        :param result_file_name: file to store results in
        :param max_threads: maximum number of threads per process
        :param sema: semaphore (used for release action)
        :param verbose: verbosity of Spider
        """
        # note: the locks are necessary for the parallel work and updating of variables
        self._emails_file_path = result_file_name

        self._max_threads = max_threads

        self._sema = sema  # a semaphore

        self._url = Scraper.create_http_link(urlsplit(url))  # starting url should also be encoded
        self._domain = domain

        # set limit properties
        self.limit = limit
        self.limit_param = limit_param

        # pages scanned count
        self._count = 0
        self._count_lock = Lock()  # lock count variable

        # create links-to-visit queue
        self._to_visit = Queue()
        self._to_visit.put(self._url)

        self._scraper = Scraper(self._domain, url)  # spider's links scraper
        self._emails = list()  # list of emails already found (no need to use hash list since emails are usually short)
        self._email_lock = Lock()  # lock to emails file

        self.verbose = verbose

    def _get_emails(self, content):
        """
        Find all email addresses in the current data with regex pattern.

        :param content: web page content
        """
        # emails that match the regex pattern
        emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", content))

        self._email_lock.acquire(True)

        with open(self._emails_file_path, "a") as emails_file:
            for email in emails:
                # we want to avoid duplicate email addresses
                if email not in self._emails:
                    self._emails.append(email)
                    emails_file.write(email+"\n")

        self._email_lock.release()

    def _exceeded_depth(self, u):
        """
        Check if depth of path exceeded limit.

        :param u: url
        :return: True if depth exceeded limit, else False
        """
        path = urlsplit(u).path
        return path.count("/") > self.limit_param

    def _reached_count(self):
        """
        Check if pages scanned count reached limit.

        :return: True if count reached, else False
        """
        return self._count >= self.limit_param

    def _limit_reached(self, u):
        """
        Check if link met limit condition.

        :param u: url
        :return: True if limit condition met, else False
        """
        if self.limit == "depth":
            return self._exceeded_depth(u)
        if self.limit == "count":
            return self._reached_count()


    def _scan(self, link):
        """
        Scan a page to get emails and update links queue.

        :param link: link to web page
        """
        # send HTTP HEAD request to check that content-type is text
        # this should save bandwidth and time since we won't waste get requests on images, etc.
        try:
            check_head = requests.head(link)

            m = re.match(r"^text/", check_head.headers.get("Content-Type", ""))
            if m:
                # increase page scanned count
                self._count_lock.acquire(True)
                self._count += 1
                self._count_lock.release()

                # request page
                r = requests.get(link)

                # update emails
                self._get_emails(r.text)

                # add new links to queue
                for new_link in self._scraper.get_hyperlinks(r.text):
                    self._to_visit.put(new_link)

        except requests.ConnectionError:
            # connection failure
            pass

    def _crawl(self):
        """
        Start crawling in the domain.
        """
        thread_list = list()

        while not self._to_visit.empty():

            # first spawning of threads
            while not self._to_visit.empty() and len(thread_list) < self._max_threads:
                link = self._to_visit.get()
                if self._limit_reached(link):
                    break

                t = Thread(target=Spider._scan, args=(self, link))
                thread_list.append(t)
                t.start()

            # if while loop didn't break
            else:
                # main thread spawning
                while any(t.is_alive() for t in thread_list):
                    i = 0
                    spawned = False
                    while i < len(thread_list) and not spawned:

                        # if a thread is not alive, we want to spawn a new one to replace him
                        if not thread_list[i].is_alive():
                            thread_list.pop(i)

                            # get new link if link queue is not empty
                            if not self._to_visit.empty():
                                link = self._to_visit.get()

                                if self._limit_reached(link):
                                    break

                                t = Thread(target=Spider._scan, args=(self, link))
                                thread_list.append(t)
                                t.start()
                                spawned = True

                        i += 1

    def crawl(self):
        """
        Wrapper for _crawl method.
        """
        t = time()
        self._crawl()
        if self.verbose:
            print("[*] Log: {} | Pages Scanned: {}".format(self._domain, self._count))
            print("[*] Log: {} | Time: {} Seconds".format(self._domain, time()-t))

        # the acquiring is done in the WebCrawler class before spawning the new process
        self._sema.release()

        # clean queue to end process
        while not self._to_visit.empty():
            self._to_visit.get()
