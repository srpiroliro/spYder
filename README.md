# Spyder

## use cases
- copy all content
- get all visible pages (not optimized for this, only requesting head would be better.)
- get domains
- scrap images


## 1. single website crawler
crawls the whole provided website from an url start point to get all the possible links

1. get url starting point
2. open url
3. scan page
4. get all links (visible and not visible)
5. filter links to only local ones + not visited links (save external links to a list)
6. for each link go to point 3 and repeat.

- - -

## 2. www crawler
starts from a website and continues crawling.

go website by website or go link by link?

1. open starting point
2. scan all links

## visualization
For both progs, create a way to visualize the data in a node graph. Each node should represent a page within the single website crawler. On the www crawler, each node should represent a separate website.

