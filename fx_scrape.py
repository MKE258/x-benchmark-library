"""抓 fxtwitter 公开接口：关注列表 / 推文。可断点续跑，已抓过的文件跳过。

用法：
  python -I fx_scrape.py following <user> <datadir>
  python -I fx_scrape.py statuses <user> <datadir> [max_posts]
  python -I fx_scrape.py self <user> <datadir> [max_posts]        # 本号：原创 + 约 2000 条回复 + 长文
  python -I fx_scrape.py batch <listfile> <datadir> [max_posts]   # listfile 每行一个用户名
"""
import json, os, sys, time, urllib.parse, urllib.request

API = "https://api.fxtwitter.com/2/profile/{u}/{kind}"
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, tries=8):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read().decode("utf-8"))
            except Exception:
                data = {"code": e.code}
        except Exception as e:
            data = {"code": -1, "err": repr(e)}
        if data.get("code") == 200 and data.get("results") is not None:
            return data
        last = data
        time.sleep(1.5 + i * 1.5)
    return last


KINDS = {"statuses": ("statuses", {}), "replies": ("statuses", {"with_replies": "true"}), "articles": ("articles", {})}


def paged(user, kind, limit, page_sleep=1.0):
    out, cursor, seen = [], None, set()
    path, extra = KINDS.get(kind, (kind, {}))
    while len(out) < limit:
        q = dict(extra)
        if cursor:
            q["cursor"] = cursor
        url = API.format(u=user, kind=path)
        if q:
            url += "?" + urllib.parse.urlencode(q)
        d = get(url)
        if not d or d.get("code") != 200:
            return out, "error:%s" % (d or {}).get("code")
        res = d.get("results") or []
        new = [x for x in res if x.get("id") not in seen]
        if not new:
            return out, "end"
        for x in new:
            seen.add(x.get("id"))
        out += new
        cursor = (d.get("cursor") or {}).get("bottom")
        if not cursor:
            return out, "end"
        time.sleep(page_sleep)
    return out, "limit"


def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def do_following(user, datadir):
    path = os.path.join(datadir, "following_%s.json" % user)
    if os.path.exists(path):
        print("skip", path)
        return
    res, status = paged(user, "following", 5000)
    save(path, {"user": user, "status": status, "results": res})
    print("following", user, len(res), status)


def do_statuses(user, datadir, max_posts, kind="statuses"):
    os.makedirs(os.path.join(datadir, kind), exist_ok=True)
    path = os.path.join(datadir, kind, "%s.json" % user)
    if os.path.exists(path):
        print("skip", kind, user)
        return
    res, status = paged(user, kind, max_posts)
    save(path, {"user": user, "status": status, "fetched": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": res})
    print(kind, user, len(res), status, flush=True)


if __name__ == "__main__":
    cmd, arg, datadir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(datadir, exist_ok=True)
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    if cmd == "following":
        do_following(arg, datadir)
    elif cmd == "statuses":
        do_statuses(arg, datadir, mx)
    elif cmd == "self":  # 本号：回复抓多一些，才能覆盖约一个月
        do_statuses(arg, datadir, mx, "statuses")
        do_statuses(arg, datadir, 2000, "replies")
        do_statuses(arg, datadir, 500, "articles")
    elif cmd == "batch":
        users = [l.strip() for l in open(arg, encoding="utf-8") if l.strip()]
        for i, u in enumerate(users):
            print("[%d/%d]" % (i + 1, len(users)), flush=True)
            do_statuses(u, datadir, mx, "statuses")
            do_statuses(u, datadir, mx, "replies")
            do_statuses(u, datadir, 500, "articles")
