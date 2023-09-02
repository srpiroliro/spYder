import queue, requests, tldextract
import re
import networkx as nx
import matplotlib.pyplot as plt

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from os.path import exists
from os import remove, mkdir
from json import loads, dump
from threading import Thread

class SpYder:
    HEADERS={
        "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    REQUEST_TIMEOUT=2

    QUEUE_MAXSIZE=0 # 100_000 # 0 === unlimited

    # constants which will go into the queue
    CRAWL=0
    PING=1
    CRAWLABLE_EXT=["php","css","htm","html"]
 
    DATA_FOLDER="data"
    UNIQUE_DOMAINS_FILE=f"{DATA_FOLDER}/unique_domains.json"
    ALL_URLS_FILE=f"{DATA_FOLDER}/all_urls.json"

    LOGS_FILE=f"{DATA_FOLDER}/execution.log"

    GRAPH_MAP_FILE=f"{DATA_FOLDER}/map.png"

    def __init__(
        self,
        
        max_urls:int=0,
        max_domains:int=0,
        
        # save_domains:bool=False, # saves a list of domains
        save_media_urls:bool=False, # save images urls
        save_css_urls:bool=False, # ...
        save_js_urls:bool=False, # ...
        save_links:bool=True, # by default its a only link crawler/getter.
        
        save_dead_urls:bool=False, # all urls are checked for status. If true, at the end returns list of 4xx/5xx
        
        ping_internal:bool=False,   # ping urls even if they wont be crawled.
        ping_external:bool=False,   # ping urls even if they wont be crawled.

        internal_crawl:bool=True, # check internal content
        internal_links:bool=False,
        internal_media:bool=False,
        internal_css:bool=False,
        internal_js:bool=False,

        external_crawl:bool=True, # check external content
        external_links:bool=False,
        external_media:bool=False,
        external_css:bool=False,
        external_js:bool=False,

        custom_headers:dict|None=None,
        
        queue_size:int=QUEUE_MAXSIZE,
        plot_it:bool=False, # open image directly. the more websiets crawled, more struggle
        all_urls:bool=False, # aka visited urls history (with false only saves domain, otherwise will display all the links visited in domain)
        
        # dont open links contaninng ...
        blacklisted_domains:list=[], 
        blacklisted_words:list=[]
    ):
        if not exists(self.DATA_FOLDER): mkdir(self.DATA_FOLDER)
        
        self.__logs()

        self.custom_headers=self.HEADERS.copy() if not custom_headers else custom_headers

        # Request session (good for inteernal crawling)
        self.session=requests.Session()
        self.session.headers.update(self.custom_headers)

        # Queue
        self.todo_urls_queue=queue.Queue(maxsize=queue_size)


        self.save_domains=True # save_domains

        self.save_all_urls=all_urls
        if self.save_all_urls:
            self.all_urls={} # start_url:set(links)


        # ~ OPTIONS ~
        self.max_urls=max_urls
        self.max_domains=max_domains
        
        self.save_media_urls=save_media_urls
        self.save_css_urls=save_css_urls
        self.save_js_urls=save_js_urls
        self.save_links=save_links
        self.save_dead_urls=save_dead_urls

        self.settings={
            "crawl":       {"external":external_crawl,    "internal":internal_crawl},
            "links":       {"external":external_links,    "internal":internal_links},
            "media":       {"external":external_media,    "internal":internal_media},
            "css":         {"external":external_css,      "internal":internal_css},
            "js":          {"external":external_js,       "internal":internal_js},
            "ping_urls":   {"external":ping_external,     "internal":ping_internal}
        }
        
        # Blacklistings
        self.blacklisted_domains=blacklisted_domains
        self.blacklisted_words=blacklisted_words

        # ~ ~ ~ ~

        # MAP OF GRAPHS
        self.plot_it=plot_it
        if self.plot_it: 
            self.connections=[]

         # CHECK: not efficient?
        self.unique_domains=set()
        self.visited_urls=set()
        self.unknown_urls=set() # links which returned 429.
        
        if self.save_dead_urls: 
            self.dead_urls=set()
            self.dead_domains=set() # to improve performance, we will save also domains

        if self.save_links: self.links=set()
        if self.save_media_urls: self.media_urls=set()
        if self.save_css_urls: self.css_urls=set()
        if self.save_js_urls: self.js_urls=set()


    def crawl(self,url:str, id_num:int=0)->dict:
        """
            Crawls given url and returns set of found urls.
        """

        found_urls={
            "links":{"external":set(),"internal":set()}, 
            "media":{"external":set(),"internal":set()},
            "css":{"external":set(),"internal":set()},
            "js":{"external":set(),"internal":set()}
        }

        starting_domain=self.__get_domain(url) 
        # cant return None due to being a valid url (if no exception was raised.)

        self.visited_urls.add(self.__format_url(url))
        self.__logs(f"crawling: {str(url.encode()).replace('b','')}",id_num)

        dirty_urls=[]
        try:
            dirty_urls=self.__get_urls(url)
            self.__logs(f"got {len(dirty_urls)} links")
        except Exception as e:
            self.__logs(f"no links found. sad :( ",id_num)
            return found_urls
        
        try:
            clean_urls=self.__clean_urls(starting_domain, url, dirty_urls) # type: ignore (can't be none)
            self.__logs(f"updating local sets/dicts",id_num)

            # CHECK: issue during multithreading?
            if self.save_all_urls:
                if starting_domain not in self.all_urls: self.all_urls[starting_domain]=set()
                
                for url_topic in found_urls:
                    self.all_urls[starting_domain].update(clean_urls[url_topic]["internal"])
                    self.all_urls[starting_domain].update(clean_urls[url_topic]["external"])

            if self.save_domains:
                self.unique_domains.update(clean_urls["domains"])
                self.__logs(f"saved them all",id_num)

            if self.plot_it:
                self.connections+=[[starting_domain, other_domain] for other_domain in clean_urls["domains"]]

        except Exception as e:
            self.__logs(f"crawl error happend! -> e: {str(e).encode()}",id_num) 
            # encode() due to url encoding errors. 
        else:
            self.__logs(f"closing.",id_num)

            return clean_urls
        return found_urls

    def multicrawl(self, starting_url:str, threads_num:int=5)->dict: 
        self.__crawl2queue(starting_url, 0)
    
        threads=[]
        for i in range(threads_num):
            threads.append(Thread(target=self.__multicrawl_handler, args=(i,)))
            threads[-1].start()
        
        for t in threads: t.join()
        self.__logs(f"crawl finished.")

        self.__save_data()
        self.__logs(f"saved")

        if self.plot_it: 
            self.__logs(f"graph drawn")
            self.graphs_map()
            self.__logs(f"drawing graph")
        
        return {
            "unique_domains":self.unique_domains,
            "visited_urls":self.visited_urls,
            "unknown_urls":self.unknown_urls,
            "dead_urls":self.dead_urls,
            "dead_domains":self.dead_domains,
            "all_urls":self.all_urls,
            "css_urls":self.css_urls,
            "js_urls":self.js_urls,
            "media_urls":self.media_urls,
            "links":self.links,
        }

         
    def graphs_map(self):
        G=nx.Graph()

        if self.save_links: G.add_nodes_from(self.unique_domains)
        elif self.save_domains: G.add_nodes_from(self.unique_domains)

        G.add_edges_from(self.connections)

        plt.figure(frameon=False).set_size_inches(12,12)
        nx.draw(G, with_labels=True, font_size=7, font_color="white", node_size=50)

        plt.savefig(self.GRAPH_MAP_FILE, dpi=200)
        # plt.show()



    def clear(self):
        for i in [self.ALL_URLS_FILE, self.GRAPH_MAP_FILE, self.UNIQUE_DOMAINS_FILE]:
            if exists(i): remove(i)

    # HELPERS

    def __multicrawl_handler(self, id_num:int=0):
        self.__logs(f"INITIALIZED", id_num)

        while not self.todo_urls_queue.empty() and \
                (len(self.visited_urls)<self.max_urls or self.max_urls==0) and \
                (len(self.unique_domains)<self.max_domains or self.max_domains==0): #  and not self.finished
            
            self.__logs(f"queue size: {self.todo_urls_queue.qsize()}", id_num)
            self.__logs(f"unique domains: {len(self.unique_domains)}", id_num)
            self.__logs(f"visited urls: {len(self.visited_urls)}", id_num)

            operation, topic, url=self.todo_urls_queue.get()

            if operation==self.CRAWL: 
                self.__crawl2queue(url, id_num)
            elif operation==self.PING:
                if self.__smart_ping(url):
                    if topic=="links": self.links.add(url)
                    elif topic=="media": self.media_urls.add(url)
                    elif topic=="css": self.css_urls.add(url)
                    elif topic=="js": self.js_urls.add(url)

        self.__logs(f"DEAD", id_num)

    def __crawl2queue(self,url:str, id_num:int):
        sorted_urls=self.crawl(url, id_num)
        # self.finished=self.finished and not bool(urls)

        for url_topic in sorted_urls:
            for origin in sorted_urls[url_topic]:
                for url in sorted_urls[url_topic][origin]:

                    url_domain=self.__get_domain(url)
                    if self.__format_url(url) in self.visited_urls or \
                            any(b in url_domain for b in self.blacklisted_words) or \
                            url_domain in self.blacklisted_domains or \
                            url in self.dead_urls: 

                        continue
                    elif url_domain in self.dead_domains:
                        self.dead_urls.add(url)

                    elif self.todo_urls_queue.full(): 
                        self.__logs(f"QUEUE IS FULL!", id_num)


                    url_crawlable=self.__is_crawlable(url) and not
                    self.todo_urls_queue.put(
                        (self.CRAWL if url_topic in ["links", "css"] else self.PING, 
                        url_topic, url)
                    )

    def __is_crawlable(self, url:str)->bool:
        """
            Returns True if url is crawlable, False otherwise.
        """
        url_data=urlparse(url)
        url_file_extension=url_data.path.split(".")[-1].lower()
        
        # CHECK: may be not very precise due to urls to root (something/) being considered as files.
        return not url_file_extension or url_file_extension in self.CRAWLABLE_EXT

    def __get_urls(self,url)->dict:
        """
            Returns a dict ( {links, media, css, js} ) of urls found in given url.
            An exception is raised if the requests fails.
        """

        url_file=url.split("?")[0].split("://")[1].lower()
        if not (url_file.endswith("/") or "." not in url_file.split("/")[-1] or url_file.count("/")==0):
            url_file=url_file.split("/")[-1]
        else: url_file=url_file.strip("/")+f"/index.html"
        
        if not (".htm" in url_file or ".php" in url_file or ".css" in url_file):
            raise Exception(f"given file ({url_file}) isn't supported.")

        try:
            response=self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            if response.status_code==429: self.unknown_urls.add(url) #TODO: if 429, add to unknown_urls
        except Exception as e:
            if self.save_dead_urls: self.dead_urls.add(url)

            raise Exception(f"request error -> e: {str(e).encode()}")
        else:
            source_code=response.text

            links=set()
            css=set()
            js=set()
            media=set()

            if ".htm" in url_file or ".php" in url_file:
                links, media, css, js = self.__get_urls_from_html(source_code, url)
            elif ".css" in url_file and self.save_css_urls:
                media, css = self.__get_urls_from_css(source_code, url)
            
            return {
                "links":links,
                "media":media,
                "css":css,
                "js":js
            }
    
    def __get_urls_from_html(self, source_code:str, base_url:str) -> tuple:
        soup=BeautifulSoup(source_code,"html.parser")

        links=set()
        css=set()
        js=set()
        media=set()
        
        if self.save_links:
            links=set(node.get("href").strip() for node in soup.find_all("a") if node.get("href"))
        
        if self.save_css_urls:
            css=set(node.get("href").strip() for node in soup.find_all("link") if node.get("href"))
            
        if self.save_js_urls:
            js=set(node.get("src").strip() for node in soup.find_all("script") if node.get("src"))
            
        if self.save_media_urls:
            media=set(node.get("src").strip() for node in soup.find_all("img") if node.get("src"))
            media|=set(node.get("src").strip() for node in soup.find_all("video") if node.get("src"))
            
            for style_tag in soup.find_all("style"):
                media|=set(self.__get_urls_from_css(style_tag.text, base_url))

        return links, media, css, js

    def __get_urls_from_css(self, css_content:str, base_url:str) -> tuple:
        url_pattern=re.compile(r'url\(["\']?(.*?)["\']?\)')
        urls=url_pattern.findall(css_content)

        media=set()
        css=set()

        for url in urls:
            absolute_url=urljoin(base_url, url)
            if absolute_url.split("?")[0].split("#")[0].endswith(".css"):
                css.add(absolute_url)
            else:
                media.add(absolute_url)

        return media, css
    
    def __smart_ping(self, url:str)->bool:
        """
            Returns True if url is alive, False otherwise.
        """

        url_domain=self.__get_domain(url)
        if url_domain in self.dead_domains: return False

        if self.__ping_url(url): return True

        new_url=url
        if url.startswith("https://"): new_url=url.replace("https://","http://")
        elif url.startswith("http://"): new_url=url.replace("http://","https://")

        if self.__ping_url(new_url): return True

        self.dead_urls.add(url)

        if not self.__ping_url(f"https://{url_domain}"):
            self.dead_domains.add(url_domain)

        return False


    def __ping_url(self, url, allow_redirects:bool=False)->bool:
        try:
            response=requests.head(
                url=url,
                timeout=self.REQUEST_TIMEOUT,
                headers=self.custom_headers,
                allow_redirects=allow_redirects
            )
            return response.status_code==200
        except: return False

    def __get_domain(self, url:str)->str|None:
        _, name, suffix=tldextract.extract(url)
        return f"{name}.{suffix}".lower() if name and suffix else ""
    
    def __get_path(self,url:str)->str:
        path=urlparse(url).path
        return "/" if not path else path

    def __format_url(self,url:str)->str|None:
        domain=self.__get_domain(url) 
        if not domain: return None

        return domain+self.__get_path(url)

    def __clean_urls(self, start_domain:str, start_url:str, urls:dict):
        """
            Returns a dict of urls sorted by external/internal and a set of domains.
        """
        result={
            "links":{"external":set(),"internal":set()}, 
            "media":{"external":set(),"internal":set()},
            "css":{"external":set(),"internal":set()},
            "js":{"external":set(),"internal":set()},
            
            "domains":set()
        }
       
        for topic in ["links","media","css","js"]:
            for link in urls[topic]:
                if self.__check_external(start_domain, link):
                    domain=self.__get_domain(link)
                    if not domain: continue

                    result[topic]["external"].add(link)
                    result["domains"].add(domain)

                elif self.__check_internal(start_domain, link):
                    result[topic]["internal"].add(link if link.startswith("http") else urljoin(start_url, link))

        return result
    
    def __check_external(self, base_domain:str, url:str)->bool:
        if not (url.startswith("http") and "://" in url): return False
        return self.__get_domain(url)!=base_domain

    def __check_internal(self, base_domain:str, url:str)->bool:
        if url.startswith("http") and "://" in url: 
            return self.__get_domain(url)!=base_domain

        return not ":" in url \
            and not "//" in url \
            and not url.startswith("?") \
            and not url.startswith("#") \
            and not url.startswith("data:")

    def __save_data(self):
        self.__json2file(self.UNIQUE_DOMAINS_FILE, list(self.unique_domains))

        # CHECK: slow?
        if self.save_all_urls:
            tmp={}
            if type(self.all_urls) is dict:
                for domain in self.all_urls:
                    tmp[domain]=list(self.all_urls[domain])
            else: tmp=list(self.all_urls)

            self.__json2file(self.ALL_URLS_FILE, tmp)

    def __logs(self, message:str|None=None, thread_num:int=0):
        if message is None:
            with open(self.LOGS_FILE, "w") as f: f.write("")
            return

        with open(self.LOGS_FILE, "a") as f:
            f.write("\n["+datetime.today().strftime("%Y-%m-%d %H:%M:%S")+f"] - [{thread_num}] {message}")

    def __file2json(self, filepath) -> dict:
        if not exists(filepath):
            return dict()
        
        with open(filepath) as f:
            return loads(f.read())

    def __json2file(self, filepath, data) -> None: 
        # TODO: modify in the future

        with open(filepath,"w") as f:
            dump(data, f)

    def __del__(self):
        print(f"unique domains: {len(self.unique_domains)}\nvisited urls: {len(self.visited_urls)}\nfini.")