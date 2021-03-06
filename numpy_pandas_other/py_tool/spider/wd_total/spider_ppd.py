#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
      拍拍贷数据爬虫
"""

import time
import requests
from lxml import etree
import json
import sys
import collections
from requests.exceptions import ProxyError
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)
# 代理
proxies = {
  "HTTPS": "https://114.230.234.223:808",
  "HTTP": "http://110.73.6.124:8123",
  "HTTPS": "https://221.229.44.14:808",
  "HTTP": "http://116.226.90.12:808",
  "HTTPS": "https://218.108.107.70:909"
}


# 爬取数据
def spider_wd():
    try:
        # 先直接获取
        url = 'http://www.ppdai.com/'
        try:
            # 使用代理
            con = requests.get(url, timeout=10, proxies=proxies).content
        except ProxyError:
            print("ProxyError Exception ,use no proxies ")
            # 不使用代理
            con = requests.get(url, timeout=10).content

        # xpath解析
        tree = etree.HTML(con)
        # 返回结果
        result = collections.OrderedDict()
        result['来源平台'] = '拍拍贷'

        # 总投资额
        total_sum = tree.xpath("/html/body/div[3]/div[1]/div[2]/div[1]/div/div/div[2]/p[3]/text()")[0]
        total_sum = float(total_sum.replace(',', '').replace('万', ''))/10000
        result['投资总额'] = str(total_sum) + '亿元'

        # 已赚取
        result['已赚取'] = ''

        # 待赚取
        result['待赚取'] = ''

        # 今日成交额
        result['今日成交额'] = ''

        # 总注册用户数
        total_count = tree.xpath("/html/body/div[3]/div[1]/div[2]/div[1]/div/div/div[1]/p[1]/text()")[0]
        total_count = float(total_count.replace(',', ''))/10000
        result['注册用户数'] = str(total_count) + '万'

        # 数据日期
        result['日期'] = time.strftime('%Y-%m-%d')

        return result
    except Exception as e:
        print("爬取失败", e)
        return -1


# 爬取数据（处理超时异常,默认10次重试），并组装成json格式数据
def re_spider_wd():
    result = spider_wd()
    # 如果没有获取到数据则重试多次
    if result == -1:
        # 如果没有爬取成功则，重爬
        for num in range(1, 10):
            time.sleep(0.5)
            print(num)
            if result == -1:
                result = spider_wd()
            else:
                break

    # 结果数据的封装
    message = collections.OrderedDict()
    if result == -1:
        message['statue_code'] = 0
    else:
        message['statue_code'] = 1
        message['msg'] = result
    return json.dumps(message).decode('unicode-escape')

if __name__ == '__main__':
    for n in range(1, 2):
        print(n)
        print(spider_wd())


