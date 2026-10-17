"""全库封面参考：不限主题，按倍数取前 16 张长文封面（至少 50 赞、发出满 24 小时、每号最多 2 张）。

用法：python -I bench_topcovers.py <数据目录> <输出目录>
"""
import os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_search as b

arts = b.load(sys.argv[1], "articles")
med = b.medians(arts)
rows = []
for u, rs in arts.items():
    for x in rs:
        l = x.get("likes") or 0
        if l >= 50 and b.cover_url(x) and b.age_hours(x) >= 24:
            rows.append((l / med[u], l, u, x))
rows.sort(key=lambda r: -r[0])
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
seen, n = {}, 0
for m, l, u, x in rows:
    if seen.get(u, 0) >= 2:
        continue  # 每号最多 2 张，避免一个号刷屏
    url = b.cover_url(x)
    ext = os.path.splitext(url)[1] or ".jpg"
    p = os.path.join(out, "%02d_%.1fx_%d_%s%s" % (n + 1, m, l, u, ext))
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?name=small", headers=b.UA), timeout=30) as r, open(p, "wb") as fh:
            fh.write(r.read())
    except Exception as e:
        print("fail", u, e)
        continue
    seen[u] = seen.get(u, 0) + 1
    n += 1
    print(os.path.basename(p), "|", (x.get("article") or {}).get("title"))
    if n >= 16:
        break
