import json
import os.path
import re
from datetime import datetime, timedelta

import requests
from lxml import etree
from requests.exceptions import RequestException

utctime = datetime.utcnow()
bjtime = utctime + timedelta(hours=8)
baseurl = 'https://s.weibo.com'
today_str = bjtime.strftime("%Y-%m-%d")
archive_filepath = f"./archives/{today_str}"
raw_filepath = f"./raw/{today_str}"


# 加载文件
def load(filename):
    with open(filename, 'r', encoding="utf-8") as f:
        content = f.read()
    return content


# 保存文件
def save(filename, content):
    with open(filename, 'w', encoding="utf-8") as f:
        if filename.endswith('.json') and isinstance(content, dict):
            json.dump(content, f, ensure_ascii=False, indent=2)
        else:
            f.write(content)


# 获取内容
def fetch_weibo(url):
    try:
        headers = {
            "Cookie": "SUB=_2AkMWIuNSf8NxqwJRmP8dy2rhaoV2ygrEieKgfhKJJRMxHRl-yT9jqk86tRB6PaLNvQZR6zYUcYVT1zSjoSreQHidcUq7",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36 Edg/90.0.818.41"
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            print("抓取完毕...")
            return resp.content.decode("utf-8")
        return None
    except RequestException:
        return None


# xpath解析微博热搜数据
def parse_weibo(content):
    html = etree.HTML(content)
    xpath = '//*[@id="pl_top_realtimehot"]/table/tbody/tr[position()>1]/td[@class="td-02"]/a[not(contains(@href, "javascript:void(0);"))]'
    titles = html.xpath(f'{xpath}/text()')
    hrefs = html.xpath(f'{xpath}/@href')
    hots = html.xpath(f'{xpath}/../span/text()')
    titles = [title.strip() for title in titles]
    hrefs = [f"{baseurl}{href.strip()}" for href in hrefs]
    hots = [hot.strip() for hot in hots]
    hot_news = {}
    for i, title in enumerate(titles):
        hot_news[title] = {'url': f"{hrefs[i]}", 'hot': int(re.findall(r'\d+', hots[i])[0])}
    print("解析完毕...")
    return hot_news


# 更新榜单，与当天历史榜单对比去重，降序排列
def update_hot_news(hot_news):
    his_filename = raw_filepath + ".json"
    if not os.path.exists(his_filename):
        save(his_filename, {})
    # 读取当天历史榜单
    his_hot_news = json.loads(load(his_filename))
    for k, v in hot_news.items():
        # 若当天榜单和历史榜单有重复，取热度数值更大的这一个
        if k in his_hot_news:
            his_hot_news[k]['hot'] = max(int(his_hot_news[k]['hot']), int(hot_news[k]['hot']))
            # 若没有，则添加到榜单
        else:
            his_hot_news[k] = v
    # 将榜单按hot值排序
    sorted_news = {k: v for k, v in sorted(his_hot_news.items(), key=lambda item: int(item[1]['hot']), reverse=True)}
    save(his_filename, sorted_news)
    save_csv(sorted_news)
    return sorted_news


# 加载停用词
# def stopwords():
#     stopwords = [line.strip() for line in open('stopwords.txt', encoding='UTF-8').readlines()]
#     return stopwords


def save_csv(sorted_news):
    str = f'{today_str},' + ",".join([k for k, v in sorted_news.items()])
    save(f'{archive_filepath}.csv', str)


# 生成词云
# def wordcloud(sorted_news):
#     str = f'{today_str},' + ",".join([k for k, v in sorted_news.items()])
#     sentence_seged = jieba.lcut(str)
#     swords = stopwords()
#     jieba_text = []
#     for word in sentence_seged:
#         if word not in swords:
#             jieba_text.append(word)
#     wd_join_text = " ".join(jieba_text)
#     # mask = np.array(Image.open("weibo.png"))
#     wc = WordCloud(font_path="msyh.ttf", width=1600, height=900, mask=None).generate_from_text(wd_join_text)
#     plt.figure()
#     plt.imshow(wc, interpolation="bilinear")
#     plt.axis("off")
#     wc.to_file(f"{archive_filepath}.png")
#     print("生成词云完毕...")


def update_readme(news):
    line = '1. [{title}]({url}) {hot}'
    lines = [line.format(title=k, hot=v['hot'], url=v['url']) for k, v in news.items()]
    lines = '\n'.join(lines)
    tm = datetime.now().strftime("%Y-%m-%d")
    yd = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d') 
    pth = os.path.join('./_post',f'{yd}-wb.md')
    new_pth = os.path.join('./_post',f'{tm}-wb.md')
    if os.path.exists(new_pth):
        pth = new_pth
        print(pth)
    # lines = f'<!-- BEGIN --> \r\n最后更新时间 {datetime.now()} \r\n![{archive_filepath}]({archive_filepath}.png) \r\n' + lines + '\r\n<!-- END -->'
    lines = f'<!-- BEGIN --> \r\n最后更新时间 {datetime.now()} \r\n' + lines + '\r\n<!-- END -->'
    content = re.sub(r'<!-- BEGIN -->[\s\S]*<!-- END -->', lines, load(pth))
    save(new_pth, content)


def save_archive(news):
    line = '1. [{title}]({url}) {hot}'
    lines = [line.format(title=k, hot=v['hot'], url=v['url']) for k, v in news.items()]
    lines = '\n'.join(lines)
    # lines = f'## {today_str}热门搜索 \r\n最后更新时间 {datetime.now()} \r\n![{today_str}]({today_str}.png) \r\n' + lines + '\r\n'
    lines = f'## {today_str}热门搜索 \r\n最后更新时间 {datetime.now()} \r\n' + lines + '\r\n'
    save(f'{archive_filepath}.md', lines)


if __name__ == '__main__':
    url = f'{baseurl}/top/summary?cate=realtimehot'
    content = fetch_weibo(url)
    hot_news = parse_weibo(content)
    sorted_news = update_hot_news(hot_news)
    # wordcloud(sorted_news)
    update_readme(sorted_news)
    save_archive(sorted_news)
