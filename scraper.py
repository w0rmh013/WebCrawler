# this module is used to scrape links from a web page
from bs4 import BeautifulSoup
from hashlib import sha256
from urllib.parse import quote, urlsplit


class Scraper:
    def __init__(self, domain, start_link):
        """
        Create instance of Scraper.

        :param domain: domain of website
        :param start_link: start link (to add to visited links)
        """
        self._domain = domain

        link_hash = sha256()
        link_hash.update(start_link.encode())
        self._link_history = [link_hash.digest()]  # list of visited links (as sha256 digests)

    @staticmethod
    def create_http_link(parts, domain=None):
        """
        Create HTTP link from parts (returned by urlsplit).

        :param parts: parts returned by urlsplit
        :param domain: optional domain if it is not included in parts
        :return: full HTTP link
        """
        encoded_path = quote(parts.path)  # url-encode the path

        if not encoded_path.startswith("/"):
            encoded_path = "/" + encoded_path

        # check which domain to use
        if domain:
            link = "http://{0}{1}".format(domain, encoded_path)
        else:
            link = "http://{0.netloc}{1}".format(parts, encoded_path)

        if parts.query != "":
            link += "?{0.query}".format(parts)
        if parts.fragment != "":
            link += "#{0.fragment}".format(parts)

        return link.replace("\\", "/")

    def _get_internal_link(self, raw_link):
        """
        Get internal link (None if external).

        :param raw_link: raw hyperlink (e.g. index.html, http://mydomain.com/test.php)
        :return: full link if the raw_link is internal, else None
        """
        # no href for tag
        if not raw_link:
            return

        parts = urlsplit(raw_link)

        # e.g. "/user/login/"
        if parts.scheme == "" and parts.netloc == "":
            return Scraper.create_http_link(parts, self._domain)

        if parts.scheme != "http" or parts.netloc != self._domain:
            return

        # e.g. http://thedomain.com/user/login/
        return Scraper.create_http_link(parts)

    def _link_visited(self, link):
        """
        Check if link was already visited.

        :param link: full HTTP link
        :return: True if already visited, else False
        """
        # we save digests instead of full link to save space
        link_hash = sha256()
        link_hash.update(link.encode())

        # if link wasn't visited, we append it to history
        digest = link_hash.digest()
        if digest not in self._link_history:
            self._link_history.append(digest)
            return False
        return True

    def get_hyperlinks(self, content):
        """
        Get hyperlinks from web page.

        :param content: web page content (e.g. .html file)
        :return: list off all internal links
        """
        soup = BeautifulSoup(content, "html.parser")  # we use the default built-in parser
        # get only internal links
        links = list()
        for link in soup.find_all("a"):
            ret = self._get_internal_link(link.get("href"))
            if ret:
                if not self._link_visited(ret):
                    links.append(ret)
        return links
