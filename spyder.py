import requests, traceback, tldextract

from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from os.path import exists
from pprint import pprint


class SpYder:
    HEADERS={
        "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    def __init__(self, max_depth:int=3):
        self.session=requests.Session()
        self.session.headers.update(self.HEADERS)

        self.unique_domains=set()
        self.all_urls={} # start_url:set(links)

        self.max_recursive_depth=max_depth

    def crawl(self,url:str, level:int=0, recursive:bool=False):
        links=self.__get_links(url)
        if links:
            start_domain=self.__get_domain(url)
            cleared_links=self.__clean_urls(start_domain, url, links)
            
            external_urls=cleared_links["urls"]["external"]
            internal_urls=cleared_links["urls"]["internal"]
            
            all_urls=external_urls.copy()
            all_urls.update(internal_urls)

            # if url not in self.all_urls: self.all_urls[url]=set()
            # self.all_urls[url].update(all_urls)
            
            if start_domain not in self.all_urls: self.all_urls[start_domain]=set()
            self.all_urls[start_domain].update(all_urls)

            self.unique_domains.update(cleared_links["domains"])

            if recursive and level<self.max_recursive_depth:
                for url in all_urls: 
                    self.crawl(url, level+1, recursive)



    def __get_links(self,url)->list:
        self.__logs(f"getting links of url: {url}")
        try:
            response=self.session.get(url)
            assert response.status_code==200

            html=response.text
            soup=BeautifulSoup(html,"html.parser")
            links=set([node.get("href") for node in soup.find_all("a") if node.get("href")])

            self.__logs(f"got {len(links)} links")

            return links
        except Exception as e:
            self.__logs(f"exception happend: {e}")

            return None

    def __join_url(self, url, path):
        main_url_path=urlparse(url).path

        if not main_url_path: ready_url=url
        elif path.startswith("/"): ready_url=url.split(main_url_path)[0]
        else: ready_url=url.rsplit("/")[0]+"/"
        
        return ready_url+path

    def __get_domain(self, url):
        subd, name, suffix=tldextract.extract(url)
        return f"{name}.{suffix}".lower()

    def __clean_urls(self, start_domain, start_url, links):
        sorted_urls={"external":set(),"internal":set()}
        domains=set()

        for link in links:
            if "http" in link and "://" in link:
                domain=self.__get_domain(link) # append domain to 
                if domain==start_domain: sorted_urls["internal"].add(link)
                else:
                    sorted_urls["external"].add(link)
                    domains.add(domain)
            elif ":" not in link:
               sorted_urls["internal"].add(self.__join_url(start_url, link))

        return {"urls":sorted_urls, "domains":domains}



    def __logs(self, message, filepath:str="simple.log"):
        with open(filepath, ("a" if exists(filepath) else "w")) as f:
            f.write("["+datetime.today().strftime("%Y-%m-%d %H:%M:%S")+f"] - {message}\n")


if __name__=="__main__":
    s=SpYder()
    s.crawl("https://tecnocampus.cat")

    print("ALL URLS")
    pprint(s.all_urls)

    print("\n\nUNIQUE DOMAINS")
    pprint(s.unique_domains)
