# Spyder

- get inner url link
- which domains does the web link to
- which urls does the web link to
- crawl X levels of depth of urls for more urls/domains
- get missing files from web (css, media, js...)
- get broken links
- 


## todo:
- [ ] pass url, threads, domains... through cli
- [x] blacklisted 
domains

- [ ] possible scenario fix: queue is empty, but the last url is still getting checked. all the other threads will quit.
    - bool:finish=True, when crawled url doesnt return links, finsihed=finished and are_ther_new_links, thus, if there are, will result in False.
    - useful?
- [ ] Ctrl+C exit
- [ ] add Lock to fix logs
- [ ] some links broken 
    - due to char encoding
    - [x] `http//domain.com` (no :) (CHECK)
- [ ] remove XML message

- [ ] add css, media and js checking.
- [ ] multiple starting urls
- [ ] check for 4XX/5XX urls (especially for media,css and js) and return this data.
- [ ] option to save only css, js, media or links.