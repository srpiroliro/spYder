import requests
from bs4 import BeautifulSoup
import traceback

def get_links(url)->list:
    try:
        response=session.get(url)
        assert response.status_code==200

        html=response.text
        soup=BeautifulSoup(html)
        return set([node.get("href") for node in soup.find_all("a")])
    except Exception as e: 


    return []


    

starting_url="https://"


headers={
    "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}


session=requests.Session()
session.headers.update(headers)

session.get()