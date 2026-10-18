"""对标库抓取：只抓原创帖和长文，不抓回复。已抓过的号默认跳过。

用法：python -I bench_scrape.py <号单，每行一个用户名> <数据目录> [--update]
--update：已抓过的号只往前补新帖。从最新一页往后翻，翻到一整页都是库里已有的就停（置顶帖是旧帖、总在第一页，
所以不能碰到第一条旧帖就停），最多翻 5 页；新帖合并到原文件最前面。
"""
import json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_scrape as fx

MAX_PAGES = 5


def update(user, datadir, kind):
    path = os.path.join(datadir, kind, "%s.json" % user)
    if not os.path.exists(path):
        fx.do_statuses(user, datadir, 300 if kind == "statuses" else 500, kind)
        return
    with open(path, encoding="utf-8") as f:
        old = json.load(f)
    known = {x.get("id") for x in old.get("results") or []}
    path_kind, extra = fx.KINDS.get(kind, (kind, {}))
    new, cursor, status = [], None, "end"
    for _ in range(MAX_PAGES):
        q = dict(extra)
        if cursor:
            q["cursor"] = cursor
        url = fx.API.format(u=user, kind=path_kind) + ("?" + urllib.parse.urlencode(q) if q else "")
        d = fx.get(url)
        if not d or d.get("code") != 200:
            status = "error:%s" % (d or {}).get("code")
            break
        res = d.get("results") or []
        fresh = [x for x in res if x.get("id") not in known]
        new += fresh
        known.update(x.get("id") for x in fresh)
        cursor = (d.get("cursor") or {}).get("bottom")
        if not fresh or not cursor:
            break
        time.sleep(1.0)
    else:
        status = "pages"  # 翻满 5 页还有新帖，中间可能漏了，要全量重抓才补得齐
    old["results"] = new + (old.get("results") or [])
    old["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    fx.save(path, old)
    print(kind, user, "+%d" % len(new), status, flush=True)


if __name__ == "__main__":
    users = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    upd = "--update" in sys.argv[3:]
    for i, u in enumerate(users):
        print("[%d/%d] %s" % (i + 1, len(users), u), flush=True)
        for kind, n in (("statuses", 300), ("articles", 500)):
            if upd:
                update(u, sys.argv[2], kind)
            else:
                fx.do_statuses(u, sys.argv[2], n, kind)
    print("DONE", flush=True)
