# X 同圈对标库

写长文前，先把自己关注圈的帖子和长文抓到本地，按「倍数」排序，查同题、查标题撞题、找封面参考。

数据走 fxtwitter 公开接口，不用登录、不要 API key，只用 Python 标准库（3.9 以上）。

## 文件

| 文件 | 作用 |
| --- | --- |
| `fx_scrape.py` | fxtwitter 接口的抓取与翻页，断点续跑，已抓过的号跳过 |
| `bench_scrape.py` | 按号单批量抓原创帖（每号约 300 条）和长文列表（每号最多 500 篇），不抓回复；`--update` 只补新帖 |
| `bench_search.py` | 按关键词检索，按倍数排序；`--days` 只看最近几天，`--full` 拉长文全文，`--covers` 下载同题封面，`--check` 查标题撞题 |
| `bench_topcovers.py` | 不限主题，取全库倍数最高的 16 张长文封面 |
| `selftest.py` | 合成数据自测，不联网 |

## 三步

1. 先自测：

   ```bash
   python selftest.py
   ```

   最后一行应为 `PASS`。

2. 写一份号单 `accounts.txt`，每行一个用户名（不带 @），然后抓：

   ```bash
   python bench_scrape.py accounts.txt data
   ```

   速度看接口状态，有时一个号要好几分钟。中途断了重跑同一条命令，已抓过的号会跳过。

   之后想补新帖，加 `--update`：已有的号从最新一页往后翻，翻到一整页都是库里已有的就停，最多 5 页，新帖合并进原文件：

   ```bash
   python bench_scrape.py accounts.txt data --update
   ```

3. 检索：

   ```bash
   python bench_search.py data 对标 选题 爆款 --full 3
   python bench_search.py data --check "候选标题一" --check "候选标题二"
   python bench_search.py data 对标 --covers 3 --out 文章目录
   python bench_topcovers.py data 文章目录/covers/top
   python bench_search.py data 关键词 --days 3 --top 10
   ```

   关键词之间是「或」，命中词越多越靠前，同样命中数按倍数排。`--days 3` 用来写短帖前看同圈这几天谁已经说过；发出不满 24 小时的帖子赞还没涨完，倍数偏低。

## 倍数怎么算

倍数 = 这条的赞数 ÷ 这个号发出满 24 小时的原创内容的中位赞数。帖子和长文分开算中位数。

看的是一条内容在它自己号里算不算爆，不比绝对赞数。平时赞少、偶尔一条爆的号，倍数会很高，要和赞数一起看。

## 三种脏数据

`bench_search.py` 读取时已经处理了前两种：

- **转发混入**：时间线里的转发，赞数是原作者的，中位数却是转发者的，会算出几千倍的假爆款。`author` 不是这个号本身的直接丢掉。
- **置顶帖重复**：置顶帖会在多页里重复出现，既让结果重复，也会改掉中位数。同一个 `id` 只留一条。
- **长文没有正文**：长文列表只给标题和开头几句，正文要拿 `id` 调 `/2/status/<id>` 单独拉，`--full` 做的就是这件事。

## 限制

- `--check` 用两个字一组的字面重合度，只能抓字面几乎一样的标题，意思相近、字面不同的抓不出来。多少算撞题没有实测过。
- fxtwitter 是第三方公开接口，哪天不能用了，库就停在那天。
- 抓下来的是别人的公开内容，留在本地自己用，别整库转发或公开。
