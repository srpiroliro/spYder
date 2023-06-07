from spyder import SpYder

target_url="https://tecnocampus.cat/"
threads=10

s=SpYder(max_domains=200, plot_it=True, internal=False)
s.clear()

s.multicrawl(target_url, threads)
# s.crawl(target_url)