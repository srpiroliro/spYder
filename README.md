# Spyder

## todo:
- [x] queues
- [x] multithreading
- [x] incorrect unique domains !!!
- [ ] prioritize which url goes into the queue
    - unique domain? +++
- [ ] visited_urls: www.link != link
    - ```visited_urls={}; /* domain:paths[] */ if cleaned_url_path in visited_urls[domain]: continue;```
    - save urls in the same format (get_domain+get_path)
- [ ] draw a map of graphs to display the connections
    - we need: 
        - nodes: domains[]
        - connections: (domainA,domainB)
    - generate after execution or during?


- [ ] possible scenario fix: queue is empty, but the last url is still getting checked. all the other threads will quit.
    - bool:finish=True, when crawled url doesnt return links, finsihed=finished and are_ther_new_links, thus, if there are, will result in False.
    - useful?
- [ ] Ctrl+C exit
- [ ] add Lock to fix logs
- [ ] some links broken 
    - due to char encoding
    - `http//domain.com` (no :)
- [ ] remove XML message


## walkthrough:
    1. get starting url
    2. crawl that url and get the links in it.
    3. add those links in the queue if they aren't in already. 
        - for now store visited urls in ram.
    4. spawn X threads
    5. go back to point 2 and repeat.
        - add option to stop after:
            - X different domains.
            - Y unique urls.
            - Z depth levels.
