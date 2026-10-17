"""合成数据自测：不联网，不需要真实数据。验证去转发、置顶去重和倍数算法。最后一行应为 PASS。"""
import io, json, os, sys, tempfile, time
from contextlib import redirect_stdout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_search as b

old = time.time() - 3 * 86400  # 三天前，满 24 小时才进中位数


def post(i, likes, text, author="alice"):
    return {"id": str(i), "likes": likes, "text": text, "created_timestamp": old,
            "author": {"screen_name": author}, "url": "https://x.com/%s/status/%d" % (author, i)}


d = tempfile.mkdtemp()
os.makedirs(os.path.join(d, "statuses"))
alice = [post(i, 10, "日常 %d" % i) for i in range(1, 10)]
alice.append(post(100, 100, "沙箱 实测"))                          # 本号原创，10 倍
alice.append(post(100, 100, "沙箱 实测"))                          # 置顶帖在分页里重复
alice.append(post(200, 50000, "沙箱 官方公告", author="official"))  # 转发，不算本号内容
json.dump({"results": alice}, open(os.path.join(d, "statuses", "alice.json"), "w", encoding="utf-8"))

data = b.load(d, "statuses")
assert len(data["alice"]) == 10, "去转发或去重失败：%d" % len(data["alice"])
assert b.medians(data)["alice"] == 10, "中位数错误"

buf = io.StringIO()
sys.argv = ["bench_search.py", d, "沙箱"]
with redirect_stdout(buf):
    b.main()
out = buf.getvalue()
assert "命中 1 条" in out and "10.0倍 100赞" in out and "official" not in out, out
print("PASS")
