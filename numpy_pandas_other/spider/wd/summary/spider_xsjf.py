#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
      向上金服数据爬虫
"""
import time
import requests
import json
import sys
import collections
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)


# 爬取数据
def spider_wd():
    try:
        # 先直接获取
        url = 'https://www.xiangshang360.com/xweb/disclosure/index?_='+str(int(round(time.time() * 1000)))
        con = requests.get(url, timeout=10).content
        rest = json.loads(con)

        # 返回结果
        result = collections.OrderedDict()
        result['来源平台'] = '向上金服'

        # 总投资额
        total_sum = float(rest['data']['lenderTotalAmount'].replace(',', ''))/100000000
        result['投资总额'] = str(total_sum) + '亿元'

        # 已赚取
        earn_sum = float(rest['data']['lenderTotalInterestAmount'].replace(',', ''))/100000000
        result['已赚取'] = str(earn_sum) + '亿元'

        # 待赚取
        not_earn_sum = float(rest['data']['borrowerTotalUnRepayAmount'].replace(',', '')) / 100000000
        result['待赚取'] = str(not_earn_sum) + '亿元'

        # 今日成交额
        result['今日成交额'] = ''

        # 注册用户数
        total_count = float(rest['data']['totalRegUserCount'])/10000
        result['注册用户数'] = str(total_count) +'万'

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
    for n in range(1, 200):
        print(n)
        print(re_spider_wd())


