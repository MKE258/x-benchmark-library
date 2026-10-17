"""对标库检索：在本地抓好的同圈号帖子和长文里按关键词找同题内容，按「倍数」排序。

倍数 = 赞数 ÷ 该号同类内容（帖子或长文）的中位赞数，看它在本号里算不算爆，不比绝对赞数。
长文多、平时赞少的号倍数会偏高，要和赞数一起看。
长文列表只带标题和摘要（摘要即开头几句），--full 会把排名靠前的长文全文单独拉回来存成 md。

用法：
  python -I bench_search.py <datadir> 关键词1 [关键词2 ...] [--top 15] [--full 3] [--covers 5] [--out <目录>]
  python -I bench_search.py <datadir> --check "候选标题1" [--check "候选标题2" ...]
关键词之间是「或」，命中越多越靠前。
--covers N：把同题长文里排名靠前、带封面的 N 张封面图下载到 <out>/covers，供人看。
--check：拿候选标题和全库长文标题比字面重合度（中文按两字片段算），列出最像的 3 个。
"""
import json, os, re, statistics, sys, time, urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0"}


def load(datadir, kind):
    out = {}
    d = os.path.join(datadir, kind)
    if not os.path.isdir(d):
        return out
    for f in os.listdir(d):
        if f.endswith(".json"):
            u = f[:-5]
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                rs = json.load(fh).get("results") or []
            # 去掉转发：转发记录的 author 是原作者，不算本号内容
            seen, keep = set(), []
            for x in rs:
                if ((x.get("author") or {}).get("screen_name") or u).lower() != u.lower() or x.get("id") in seen:
                    continue  # 置顶帖会在分页里重复出现
                seen.add(x.get("id"))
                keep.append(x)
            out[u] = keep
    return out


def age_hours(x):
    ts = x.get("created_timestamp")
    return (time.time() - ts) / 3600 if ts else 1e9


def medians(posts_by_user):
    m = {}
    for u, rs in posts_by_user.items():
        likes = [x.get("likes") or 0 for x in rs if age_hours(x) >= 24]
        m[u] = max(statistics.median(likes), 1) if likes else 1
    return m


def text_of(x, kind):
    if kind == "articles":
        a = x.get("article") or {}
        return (a.get("title") or "") + "\n" + (a.get("preview_text") or "")
    return x.get("text") or ""


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_full(sid):
    d = get_json("https://api.fxtwitter.com/2/status/%s" % sid)
    a = (d.get("status") or {}).get("article") or {}
    blocks = (a.get("content") or {}).get("blocks") or []
    return a.get("title") or "", "\n".join(b.get("text", "") for b in blocks)


def cover_url(x):
    c = (x.get("article") or {}).get("cover_media") or {}
    return (c.get("media_info") or {}).get("original_img_url")


def grams(s):
    s = re.sub(r"[\W_]+", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def day_of(x):
    return datetime.fromtimestamp(x.get("created_timestamp") or 0, timezone.utc).strftime("%Y-%m-%d")


def check_titles(datadir, cands):
    arts = load(datadir, "articles")
    med = medians(arts)
    pool = []
    for u, rs in arts.items():
        for x in rs:
            t = (x.get("article") or {}).get("title") or ""
            if t:
                pool.append((u, t, x, (x.get("likes") or 0) / med[u]))
    for c in cands:
        g = grams(c)
        scored = sorted(((len(g & grams(t)) / len(g | grams(t)), u, t, x, m) for u, t, x, m in pool), key=lambda s: -s[0])[:3]
        print("== 候选：%s ==" % c)
        for sim, u, t, x, m in scored:
            print("重合 %.2f | %.1f倍 %d赞 @%s %s | %s | %s" % (sim, m, x.get("likes") or 0, u, day_of(x), t, x.get("url")))
        print()


def main():
    args = sys.argv[1:]
    datadir = args[0]
    opts = {"--top": "15", "--full": "0", "--covers": "0", "--out": ""}
    kws, checks, i = [], [], 1
    while i < len(args):
        if args[i] == "--check":
            checks.append(args[i + 1])
            i += 2
        elif args[i] in opts:
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            kws.append(args[i].lower())
            i += 1
    if checks:
        check_titles(datadir, checks)
        if not kws:
            return
    top, nfull, ncov = int(opts["--top"]), int(opts["--full"]), int(opts["--covers"])
    out = opts["--out"] or datadir

    hits = []
    for kind in ("articles", "statuses"):
        data = load(datadir, kind)
        med = medians(data)
        for u, rs in data.items():
            for x in rs:
                if kind == "statuses" and "/i/article/" in (x.get("text") or ""):
                    continue  # 长文的转发壳，正文在 articles 里
                t = text_of(x, kind)
                n = sum(1 for k in kws if k in t.lower())
                if n:
                    likes = x.get("likes") or 0
                    hits.append((kind, u, n, likes / med[u], likes, x, t))

    for kind, label in (("articles", "长文"), ("statuses", "帖子")):
        hs = sorted([h for h in hits if h[0] == kind], key=lambda h: (-h[2], -h[3]))[:top]
        print("== %s：命中 %d 条，列前 %d ==" % (label, sum(1 for h in hits if h[0] == kind), len(hs)))
        for _, u, n, mult, likes, x, t in hs:
            if kind == "articles":
                a = x.get("article") or {}
                head = "标题：%s | 开头：%s" % (a.get("title") or "", " ".join((a.get("preview_text") or "").split())[:60])
                if cover_url(x):
                    head += " | 有封面"
            else:
                head = " ".join(t.split())[:80]
            print("%.1f倍 %d赞 命中%d @%s %s | %s | %s" % (mult, likes, n, u, day_of(x), head, x.get("url")))
        print()

    arts = sorted([h for h in hits if h[0] == "articles"], key=lambda h: (-h[2], -h[3]))
    if nfull:
        d = os.path.join(out, "full")
        os.makedirs(d, exist_ok=True)
        for _, u, n, mult, likes, x, t in arts[:nfull]:
            try:
                title, body = fetch_full(x["id"])
            except Exception as e:
                print("全文失败", x.get("url"), repr(e))
                continue
            p = os.path.join(d, "%s_%s.md" % (u, x["id"]))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("# %s\n\n@%s · %d赞 · %.1f倍 · %s\n\n%s\n" % (title, u, likes, mult, x.get("url"), body))
            print("全文已存", p)

    if ncov:
        d = os.path.join(out, "covers")
        os.makedirs(d, exist_ok=True)
        got = 0
        for _, u, n, mult, likes, x, t in sorted(arts, key=lambda h: -h[3]):  # 封面只看倍数，不看命中词数
            url = cover_url(x)
            if not url:
                continue
            ext = os.path.splitext(url)[1] or ".jpg"
            p = os.path.join(d, "%02d_%.1fx_%s_%s%s" % (got + 1, mult, u, x["id"], ext))
            try:
                req = urllib.request.Request(url + "?name=small", headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r, open(p, "wb") as fh:
                    fh.write(r.read())
            except Exception as e:
                print("封面失败", x.get("url"), repr(e))
                continue
            print("封面已存", p, "|", (x.get("article") or {}).get("title"))
            got += 1
            if got >= ncov:
                break


if __name__ == "__main__":
    main()
