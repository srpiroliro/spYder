import queue, requests, tldextract
import networkx as nx
import matplotlib.pyplot as plt

from urllib.parse import urlparse
from datetime import datetime
from os.path import exists
from os import remove
from json import loads, dump
from threading import Thread
from bs4 import BeautifulSoup

class SpYder:
    HEADERS={
        "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    QUEUE_MAXSIZE=0 # 100_000 # 0 === unlimited
 
    DATA_FOLDER="data"
    UNIQUE_DOMAINS_FILE=f"{DATA_FOLDER}/unique_domains.json"
    ALL_URLS_FILE=f"{DATA_FOLDER}/all_urls.json"

    LOGS_FILE=f"{DATA_FOLDER}/execution.log"

    def __init__(self, max_urls:int=0, max_domains:int=0, internal:bool=True, external:bool=True, queue_size:int=QUEUE_MAXSIZE, plot_it:bool=False):
        self.__logs()

        self.session=requests.Session()
        self.session.headers.update(self.HEADERS)

        self.todo_urls_queue=queue.Queue(maxsize=queue_size)

        # CHECK: not efficient?
        self.unique_domains=set()
        self.all_urls={} # start_url:set(links)
        self.visited_urls=set()

        # OPTIONS
        self.max_urls=max_urls
        self.max_domains=max_domains
        self.crawl_internal=internal
        self.crawl_external=external

        # MAP OF GRAPHS
        self.plot_it=plot_it
        if self.plot_it: self.connections=[]

    def crawl(self,url:str, id_num:int=0)->set:
        found_links=set()
        dirty_links=[]

        starting_domain=self.__get_domain(url) 
        # cant return None due to being a valid url (if no exception was raised.)

        self.visited_urls.add(self.__format_url(url))
        self.__logs(f"crawling: '{url}'",id_num)

        try:
            dirty_links=self.__get_links(url)
            self.__logs(f"got {len(dirty_links)} links")            
        except Exception as e:
            self.__logs(f"no links found. sad :( ",id_num)
            return set()
        
        try:
            clean_links=self.__clean_urls(starting_domain, url, dirty_links)

            if self.crawl_external: found_links.update(clean_links["urls"]["external"])
            if self.crawl_internal: found_links.update(clean_links["urls"]["internal"])

            self.__logs(f"updating local sets/dicts",id_num)

            # CHECK: issue during multithreading?
            if starting_domain not in self.all_urls: self.all_urls[starting_domain]=set()
            self.all_urls[starting_domain].update(found_links)

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

        self.__save_data()

        if self.plot_it: self.graphs_map()
            
    def graphs_map(self):
        G=nx.Graph()
        G.add_nodes_from(self.unique_domains)
        G.add_edges_from(self.connections)

        nx.draw(G)
        plt.show()



    def clear(self):
        for i in []:
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
            if self.__format_url(url) in self.visited_urls: continue
            elif self.todo_urls_queue.full(): self.__logs(f"QUEUE IS FULL!", id_num)

            self.todo_urls_queue.put(url)

    def __get_links(self,url)->list:
        response=self.session.get(url)
        assert response.status_code==200

        html=response.text.encode()
        soup=BeautifulSoup(html,"html.parser")
        links=set([node.get("href").strip() for node in soup.find_all("a") if node.get("href")])

        return links

    def __join_url(self, url, path):
        main_url_path=urlparse(url).path

        if not main_url_path or "/"==main_url_path: 
            ready_url=url.strip("/")
        elif path.startswith("/"): 
            ready_url=url.split(main_url_path)[0]
        else: 
            ready_url=url.rsplit("/",1)[0]+"/"

        return ready_url+path

    def __get_domain(self, url:str)->str|None:
        subd, name, suffix=tldextract.extract(url)
        return f"{name}.{suffix}".lower() if name and suffix else False
    
    def __get_path(self,url:str)->str:
        path=urlparse(url).path
        return "/" if not path else path

    def __format_url(self,url:str)->str|None:
        domain=self.__get_domain() 
        if not domain: return None

        return domain+self.__get_path(url)

    def __clean_urls(self, start_domain, start_url, links):
        sorted_urls={"external":set(),"internal":set()}
        domains=set()

        for link in links:
            if link.startswith("http") and "://" in link:
                domain=self.__get_domain(link)

                if not domain: continue
                elif domain==start_domain:
                    sorted_urls["internal"].add(link)
                else:
                    sorted_urls["external"].add(link)
                    domains.add(domain)

            elif ":" not in link and not "//" in link and not link.startswith("?") and not link.startswith("#"):
               sorted_urls["internal"].add(self.__join_url(start_url, link)) 

        return {"urls":sorted_urls, "domains":domains}

    def __save_data(self):
        self.__json2file(self.UNIQUE_DOMAINS_FILE, list(self.unique_domains))

        # CHECK: slow?
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

if __name__=="__main__":
    target_url="https://tecnocampus.cat/"
    threads=20

    s=SpYder(max_domains=200)
    s.clear()

    s.multicrawl(target_url, threads)
    # s.crawl(target_url)