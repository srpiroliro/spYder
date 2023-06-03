import queue
import requests, tldextract
from urllib.parse import urlparse
from datetime import datetime
from os.path import exists
from os import remove
from json import loads, dump

from bs4 import BeautifulSoup

class SpYder:
    HEADERS={
        "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    def __init__(self, max_depth:int=0, internal:bool=True, external:bool=True):
        self.__logs() # wipe logs

        self.session=requests.Session()
        self.session.headers.update(self.HEADERS)

        # CHECK: not efficient?
        self.unique_domains=set()
        self.all_urls={} # start_url:set(links)
        self.visited_urls=set()


        # OPTIONS
        self.max_recursive_depth=max_depth
        self.crawl_internal=internal
        self.crawl_external=external

    def crawl(self,url:str, level:int=0, thread_num:int=0):
        try:
            self.visited_urls.add(url)

            self.__logs(f"crawling '{url}' on level={level}")

            links=self.__get_links(url)
            if not links:
                self.__logs(f"sad :(. no links.")
                return None
            
            self.__logs(f"getting domain")
            start_domain=self.__get_domain(url)
            self.__logs(f"domain is {start_domain}")

            cleared_links=self.__clean_urls(start_domain, url, links)
            
            external_urls=cleared_links["urls"]["external"]
            internal_urls=cleared_links["urls"]["internal"]
            
            all_urls=set()
            if self.crawl_external: all_urls.update(external_urls)
            if self.crawl_internal: all_urls.update(internal_urls)

            # if url not in self.all_urls: self.all_urls[url]=set()
            # self.all_urls[url].update(all_urls)

            self.__logs(f"updating local sets/dicts")

            if start_domain not in self.all_urls: self.all_urls[start_domain]=set()
            self.all_urls[start_domain].update(all_urls)

            self.unique_domains.update(cleared_links["domains"])
            self.__logs(f"saved them all")

            if level<self.max_recursive_depth or level<0:
                self.__logs(f"and the adventure continues!")

                for sub_url in all_urls:
                    if sub_url in self.visited_urls: continue
                    self.crawl(sub_url, level+1)
                
                self.__logs(f"recursivity done! (level={level})")
            else:
                self.__logs(f"no more adventure (level={level})")
            
            if level==0:
                self.__logs(f"saving data")
                self.__save_data()
                self.__logs(f"data saved")

        except Exception as e:
            self.__logs(f"crawl error happend! -> e: {str(e).encode()}")


    # TODO:

    def multileg(self):
        self.queue=queue.Queue()

        # start crawl on first url
        # add found urls to queue
        # start X threads, each thread wait id amount of seconds

    def single(self):
        while not self.queue.isempty(): 
            url=self.queue.get()
            # crawl url 
            # put all results into queue

    # save to local database server
        





    def __get_links(self,url)->list:
        self.__logs(f"getting links of url")
        try:
            response=self.session.get(url)
            assert response.status_code==200

            html=response.text.encode()
            soup=BeautifulSoup(html,"html.parser")
            links=set([node.get("href") for node in soup.find_all("a") if node.get("href")])

            self.__logs(f"got {len(links)} links")

            return links
        except Exception as e:
            self.__logs(f"exception happend: {e}")

            return None

    def __join_url(self, url, path):
        main_url_path=urlparse(url).path

        if not main_url_path or "/"==main_url_path: 
            ready_url=url.strip("/")
        elif path.startswith("/"): 
            ready_url=url.split(main_url_path)[0]
        else: 
            ready_url=url.rsplit("/",1)[0]+"/"

        return ready_url+path

    def __get_domain(self, url):
        subd, name, suffix=tldextract.extract(url)
        return f"{name}.{suffix}".lower()

    def __clean_urls(self, start_domain, start_url, links):
        sorted_urls={"external":set(),"internal":set()}
        domains=set()

        for link in links:
            if link.startswith("http") and "://" in link:
                domain=self.__get_domain(link) # append domain to 

                if domain==start_domain:
                    sorted_urls["internal"].add(link)
                else:
                    sorted_urls["external"].add(link)
                    domains.add(domain)

            elif ":" not in link and not "//" in link and not link.startswith("?") and not link.startswith("#"):
               sorted_urls["internal"].add(self.__join_url(start_url, link)) 

        return {"urls":sorted_urls, "domains":domains}

    def __save_data(self):
        self.__json2file("data/unique_domains.json", list(self.unique_domains))

        # CHECK: slow?
        tmp={}
        for domain in self.all_urls:
            tmp[domain]=list(self.all_urls[domain])
        self.__json2file("data/all_urls.json", tmp)



    def __logs(self, message:str=None, filepath:str="simple.log", thread_num:int=0):
        if message is None:
            with open(filepath, "w") as f: f.write("")
            return
        
        with open(filepath, ("a" if exists(filepath) else "w")) as f:
            f.write("\n["+datetime.today().strftime("%Y-%m-%d %H:%M:%S")+f"] - [{thread_num}] {message}")

    def __file2json(self, filepath) -> dict:
        if not exists(filepath):
            return dict()
        
        with open(filepath,"r") as f:
            return loads(f.read())

    def __json2file(self, filepath, data) -> None:
        if exists(filepath):
            file_contents=self.__file2json(filepath)
            if not type(file_contents) is type(data):
                pass # ignore and later on overwrite
            elif type(file_contents) is list:
                data+=file_contents
            elif type(file_contents) is dict:
                data=data|file_contents
        
        with open(filepath,"w") as f:
            dump(data, f)


if __name__=="__main__":
    for i in ["data/unique_domains.json","data/all_urls.json"]:
        if exists(i): remove(i)

    s=SpYder(max_depth=3, external=False)
    s.crawl("https://tecnocampus.cat/")
