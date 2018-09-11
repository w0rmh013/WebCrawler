from argparse import ArgumentParser
import os
import sys
from web_crawler import WebCrawler


def main():
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--depth", type=int, help="limit crawling by depth of directory tree (default, 10)")
    group.add_argument("-c", "--count", type=int, help="limit crawling by number of pages")
    parser.add_argument("url_list", help="file containing urls separated by newlines")
    parser.add_argument("-v", "--verbose", action="store_true", help="set verbosity of program")
    parser.add_argument("-p", "--max-processes", type=int, help="maximum number of processes to run in parallel (default is 10)")
    parser.add_argument("-t", "--max-threads", type=int, help="maximum number of threads per process (default is 20)")
    args = parser.parse_args()

    # check if url_list file exists and that user has permission to read it
    if not os.path.isfile(args.url_list) or not os.access(args.url_list, os.R_OK):
        print("[-] File does not exist: {}".format(args.url_list))
        sys.exit(1)

    # get url list
    urls = list()
    with open(args.url_list, "r") as url_list_file:
        for url in url_list_file:
            urls.append(url.strip())

    crawler = WebCrawler(urls)

    # set custom parameters
    if args.max_processes:
        crawler.max_processes = args.max_processes
    if args.max_threads:
        crawler.max_threads = args.max_threads
    if args.verbose:
        crawler.verbose = True
    if args.depth:
        crawler.limit = "depth"
        crawler.limit_param = args.depth
    elif args.count:
        crawler.limit = "count"
        crawler.limit_param = args.count

    crawler.start()
    sys.exit(0)


if __name__ == '__main__':
    main()
