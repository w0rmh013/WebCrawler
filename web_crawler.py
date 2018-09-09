# this module implements the web crawler and manages the spiders
from multiprocessing import Process
import os
import string
import time

from spider import Spider


class WebCrawler:
    def __init__(self, urls, log_dir=os.getcwd()):
        """
        Create instance of WebCrawler.

        :param urls: list of urls to crawl in
        :param log_dir: directory path to store logs and results
        """
        # clean duplicate urls from list and return cleaned list
        def clean_duplicates(u_list):
            domains = list()
            clean = list()

            for u in u_list:
                d = Spider.get_domain(u).lower()
                if d not in domains:
                    domains.append(d)
                    clean.append(u)
            return clean

        self._urls = clean_duplicates(urls)  # url list without duplicates

        if not os.path.isdir(log_dir):
            print("[-] Log directory does not exist: {}".format(log_dir))
            raise FileNotFoundError
        self._log_dir = log_dir

    def start(self):
        """
        Start crawling in domains.
        """
        # create a unique log directory name
        def create_log_dir_name(uu):
            d = Spider.get_domain(uu).lower()
            clean_domain = ""
            for char in d:
                if char not in string.ascii_letters+string.digits:
                    clean_domain += "_"
                else:
                    clean_domain += char
            return clean_domain + time.strftime("__%Y%m%d_%H%M%S")

        print("[*] Starting to crawl...")
        # the spiders can crawl independently and have no common resources
        for u in self._urls:
            s = Spider(u, os.path.join(self._log_dir, create_log_dir_name(u)))
            p = Process(target=Spider.crawl, args=(s, ))
            p.start()
        print("[+] Crawlers spawned.")