"""对标库抓取：只抓原创帖和长文，不抓回复。已抓过的号会跳过。

用法：python -I bench_scrape.py <号单，每行一个用户名> <数据目录>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_scrape as fx

users = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
for i, u in enumerate(users):
    print("[%d/%d] %s" % (i + 1, len(users), u), flush=True)
    fx.do_statuses(u, sys.argv[2], 300, "statuses")
    fx.do_statuses(u, sys.argv[2], 500, "articles")
print("DONE", flush=True)
