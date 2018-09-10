# this module implements the web crawler for a list of urls and manages the spiders
from multiprocessing import Process, Semaphore
import os
import string
import time
from urllib.parse import urlsplit

from spider import Spider


class WebCrawler:
    def __init__(self, urls, log_dir=os.getcwd(), max_processes=10, verbose=False):
        """
        Create instance of WebCrawler.

        :param urls: list of urls to crawl in
        :param log_dir: directory path to store logs and results
        :param max_processes: maximum number of processes to run in parallel
        """
        # clean duplicate urls from list and return cleaned list
        def clean_duplicates(u_list):
            domains = list()
            clean = list()

            for u in u_list:
                d = urlsplit(u).netloc.lower()
                if d == "":
                    continue
                if d not in domains:
                    domains.append(d)
                    clean.append(u)
            return clean

        self._urls = clean_duplicates(urls)  # url list without duplicates
        self.log_dir = log_dir

        self.max_processes = max_processes
        self._sema = None  # semaphore used to limit number of processes running in parallel

        self.verbose = verbose

    def start(self):
        """
        Start crawling in domains.
        """
        # create a unique log directory name
        def create_log_dir_name(dd):
            clean_domain = ""
            for char in dd:
                if char not in string.ascii_letters+string.digits:
                    clean_domain += "_"
                else:
                    clean_domain += char
            return clean_domain + time.strftime("__%Y%m%d_%H%M%S")

        self._sema = Semaphore(self.max_processes)

        # the spiders can crawl independently and have no common resources
        for u in self._urls:
            d = urlsplit(u).netloc.lower()
            s = Spider(u, d, os.path.join(self.log_dir, create_log_dir_name(d)), self._sema)

            p = Process(target=Spider.crawl, args=(s, ))
            self._sema.acquire(True)  # acquire semaphore for next spider
            p.start()

            if self.verbose:
                print("[+] Spawned spider for: {}".format(u))
