import queue, requests, tldextract
import re
import networkx as nx
import matplotlib.pyplot as plt

from bs4 import BeautifulSoup
from urllib.parse import urlparse
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
        
        check_url_status:bool=False, # all urls are checked for status. If true, at the end returns list of 4xx/5xx
        
        internal_crawl:bool=True, # check internal content
        internal_media:bool=False,
        internal_css:bool=False,
        internal_js:bool=False,

        external_crawl:bool=True, # check external content
        external_media:bool=False,
        external_css:bool=False,
        external_js:bool=False,
        
        queue_size:int=QUEUE_MAXSIZE,
        plot_it:bool=False, # open image directly. the more websiets crawled, more struggle
        all_urls:bool=False, # aka visited urls history (with false only saves domain, otherwise will display all the links visited in domain)
        
        # dont open links contaninng ...
        blacklisted_domains:list=[], 
        blacklisted_words:list=[]
    ):
        if not exists(self.DATA_FOLDER): mkdir(self.DATA_FOLDER)
        
        self.__logs()

        # Request session (good for inteernal crawling)
        self.session=requests.Session()
        self.session.headers.update(self.HEADERS)

        # Queue
        self.todo_urls_queue=queue.Queue(maxsize=queue_size)


        self.save_domains=True # save_domains
        # CHECK: not efficient?
        self.unique_domains=set()
        self.visited_urls=set()

        self.enable_all_urls=all_urls
        if self.enable_all_urls:
            self.all_urls={} # start_url:set(links)



        # ~ OPTIONS ~
        self.max_urls=max_urls
        self.max_domains=max_domains
        
        # TODO: implement.
        self.save_media_urls=save_media_urls
        self.save_css_urls=save_css_urls
        self.save_js_urls=save_js_urls
        self.save_links=save_links
        
        self.check_url_status=check_url_status
        
        self.crawl_external=external_crawl
        self.imgs_external=external_media
        self.css_external=external_css
        self.js_external=external_js
        
        self.crawl_internal=internal_crawl
        self.imgs_internal=internal_media
        self.css_internal=internal_css
        self.js_internal=internal_js
        
        # Blacklistings
        self.blacklisted_domains=blacklisted_domains
        self.blacklisted_words=blacklisted_words

        # ~ ~ ~ ~

        # MAP OF GRAPHS
        self.plot_it=plot_it
        if self.plot_it: 
            self.connections=[]

    def crawl(self,url:str, id_num:int=0)->set:
        found_links=set()
        dirty_links=[]

        starting_domain=self.__get_domain(url) 
        # cant return None due to being a valid url (if no exception was raised.)

        self.visited_urls.add(self.__format_url(url))
        self.__logs(f"crawling: {str(url.encode()).replace('b','')}",id_num)

        try:
            dirty_links=self.__get_urls(url)
            self.__logs(f"got {len(dirty_links)} links")
        except Exception as e:
            self.__logs(f"no links found. sad :( ",id_num)
            return set()
        
        try:
            clean_links=self.__clean_urls(starting_domain, url, dirty_links)

            if self.crawl_external: found_links.update(clean_links["urls"]["external"])
            if self.crawl_internal: found_links.update(clean_links["urls"]["internal"])
            # TODO: add imgs,js and css

            self.__logs(f"updating local sets/dicts",id_num)

            # CHECK: issue during multithreading?
            if self.enable_all_urls:
                if starting_domain not in self.all_urls: self.all_urls[starting_domain]=set()
                self.all_urls[starting_domain].update(found_links)

            if self.save_domains:
                self.unique_domains.update(clean_links["domains"])
                self.__logs(f"saved them all",id_num)

            if self.plot_it:
                self.connections+=[[starting_domain, other_domain] for other_domain in clean_links["domains"]]

        except Exception as e:
            self.__logs(f"crawl error happend! -> e: {str(e).encode()}",id_num) 
            # encode() due to url encoding errors. 
        
        self.__logs(f"closing.",id_num)

        return found_links

    def multicrawl(self, starting_url:str, threads_num:int=5)->None: 
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

            url=self.todo_urls_queue.get()
            
            self.__crawl2queue(url, id_num)
        
        self.__logs(f"DEAD", id_num)

    def __crawl2queue(self,url:str, id_num:int):
        urls=self.crawl(url, id_num)
        # self.finished=self.finished and not bool(urls)

        for url in urls:
            url_domain=self.__get_domain()
            if self.__format_url(url) in self.visited_urls or \
                any([b in url_domain for b in self.blacklisted_words]) or \
                url_domain in self.blacklisted_domains: 

                # CHECK: any() too slow?
                continue

            elif self.todo_urls_queue.full(): self.__logs(f"QUEUE IS FULL!", id_num)

            self.todo_urls_queue.put(url)

    def __get_urls(self,url)->list:
        url_file=url.split("?")[0].split("://")[1].lower()
        if not (url_file.endswith("/") or "." not in url_file.split("/")[-1] or url_file.count("/")==0):
            url_file=url_file.split("/")[-1]
        else: url_file=url_file.strip("/")+f"/index.html"
        
        if not (".htm" in url_file or ".php" in url_file or ".css" in url_file):
            raise Exception(f"given file ({url_file}) isn't supported.")


        response=self.session.get(url, timeout=self.REQUEST_TIMEOUT, headers=self.custom_headers)
        assert response.status_code==200

        source_code=response.text.encode()
        if ".htm" in url_file or ".php" in url_file:
            return self.__get_urls_from_html(source_code, url)
        elif ".css" in url_file and self.save_css_urls:
            return self.__get_urls_from_css(source_code, url)
        
        return
    
    def __get_urls_from_html(self, source_code:str, current_url:str):
        soup=BeautifulSoup(source_code,"html.parser")
        
        urls=set()
        if self.save_links:
            urls|=set(node.get("href").strip() for node in soup.find_all("a") if node.get("href"))
        
        if self.save_css_urls:
            urls|=set(node.get("href").strip() for node in soup.find_all("link") if node.get("href"))
            
        if self.save_js_urls:
            urls|=set(node.get("src").strip() for node in soup.find_all("script") if node.get("src"))
            
        if self.save_media_urls:
            urls|=set(node.get("src").strip() for node in soup.find_all("img") if node.get("src"))
            urls|=set(node.get("src").strip() for node in soup.find_all("video") if node.get("src"))
            
            splitted_url_elements=current_url.split("://")[1].split("/")
            current_folder=current_url if len(splitted_url_elements)==1 or "." not in splitted_url_elements[-1] else current_url.rsplit("/",1)[0]

            for style_tag in soup.find_all("style"):
                css_urls=re.findall(r"url\(['\"]?([^'\"\)])['\"]?\)",style_tag.text)
                filtered_css_urls=set(
                    target if "://" in target else self.__join_url(current_folder,target) 
                        for target in css_urls 
                            if target)
                
                urls|=filtered_css_urls

        return urls
    
    # TODO:
    def __get_urls_from_css(self, source_code:str, current_url:str):
        # from source_code extract urls using regex
        # relative paths to absolute using current_url
        
        
        pass
    
    
    def __ping_url(self, url, allow_redirects:bool=False)->bool:
        # CHECK: have in mind that http redirects to https, causing this to return False.
        try:
            response=requests.head(
                url=url,
                timeout=self.REQUEST_TIMEOUT,
                headers=self.custom_headers,
                allow_redirects=allow_redirects
            )
            return response.status_code==200
        except: return False

    def __join_url(self, url, path):
        main_url_path=urlparse(url).path

        if not main_url_path or "/"==main_url_path:     ready_url=url.strip("/")
        elif path.startswith("/"):                      ready_url=url.split(main_url_path)[0]
        else:                                           ready_url=url.rsplit("/",1)[0]+"/"

        return ready_url+path

    def __get_domain(self, url:str)->str|None:
        _, name, suffix=tldextract.extract(url)
        return f"{name}.{suffix}".lower() if name and suffix else False
    
    def __get_path(self,url:str)->str:
        path=urlparse(url).path
        return "/" if not path else path

    def __format_url(self,url:str)->str|None:
        domain=self.__get_domain(url) 
        if not domain: return None

        return domain+self.__get_path(url)

    def __clean_urls(self, start_domain, start_url, links):
        sorted_urls={"external":set(),"internal":set()}
        domains=set()
        
        # TODO: add img, css and js.

        for link in links:
            if link.startswith("http") and "://" in link:
                domain=self.__get_domain(link)

                if not domain: continue
                elif domain==start_domain:
                    sorted_urls["internal"].add(link)
                else:
                    sorted_urls["external"].add(link)
                    domains.add(domain)

            elif ":" not in link \
                and not "//" in link \
                    and not link.startswith("?") \
                    and not link.startswith("#") \
                    and not link.startswith("data:"):

               sorted_urls["internal"].add(self.__join_url(start_url, link)) 

        return {"urls":sorted_urls, "domains":domains}

    def __save_data(self):
        self.__json2file(self.UNIQUE_DOMAINS_FILE, list(self.unique_domains))

        # CHECK: slow?
        if self.enable_all_urls:
            tmp={}
            if type(self.all_urls) is dict:
                for domain in self.all_urls:
                    tmp[domain]=list(self.all_urls[domain])
            else: tmp=list(self.all_urls)

            self.__json2file(self.ALL_URLS_FILE, tmp)

    def __logs(self, message:str=None, thread_num:int=0):
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