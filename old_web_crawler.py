# this module implements the web crawler for a list of urls and manages the spiders
from multiprocessing import Process, Semaphore
import os
import string
import time
from urllib.parse import urlsplit

from spider import Spider


class WebCrawler:
    def __init__(self, urls, limit="depth", limit_param=10, log_dir=os.getcwd(), max_processes=10, max_threads=20, verbose=False):
        """
        Create instance of WebCrawler.

        :param urls: list of urls to crawl in
        :param limit: crawling limit type ("depth" or "count")
        :param limit_param: limit parameter (max depth or max number of pages)
        :param log_dir: directory path to store logs and results
        :param max_processes: maximum number of processes to run in parallel
        :param max_threads: maximum number of threads per process
        :param verbose: verbosity of WebCrawler
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
                    clean.append(u.replace("\\", "/"))
            return clean

        self._urls = clean_duplicates(urls)  # url list without duplicates

        # set limit properties
        self.limit = limit
        self.limit_param = limit_param

        self.log_dir = log_dir

        self.max_processes = max_processes
        self.max_threads = max_threads
        self._sema = None  # semaphore used to limit number of processes running in parallel

        self.verbose = verbose

    def start(self):
        """
        Start crawling in domains.
        """
        # create a unique log directory name
        def create_log_dir_name(dd):
            clean_domain = "".join(c if c in string.ascii_letters+string.digits else "_" for c in dd)
            return clean_domain + time.strftime("__%Y%m%d_%H%M%S")

        self._sema = Semaphore(self.max_processes)

        # the spiders can crawl independently and have no common resources
        for u in self._urls:
            d = urlsplit(u).netloc.lower()
            s = Spider(u, d, self.limit, self.limit_param, os.path.join(self.log_dir, create_log_dir_name(d)), self.max_threads, self._sema)

            p = Process(target=Spider.crawl, args=(s, ))
            self._sema.acquire(True)  # acquire semaphore for next spider
            p.start()

            if self.verbose:
                print("[+] Spawned spider for: {}".format(u))
