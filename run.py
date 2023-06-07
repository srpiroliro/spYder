from spyder import SpYder

target_url="https://tecnocampus.cat/"
threads=40

s=SpYder(
    max_domains=4000, 
    plot_it=True, 
    internal=False,
    external=True
)
s.clear()

s.multicrawl(target_url, threads)
# s.crawl(target_url)