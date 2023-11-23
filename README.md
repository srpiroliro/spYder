# spYder - The Web Crawler

spYder is a robust web crawling and scraping tool designed to facilitate the collection and analysis of web data. It's built with flexibility in mind, offering a multitude of settings to control the scope and depth of the crawl.

## Features

- **Configurable Constraints**: Set maximum URLs and domains to control the breadth of the crawl.
- **Selective Content Saving**: Choose to save links, media URLs (images, videos), CSS, and JS files.
- **Dead URL Tracking**: Option to track URLs that return 4xx/5xx status codes.
- **Ping Settings**: Control whether to ping internal and external URLs.
- **Crawl Settings**: Decide whether to crawl internal and external content.
- **Queue Management**: Use a thread-safe queue to manage URLs to be crawled, with customizable size and timeout settings.
- **Data Visualization**: Generate a graph map of the crawled websites (requires additional plotting setup).
- **Extensibility**: Use custom headers for requests.
- **Blacklisting**: Prevent crawling of URLs with certain words or from specific domains.
- **Log Management**: Maintain an execution log for monitoring and debugging purposes.

## Installation

Before installing spYder, ensure you have Python 3.x installed on your system. Then, install the required packages:

```bash
pip install requests tldextract networkx matplotlib bs4
```

## Usage

Instantiate the `SpYder` class with your desired configuration:

```python
from spYder import SpYder

spider = SpYder(
    max_urls=100,
    max_domains=10,
    save_media_urls=True,
    save_css_urls=True,
    save_js_urls=True,
    save_links=True,
    save_dead_urls=True,
    ping_internal=True,
    ping_external=False,
    internal_crawl=True,
    external_crawl=False,
    plot_it=True,
    blacklisted_domains=['example.com'],
    blacklisted_words=['login', 'register']
)
```

To start a crawl, call the `multicrawl` method with the starting URL and the number of threads:

```python
result = spider.multicrawl('http://example.com', threads_num=5)
```

## Output

The crawl results are stored in various sets and can be accessed directly:

- `unique_domains`: Set of unique domains visited.
- `visited_urls`: Set of URLs visited.
- `unknown_urls`: Set of URLs that returned status 429.
- `dead_urls`: Set of URLs that returned 4xx/5xx statuses.
- `dead_domains`: Set of domains where all URLs were dead.
- `all_urls`: Dictionary with domains as keys and sets of URLs as values.
- `css_urls`: Set of CSS file URLs.
- `js_urls`: Set of JavaScript file URLs.
- `media_urls`: Set of media file URLs (images, videos).
- `links`: Set of hyperlink URLs.

## Graph Map

If `plot_it` is set to `True`, a graph map will be generated showing the connections between different domains.

## Cleaning Up

Use the `clear` method to remove temporary files created during the crawl:

```python
spider.clear()
```

## Contributing

Contributions to spYder are welcome! Please fork the repository and submit a pull request with your changes.
