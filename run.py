from pprint import pprint
from spyder import SpYder

target_url="https://pixrobot.net/"
threads=5

s=SpYder(
    max_urls=0,
    max_domains=0,
    
    # save_domains:bool=False, # saves a list of domains
    save_media_urls=True, # save images urls
    save_css_urls=True, # ...
    save_js_urls=True, # ...
    save_links=True, # by default its a only link crawler/getter.
    
    save_dead_urls=True, # all urls are checked for status. If true, at the end returns list of 4xx/5xx
    
    ping_internal=True,   # ping urls even if they wont be crawled.
    ping_external=False,   # ping urls even if they wont be crawled.

    internal_crawl=True, # check internal content
    internal_links=True,
    internal_media=True,
    internal_css=True,
    internal_js=True,

    external_crawl=False, # check external content
    external_links=False,
    external_media=False,
    external_css=False,
    external_js=False,

    custom_headers=None,
    
    # queue_size=QUEUE_MAXSIZE,
    plot_it=False, # open image directly. the more websiets crawled, more struggle
    all_urls=True, # aka visited urls history (with false only saves domain, otherwise will display all the links visited in domain)
    
    # dont open links contaninng ...
    blacklisted_domains=[], 
    blacklisted_words=[]
)
s.clear()

pprint(s.multicrawl(target_url, threads))
# s.crawl(target_url)
