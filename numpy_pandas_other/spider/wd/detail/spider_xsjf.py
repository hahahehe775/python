#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
      向上金服标的爬虫
"""
import pymysql.cursors
import time
import requests
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
# 还款方式
repayment_type = {
    "AVERAGE_CAPITAL_PLUS_INTEREST": "等额本息",
    "MONTH_RETURN_INTEREST": "先息后本",
    "LAST_REBATE_CAPITAL_PLUS_INTEREST": "到期本息"
                 }
# 平台名称
source_from = "向上金服"
# 详细信息的链接(委托投标)
detail_link_wei = "https://www.xiangshang360.com/xweb/planlistsecond"
# 详细信息的链接(主动投标)
detail_link_zhu = "https://www.xiangshang360.com/xweb/bidding/list"
# 详细信息的链接(转让项目)
detail_link_zhuan = "https://www.xiangshang360.com/xweb/bidding/transfer/list"
# 数据库配置
config = {
    'host': '172.16.34.48',
    'port': 3306,
    'user': 'bigdata_read',
    'password': 'bigdata_read',
    'db': 'cgjrRisk',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def parse_data(result_data, url_type):
    """数据的抽取

    :param result_data: 请求到的数据
    :param url_type: 请求的类型
    :return: :list集合
    :rtype:
    """
    # 一页的数据
    data_list = []
    if "wei" == url_type:
        datas = result_data["data"]["productPlanVos"]
    if "zhu" == url_type:
        datas = result_data["data"]["biddingList"]
    if "zhuan" == url_type:
        datas = result_data["data"]["biddingTransferList"]
    # 如果没有数据，则返回集合元素为0
    if datas is None or 0 == len(datas):
        return data_list
    for data in datas:
        # 返回结果
        result = collections.OrderedDict()
        result['来源平台'] = source_from
        # 项目名称
        result["项目名称"] = data["plname"]
        # 年化收益
        result['年化收益'] = data["expRate"]
        # 转让项目
        if "zhuan" == url_type:
            # 项目类型
            result['项目类型'] = "转让项目"
            # 标id
            result["标id"] = data["applyKey"]
            # 投资期限
            result['投资期限'] = str(data["residualMaturity"]) + "天"
            # 还款方式
            result['还款方式'] = repayment_type[data["repaymentType"]]
            # 项目总额
            result['项目总额'] = ""
            # 剩余金额
            result['剩余金额'] = ""
            # 起投金额
            result['起投金额'] = ""
            # 转让价格
            result['转让价格'] = data["transferAmount"].replace(",", "")
            # 债权价值
            result['债权价值'] = data["applyLoanValue"].replace(",", "")
            # 转让人
            result['转让人'] = data["realNameFrom"]
            # 项目开始时间
            result['项目开始时间'] = data["startTime"]
            # 项目结束时间
            result['项目结束时间'] = data["endTime"]
        # 其他非转让项目
        if "wei" == url_type or "zhu" == url_type:
            # 标id
            result["标id"] = data["plnKey"]
            # 投资期限
            result['投资期限'] = str(data["forceExitDay"])+"天"
            # 剩余金额
            result['剩余金额'] = data["remainAmount"]
            # 起投金额
            result['起投金额'] = data["minBuyerAmount"]
            # 转让价格
            result['转让价格'] = ""
            # 债权价值
            result['债权价值'] = ""
            # 转让人
            result['转让人'] = ""
            # 项目开始时间
            result['项目开始时间'] = "0001-01-01 00:00:00"
            # 项目结束时间
            result['项目结束时间'] = "0001-01-01 00:00:00"
            # 项目类型
            if "wei" == url_type:
                result['项目类型'] = "委托投标"
                # 还款方式
                result['还款方式'] = data["allowAutoExit"]
                # 项目总额
                result['项目总额'] = data["totalAmt"].replace(",", "")
            if "zhu" == url_type:
                result['项目类型'] = "主动投标"
                # 还款方式
                result['还款方式'] = data["repaymentType"]
                # 项目总额
                result['项目总额'] = data["totalAmount"].replace(",", "")
            # 追加到集合中
        data_list.append(result)
    return data_list


def package_data(result):
    """数据最终结果的封装
    """
    # 结果数据的封装
    message = collections.OrderedDict()
    if result == 0:
        message["statue_code"] = 0
        message["msg_size"] = 0
    else:
        message["statue_code"] = 1
        message["msg_size"] = len(result)
        message["msg"] = result
    return json.dumps(message).decode("unicode-escape")


def spider_wd(url, payload):
    """爬取数据(容错的方式爬取)

    :param url: 请求的链接
    :param payload: 请求的参数
    :return: :数据
    :rtype:
    """
    try:
        try:
            # 使用代理
            result = requests.get(url, timeout=10, params=payload, proxies=proxies).content
        except ProxyError:
            print("ProxyError Exception ,use no proxies ")
            # 不使用代理
            result = requests.get(url, timeout=10, params=payload).content
        return result
    except Exception as e:
        print("爬取失败", e)
        return 0


def re_spider_wd(url, payload):
    """爬取数据（处理超时异常,默认10次重试）

    :param url: 请求的链接
    :param payload: 请求的参数
    :return: :爬取到的数据
    :rtype:
    """
    result = spider_wd(url, payload)
    result = json.loads(result)
    # 1.异常、2.结果不正确、3.结果失败。都需要重试
    # 如果没有获取到数据则重试多次
    if 200 == result["code"]:
        # 如果没有爬取成功则，重爬
        for num in range(1, 20):
            if 200 == result["code"]:
                print("reconnect "+str(num)+" times!!!")
                time.sleep(2)
                result = spider_wd(url, payload)
            else:
                break
    return result


def insert_db(result):
    """
    写到mysql中
    """
    # 插入的记录数
    insert_count = 0
    connection = pymysql.connect(**config)
    try:
        result = json.loads(result)
        if result['statue_code'] != 0:
            with connection.cursor() as cursor:
                sql = 'INSERT INTO ods_xsjf_project_info (id, from_platform, project_type, project_name, ' \
                      'rate, duration, repayment_style, project_amount, ' \
                      'remain_amount, min_amount, transfer_amount, apply_loan_value, ' \
                      'transfer_user_name, open_time, close_time, stat_time)' \
                      ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

                # 批量插入,放到集合中
                msg_list = []
                for m in result['msg']:
                    bid = m["标id".decode("utf-8")]
                    # 如果数据库中没有记录，则插入
                    if 0 == cursor.execute("SELECT * FROM ods_xsjf_project_info WHERE id='"+bid+"'"):
                        msg_data = (m["标id".decode("utf-8")],
                                    m["来源平台".decode("utf-8")],
                                    m["项目类型".decode("utf-8")],
                                    m["项目名称".decode("utf-8")],
                                    m["年化收益".decode("utf-8")],
                                    m["投资期限".decode("utf-8")],
                                    m["还款方式".decode("utf-8")],
                                    m["项目总额".decode("utf-8")],
                                    m["剩余金额".decode("utf-8")],
                                    m["起投金额".decode("utf-8")],
                                    m["转让价格".decode("utf-8")],
                                    m["债权价值".decode("utf-8")],
                                    m["转让人".decode("utf-8")],
                                    m["项目开始时间".decode("utf-8")],
                                    m["项目结束时间".decode("utf-8")],
                                    time.strftime("%Y-%m-%d %H:%M:%S")
                                    )
                        msg_list.append(msg_data)
                        insert_count += 1
                print("该批次插入了："+str(len(msg_list))+"条记录！\n")
                cursor.executemany(sql, msg_list)
                connection.commit()
        return insert_count
    except Exception as e:
        print("插入数据库失败，",e)
        return insert_count
    finally:
        connection.close()


def re_spider_wd_pages_into_db(url, url_type):
    """爬取每一页的数据（处理超时异常,默认10次重试）

    :param url: 请求的链接
    :param url_type: 请求的参数
    """
    # 插入的总的条数
    count = 0
    # 参数
    payload = {"planIds": "init",
               "pageNum": 1,
               "_": "1498196571937"
               }
    # 获取数据
    result = re_spider_wd(url, payload)
    if "zhu" == url_type or "zhuan" == url_type:
        pages = 9
    else:
        pages = result["data"]["total"]/10
    for p in range(1, pages+2):
        time.sleep(0.5)
        # 发送的参数
        payload = {"planIds": "init",
                   "pageNum": p,
                   "_": "1498196571937"
                   }
        print("第"+str(p)+"页的数据：")
        result = re_spider_wd(url, payload)
        result = parse_data(result, url_type)
        result = package_data(result)
        count += insert_db(result)
    print("总共插入："+str(count)+"条记录")


def start_spider():
    """
        开始爬虫
    """
    start_time = int(time.time())
    print("开始时间：" + str(time.strftime("%Y-%m-%d %H:%M:%S")))
    re_spider_wd_pages_into_db(detail_link_wei, "wei")
    re_spider_wd_pages_into_db(detail_link_zhu, "zhu")
    re_spider_wd_pages_into_db(detail_link_zhuan, "zhuan")
    print("结束时间：" + str(time.strftime("%Y-%m-%d %H:%M:%S")))
    end_time = int(time.time())
    print("总共用时：" + str(end_time - start_time) + "秒")


if __name__ == '__main__':
    for n in range(1, 2):
        start_spider()
