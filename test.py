from web_crawler import WebCrawler


def main():
    c = WebCrawler(["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"], "./logs", 2)
    # c = WebCrawler(["http://localhost:8000"], "./logs")
    c.start()


if __name__ == "__main__":
    main()
