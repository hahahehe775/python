#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
      百度失信人黑名单的爬取
"""
from time import strftime,gmtime
import elasticsearch
import requests
import sys
import collections
import time
import json
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
# headers
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cookie': 'JSESSIONID=9CAA8C2BEE80C74B1952EFA9E69C4150; '
              'wafenterurl=L3NzZncvZnltaC8xNDUxL3p4Z2suaHRtP3N0PTAmcT0mc3hseD0xJmJ6e'
              'HJseD0xJmNvdXJ0X2lkPSZienhybWM9JnpqaG09JmFoPSZzdGFydENwcnE9JmVuZENwcnE9JnBhZ2U9Mw==; '
              '__utma=161156077.495504895.1501221471.1501221471.1501221471.1; '
              '__utmc=161156077; '
              '__utmz=161156077.1501221471.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); '
              'wafcookie=6638c7e043d4634e31fc03f98c44d6c6; '
              'wafverify=1ac90afbc1da7e6e86e4f07057416bcb; '
              'wzwsconfirm=7711ddd10a544f8efa642db4685e86e8; '
              'wzwstemplate=OA==; '
              'clientlanguage=zh_CN; '
              'JSESSIONID=0E40DC7D29A84A4528787317B590F218; '
              'ccpassport=601fd92b79652fe0489b52310512d73b; '
              'wzwschallenge=-1; '
              'wzwsvtime=1501226469',
    'Host': 'www.ahgyss.cn',
    'Proxy-Connection': 'keep-alive',
    'Referer': 'http://www.ahgyss.cn/ssfw/fymh/1451/zxgk.htm'
               '?st=0&q=&sxlx=&bzxrlx=&court_id=&bzxrmc=&zjhm=&ah=&startCprq=&endCprq=&page=11',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/58.0.3029.110 Safari/537.36'
}

# es链接地址
class ElasticSearchClient(object):
    @classmethod
    def get_es_servers(cls):
        hosts = [
            {"host": "172.16.39.55", "port": 9200},
            {"host": "172.16.39.56", "port": 9200},
            {"host": "172.16.39.57", "port": 9200}
        ]
        es = elasticsearch.Elasticsearch(
            hosts,
            sniff_on_start=True,
            sniff_on_connection_fail=True,
            sniffer_timeout=6000,
            http_auth=('elastic', 'cgtz@bigdata')
        )
        return es


def is_chinese(s):
    """
    判断是否有中文
    :return:
    """
    for ch in s.decode('utf-8'):
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


# es数据操作
class LoadElasticSearchTest(object):
    def __init__(self, index, doc_type):
        self.index = index
        self.doc_type = doc_type
        self.es_client = ElasticSearchClient.get_es_servers()

    # 如果返回结果>=1,这表明该黑名单已经存在了
    def search_data(self, id_card_no, name):
        return len(self.es_client.search(index="blacklist",
                                        body={"query": {"bool": {"filter": [{"term": {"ID_card_no": str(id_card_no)}},{ "term": { "name":  str(name) }}]}}})['hits']['hits'] )

    def add_date(self, id, row_obj):
        """
        单条插入ES
        """
        resu = self.es_client.index(index=self.index, doc_type=self.doc_type, id=id, body=row_obj)
        return resu.get('created', '')


# 数据解析
def parse_data(html):
    # 一页的数据
    data_list = []
    # 具体数据
    rest = html["data"]
    rest = rest[0]["result"]
    if len(rest) > 0:
        try:
            for rs in rest:
                try:
                    result = collections.OrderedDict()
                    result['name'] = rs.get('iname', '')
                    result['ID_card_no'] = rs.get('cardNum', '')
                    id_card_no_pre = result.get('ID_card_no', '')
                    # 获取身份证，如果有
                    if id_card_no_pre:
                        result['ID_card_no_pre'] = id_card_no_pre[0: 6]
                    result['from_platform'] = rs.get('courtName', '')
                    result['case_code'] = rs.get('caseCode', '')
                    result['filing_time'] = rs.get('publishDate', '')
                    result['notes'] = rs.get('disruptTypeName', '')
                    result['involved_amt'] = rs.get('duty', '')
                    result['gender'] = rs.get('sexy', '')
                    result['address'] = rs.get('areaName', '')
                    data_list.append(result)
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)
    return data_list


# 爬取数据
def spider_data(url):
    try:
        try:
            # 使用代理
            res = requests.get(url, timeout=10, proxies=proxies)
        except ProxyError:
            print("ProxyError Exception ,use no proxies ")
            # 不使用代理
            res = requests.get(url, timeout=10)
        res = res.content
        res = res[:-2]
        res = res[46:]
        return json.loads(res)
    except Exception as e:
        print("爬取失败", e)
        return -1


# 数据最终结果的封装
def package_data(result):
    # 结果数据的封装
    message = collections.OrderedDict()
    if len(result) == 0:
        message["statue_code"] = 0
        message["msg_size"] = 0
    else:
        message["statue_code"] = 1
        message["msg_size"] = len(result)
        message["msg"] = result
    return json.dumps(message).decode("unicode-escape")


# 数据的解析,写到elastic中
def parse_data_write_es(rest):
    users = rest["msg"]
    if len(users) > 0:
        load_es = LoadElasticSearchTest('blacklist', 'promise')
        insert_count = 0
        for user in users:
            try:
                id_card = user.get('ID_card_no', '')
                name = user.get('name', '')
                if id_card and name and len(id_card) >= 6 and (not is_chinese(id_card)):
                    from_platform = user.get('from_platform', '').strip()
                    name = user.get('name', '').strip()
                    ID_card_no = user.get('ID_card_no', '').strip()
                    ID_card_no_pre = user.get('ID_card_no_pre', '').strip()
                    phone_no = user.get('phone_no', '').strip()
                    qq = user.get('qq', '').strip()
                    gender = user.get('gender', '').strip()
                    address = user.get('address', '').strip()
                    involved_amt = user.get('involved_amt', '').strip()
                    filing_time = user.get('filing_time', '').strip()
                    case_code = user.get('case_code', '').strip()
                    notes = user.get('notes', '').strip()

                    id = str(id_card) + str(name)
                    action = '{"from_platform": \"'+from_platform+'\", ' \
                              '"name": \"'+name+'\", ' \
                              '"ID_card_no": \"'+ID_card_no+'\", ' \
                              '"ID_card_no_pre": \"'+ID_card_no_pre+'\", ' \
                              '"phone_no": \"'+phone_no+'\", ' \
                              '"qq": \"'+qq+'\", ' \
                              '"gender": \"'+gender+'\", ' \
                              '"address": \"'+address+'\", ' \
                              '"involved_amt": \"'+involved_amt+'\", ' \
                              '"filing_time": \"'+filing_time+'\", ' \
                              '"case_code": \"'+case_code+'\",' \
                              '"notes": \"'+notes+'\"}'

                    if load_es.add_date(id, action) == True:
                        insert_count += 1
            except Exception as e:
                print(e)
        print('该批次共插入 '+str(insert_count)+' 条数据')


# 爬取每页的具体数据（处理超时异常,默认10次重试）
def re_spider_page_data(url_list):
    count = 1
    for url in url_list:
        try:
            html = spider_data(url)
            # 如果没有获取到数据则重试多次
            if html == -1:
                # 如果没有爬取成功则，重爬
                for num in range(1, 10):
                    time.sleep(8)
                    print(num)
                    if html == -1:
                        html = spider_data(url)
                    else:
                        break
            # 解析数据
            result = parse_data(html)
            # 包装数据
            result = package_data(result)
            result = json.loads(result)
            print('第 ' + str(count) + ' 页爬取，共 '+str(len(result["msg"]))+' 条数据====>')
            parse_data_write_es(result)
            time.sleep(1)
            count += 1
        except Exception as e:
            print(e)


if __name__ == '__main__':
    # 常用字
    # first_name_list = [
    #         '明','国','华','建','文','平','志','伟','东','海','强','晓','生','光','林','小','民','永','杰','军',
    #         '波','成','荣','新','峰','刚','家','龙','德','庆','斌','辉','良','玉','俊','立','浩','天','宏','子',
    #         '金','健','一','忠','洪','江','福','祥','中','正','振','勇','耀','春','大','宁','亮','宇','兴','宝',
    #         '少','剑','云','学','仁','涛','瑞','飞','鹏','安','亚','泽','世','汉','达','卫','利','胜','敏','群',
    #         '松','克','清','长','嘉','红','山','贤','阳','乐','锋','智','青','跃','元','南','武','广','思','雄',
    #         '锦','威','启','昌','铭','维','义','宗','英','凯','鸿','森','超','坚','旭','政','传','康','继','翔',
    #         '远','力','进','泉','茂','毅','富','博','霖','顺','信','凡','豪','树','和','恩','向','道','川','彬',
    #         '柏','磊','敬','书','鸣','芳','培','全','炳','基','冠','晖','京','欣','廷','哲','保','秋','君','劲',
    #         '栋','仲','权','奇','礼','楠','炜','友','年','震','鑫','雷','兵','万','星','骏','伦','绍','麟','雨',
    #         '行','才','希','彦','兆','贵','源','有','景','升','惠','臣','慧','开','章','润','高','佳','虎','根'
    # ]
    print('-----------------------start:' + str(strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + '-----------------------')
    # first_name_list = [
    #     '世','舜','丞','主','产','仁','仇','仓','仕','仞','任','伋','众','伸','佐','佺','侃','侪','促',
    #     '俟','信','俣','修','倝','倡','倧','偿','储','僖','僧','僳','儒','俊','伟','列','则','刚','创',
    #     '前','剑','助','劭','势','勘','参','叔','吏','嗣','士','壮','孺','守','宽','宾','宋','宗','宙',
    #     '宣','实','宰','尊','峙','峻','崇','崈','川','州','巡','帅','庚','战','才','承','拯','操','斋',
    #     '昌','晁','暠','曹','曾','珺','玮','珹','琒','琛','琩','琮','琸','瑎','玚','璟','璥','瑜','生',
    #     '畴','矗','矢','石','磊','砂','碫','示','社','祖','祚','祥','禅','稹','穆','竣','竦','综','缜',
    #     '绪','舱','舷','船','蚩','襦','轼','辑','轩','子','杰','榜','碧','葆','莱','蒲','天','乐','东',
    #     '钢','铎','铖','铠','铸','铿','锋','镇','键','镰','馗','旭','骏','骢','骥','驹','驾','骄','诚',
    #     '诤','赐','慕','端','征','坚','建','弓','强','彦','御','悍','擎','攀','旷','昂','晷','健','冀',
    #     '凯','劻','啸','柴','木','林','森','朴','骞','寒','函','高','魁','魏','鲛','鲲','鹰','丕','乒',
    #     '候','冕','勰','备','宪','宾','密','封','山','峰','弼','彪','彭','旁','日','明','昪','昴','胜',
    #     '汉','涵','汗','浩','涛','淏','清','澜','浦','澉','澎','澔','濮','濯','瀚','瀛','灏','沧','虚',
    #     '豪','豹','辅','辈','迈','邶','合','部','阔','雄','霆','震','韩','俯','颁','颇','频','颔','风',
    #     '飒','飙','飚','马','亮','仑','仝','代','儋','利','力','劼','勒','卓','哲','喆','展','帝','弛',
    #     '弢','弩','彰','征','律','德','志','忠','思','振','挺','掣','旲','旻','昊','昮','晋','晟','晸',
    #     '朕','朗','段','殿','泰','滕','炅','炜','煜','煊','炎','选','玄','勇','君','稼','黎','利','贤',
    #     '谊','金','鑫','辉','墨','欧','有','友','闻','问','秀','娟','英','华','慧','巧','美','娜','静',
    #     '淑','惠','珠','翠','雅','芝','玉','萍','红','娥','玲','芬','芳','燕','彩','春','菊','兰','凤',
    #     '爱','妹','霞','香','月','莺','媛','艳','瑞','凡','佳','嘉','琼','勤','珍','贞','莉','桂','娣',
    #     '叶','璧','璐','娅','琦','晶','妍','茜','秋','珊','莎','锦','黛','青','倩','婷','姣','婉','娴',
    #     '瑾','颖','露','瑶','怡','婵','雁','蓓','纨','仪','荷','丹','蓉','眉','君','琴','蕊','薇','菁',
    #     '梦','岚','苑','婕','馨','瑗','琰','韵','融','园','艺','咏','卿','聪','澜','纯','毓','悦','昭',
    #     '冰','爽','琬','茗','羽','希','宁','欣','飘','育','滢','馥','筠','柔','竹','霭','凝','晓','欢',
    #     '霄','枫','芸','菲','寒','伊','亚','宜','可','姬','舒','影','荔','枝','思','丽''洁','梅','琳',
    #     '素','云','莲','真','环','雪','荣',
    # ]
    # first_name_list = [
    #     '乙', '丁', '厂', '卜', '人', '入', '几', '儿', '力', '刀', '又', '干', '工', '土', '才', '大', '小', '口', '巾', '山', '个', '勺',
    #     '凡', '川', '夕', '幺',
    #     '广', '门', '尸', '弓', '己', '已', '子', '也', '女', '王', '井', '元', '云', '木', '不', '歹', '夭', '犬', '车', '牙', '屯', '互',
    #     '瓦', '止', '日', '贝',
    #     '水', '午', '牛', '手', '毛', '气', '长', '斤', '爪', '月', '乌', '文', '方', '火', '斗', '户', '心', '巴', '玉', '示', '术', '丙',
    #     '石', '且', '目', '甲',
    #     '申', '电', '田', '生', '禾', '丘', '瓜', '用', '册', '鸟', '主', '立', '宁', '穴', '它', '必', '永', '皮', '矛', '母', '考', '老',
    #     '耳', '亚', '臣', '西',
    #     '而', '虫', '曲', '因', '回', '肉', '网', '舌', '竹', '自', '向', '行', '舟', '兆', '伞', '朵', '交', '衣', '羊', '米', '州', '羽',
    #     '走', '克', '求', '豆',
    #     '丽', '辰', '来', '县', '足', '串', '员', '我', '秀', '身', '龟', '兔', '角', '卵', '辛', '弟', '良', '其', '若', '雨', '虎', '果',
    #     '易', '垂', '舍', '鱼',
    #     '兔', '京', '单', '某', '南', '面', '冒', '胃', '革', '带', '皇', '泉', '鬼', '盾', '须', '食', '亭', '亮', '帝', '首', '眉', '壶',
    #     '栗', '夏', '脊', '桑',
    #     '能', '黄', '戚', '爽', '象', '麻', '康', '鹿', '望', '率', '商', '琴', '尊', '鼠', '燕', '巨', '民', '麦', '录', '隶', '衰', '高',
    #     '兽', '禽', '匕', '戈',
    #     '凸', '皿', '凹', '矢', '吕', '臼', '囱', '帚', '函', '韭', '巢', '壹', '粟', '凿', '鼎', '蜀', '穆', '爵', '罕', '巫', '马', '仓',
    #     '龙', '业', '乐', '齐',
    #     '监', '一', '二', '十', '七', '八', '九', '三', '士', '寸', '下', '上', '刃', '叉', '夫', '天', '五', '尤', '中', '介', '凶', '丹',
    #     '六', '引', '丑', '尺',
    #     '孔', '末', '未', '甘', '本', '只', '四', '斥', '白', '乎', '朱', '血', '杀', '亦', '束', '金', '要', '系', '音', '卒', '彭', '及',
    #     '亡', '之', '开', '支',
    #     '友', '比', '见', '仁', '化', '反', '父', '从', '分', '公', '欠', '匀', '为', '队', '予', '双', '幻', '正', '去', '世', '古', '左',
    #     '右', '灭', '卡', '北',
    #     '占', '旦', '叶', '史', '兄', '付', '令', '丛', '印', '包', '饥', '闪', '半', '讨', '丝', '出', '孕', '圣', '巩', '扩', '共', '协',
    #     '百', '页', '匠', '夸',
    #     '灰', '列', '死', '夹', '划', '至', '此', '贞', '尘', '尖', '劣', '光', '则', '先', '丢', '休', '伏', '伐', '后', '全', '企', '众',
    #     '负', '各', '名', '多',
    #     '争', '次', '闭', '闯', '并', '守', '字', '安', '军', '寻', '孙', '阵', '阳', '阴', '好', '弄', '戒', '吞', '坏', '找', '赤', '折',
    #     '两', '医', '连', '步',
    #     '时', '吴', '里', '呆', '男', '困', '吹', '别', '告', '秃', '利', '兵', '体', '位', '希', '坐', '妥', '饮', '床', '库', '弃', '闲',
    #     '间', '灶', '没', '宋',
    #     '牢', '灾', '启', '初', '社', '君', '灵', '即', '尿', '尾', '局', '奉', '武', '规', '幸', '取', '苗', '直', '林', '析', '或', '卧',
    #     '事', '枣', '奔', '奇',
    #     '妻', '轰', '顷', '斩', '肯', '具', '昌', '昆', '明', '典', '鸣', '岩', '败', '牧', '乖', '凭', '制', '采', '受', '命', '乳', '朋',
    #     '昏', '育', '炎', '泪',
    #     '宝', '宗', '帘', '承', '降', '封', '歪', '研', '耍', '茧', '茶', '相', '查', '咸', '厚', '牵', '皆', '省', '是', '畏', '品', '咱',
    #     '骨', '拜', '看', '罚',
    #     '卸', '香', '秋', '科', '重', '复', '段', '便', '俩', '保', '信', '追', '美', '前', '染', '突', '穿', '冠', '扁', '既', '屋', '昼',
    #     '盈', '绝', '脉', '狱',
    #     '艳', '素', '蚕', '盐', '埋', '莫', '获', '真', '索', '哥', '辱', '套', '逐', '原', '哭', '罢', '乘', '称', '笔', '臭', '射', '拿',
    #     '旅', '料', '益', '兼',
    #     '烦', '涉', '家', '容', '宰', '读', '扇', '雀', '甜', '衔', '悉', '盗', '章', '族', '旋', '寇', '宿', '逮', '绵', '葬', '朝', '森',
    #     '棉', '雁', '晶', '答',
    #     '筋', '集', '焦', '奥', '番', '等', '寒', '窗', '粥', '隙', '登', '解', '舞', '鲜', '暴', '墨', '丈', '内', '尼', '加', '吉', '的',
    #     '官', '炊', '肩', '建',
    #     '居', '奏', '黑', '辞', '塞', '夯', '囚', '吏', '夷', '旭', '驮', '邑', '闰', '秉', '岳', '娄', '虐', '聂', '莽', '殷', '舀', '卿',
    #     '彪', '逸', '祭', '尉',
    #     '棘', '掰', '黍', '粤', '奠', '聘', '频', '赫', '兢', '寡', '霍', '嚣', '羹', '矗', '昔', '卑', '幽', '羔', '涩', '祟', '丈', '内',
    #     '尼', '加', '吉', '的',
    #     '官', '炊', '肩', '建', '居', '奏', '黑', '辞', '塞', '麦', '隶', '谷', '岔', '委', '威', '宦', '亿', '艺', '扎', '厅', '切', '什',
    #     '仆', '仇', '仍', '仅',
    #     '忆', '订', '计', '认', '刊', '巧', '扑', '扒', '功', '扔', '节', '可', '布', '轧', '叮', '号', '叼', '叫', '叨', '仗', '仙', '们',
    #     '仪', '仔', '他', '句',
    #     '犯', '冬', '汁', '让', '礼', '训', '刑', '议', '讯', '记', '辽', '奶', '奴', '召', '台', '纠', '幼', '扛', '寺', '扣', '托', '圾',
    #     '地', '扬', '场', '芒',
    #     '芝', '朽', '朴', '机', '在', '有', '达', '成', '邪', '吐', '吓', '吃', '吸', '吗', '屿', '帆', '刚', '年', '迁', '伟', '传', '伍',
    #     '优', '延', '任', '伤',
    #     '池', '汤', '忙', '宇', '宅', '讲', '许', '论', '讽', '设', '访', '那', '迅', '收', '阶', '防', '奸', '如', '她', '妈', '红', '纤',
    #     '级', '约', '纪', '驰',
    #     '巡', '形', '进', '远', '违', '运', '扶', '抚', '技', '扰', '拒', '批', '扯', '址', '抄', '坝', '贡', '攻', '抓', '扮', '抢', '孝',
    #     '均', '抛', '投', '坟',
    #     '抗', '坑', '坊', '抖', '护', '志', '扭', '块', '把', '报', '却', '劫', '芽', '花', '芹', '芬', '苍', '芳', '芦', '劳', '杆', '杠',
    #     '杜', '材', '村', '杏',
    #     '极', '李', '杨', '更', '励', '否', '歼', '坚', '旱', '盯', '呈', '助', '园', '旷', '围', '呀', '吨', '邮', '吵', '听', '吩', '呜',
    #     '吧', '吼', '岗', '帐',
    #     '财', '针', '钉', '私', '估', '何', '但', '伸', '作', '伯', '伶', '佣', '低', '你', '住', '伴', '佛', '近', '彻', '役', '返', '余',
    #     '谷', '含', '邻', '岔',
    #     '肝', '肚', '肠', '狂', '犹', '删', '岛', '迎', '饭', '言', '冻', '状', '况', '疗', '冷', '序', '冶', '忘', '闷', '判', '灿', '汪',
    #     '沙', '汽', '沃', '泛',
    #     '沟', '沉', '沉', '忧', '快', '完', '宏', '究', '良', '证', '评', '补', '识', '诉', '诊', '词', '译', '迟', '改', '张', '忌', '阿',
    #     '阻', '附', '妙', '妖',
    #     '妨', '努', '忍', '劲', '驱', '纯', '纱', '纳', '纲', '驳', '纵', '纷', '纸', '纹', '纺', '驴', '纽', '玩', '环', '青', '责', '现',
    #     '表', '抹', '拢', '拔',
    #     '拣', '担', '坦', '押', '抽', '拐', '拍', '者', '顶', '拆', '拥', '抵', '拘', '势', '抱', '垃', '拉', '拦', '拌', '招', '坡', '披',
    #     '拨', '择', '抬', '苦',
    #     '茂', '苹', '英', '范', '茄', '茎', '茅', '枝', '杯', '柜', '板', '松', '枪', '构', '述', '枕', '丧', '刺', '矿', '码', '厕', '态',
    #     '欧', '垄', '转', '轮',
    #     '软', '到', '叔', '齿', '些', '虏', '肾', '贤', '尚', '旺', '味', '畅', '昂', '固', '忠', '咐', '呼', '咏', '呢', '岸', '帖', '帜',
    #     '岭', '贩', '购', '钓',
    #     '知', '物', '刮', '秆', '和', '季', '委', '佳', '侍', '供', '使', '例', '版', '侄', '侦', '侧', '侨', '佩', '货', '依', '迫', '质',
    #     '欣', '征', '往', '爬',
    #     '彼', '径', '所', '斧', '爸', '贪', '念', '贫', '肤', '肺', '肢', '肿', '胀', '股', '肥', '服', '胁', '狐', '忽', '狗', '饰', '饱',
    #     '饲', '店', '夜', '府',
    #     '底', '剂', '郊', '废', '净', '盲', '放', '刻', '闸', '闹', '券', '卷', '炒', '炕', '炉', '沫', '浅', '泄', '河', '沾', '油', '泊',
    #     '沿', '泡', '注', '泻',
    #     '泳', '泥', '沸', '波', '泼', '泽', '治', '怖', '性', '怕', '怜', '怪', '定', '宜', '审', '宙', '空', '试', '郎', '诗', '房', '诚',
    #     '衬', '衫', '视', '话',
    #     '诞', '询', '该', '详', '届', '刷', '屈', '弦', '孟', '孤', '陕', '限', '妹', '姑', '姐', '姓', '始', '驾', '线', '练', '组', '细',
    #     '驶', '织', '终', '驻',
    #     '驼', '绍', '经', '贯', '帮', '珍', '玻', '型', '挂', '持', '项', '垮', '挎', '城', '挠', '政', '赴', '挡', '挺', '括', '拴', '拾',
    #     '洮', '指', '垫', '挣',
    #     '挤', '拼', '挖', '按', '挥', '挪', '春', '草', '荒', '茫', '荡', '荣', '故', '胡', '药', '枯', '柄', '栋', '柏', '柳', '柱', '柿',
    #     '栏', '残', '殃', '轻',
    #     '鸦', '背', '战', '削', '盼', '眨', '哄', '威', '砖', '厘', '砌', '砍', '耐', '览', '哑', '映', '星', '昨', '趴', '贵', '界', '虹',
    #     '虾', '蚁', '思', '蚂',
    #     '咽', '骂', '哗', '响', '哈', '咬', '咳', '哪', '炭', '峡', '贱', '贴', '钟', '钢', '钥', '钩', '缸', '矩', '怎', '牲', '选', '适',
    #     '秒', '种', '竿', '贷',
    #     '顺', '修', '促', '侮', '俭', '俗', '俘', '侵', '俊', '待', '律', '很', '叙', '剑', '逃', '盆', '胆', '胜', '胞', '胖', '勉', '狭',
    #     '狮', '狡', '狠', '贸',
    #                    '价', '份', '仰', '仿', '伙', '伪', '似', '爷', '创', '肌', '旬', '旨', '壮', '冲', '冰', '决', '妄', '问', '灯',
    #     '汗', '污', '江',
    # ]
    first_name_list = [
        '戋', '圢', '氕', '伋', '仝', '氿', '汈', '氾', '忉', '宄', '訏', '讱', '玐', '㺩', '扞', '圲', '圫', '芏', '芃', '朳', '朸', '𠱃',
        '邨', '吒', '吖', '屼', '屾', '辿', '钆', '仳', '㲻', '伣', '伈', '癿', '甪', '邠', '犴', '冱', '㡯', '邡', '闫', '闬', '澫', '汋',
        '䜣', '讻', '詝', '孖', '㚤', '紃', '纩', '玗', '玒', '玔', '玓', '玘',
        '制', '知', '迭', '氛', '垂', '牧', '物', '乖', '刮', '秆', '和', '季', '委', '秉', '佳', '侍', '岳', '供', '使', '例', '侠', '侥',
        '版', '侄', '侦', '侣', '侧', '凭', '侨', '佩', '货', '侈', '依', '卑', '的', '迫', '质', '欣', '征', '往', '爬', '彼', '径', '所',
        '舍', '金', '刹', '命', '肴', '斧', '爸', '采', '觅', '受', '乳', '贪',
        '念', '贫', '忿', '肤', '肺', '肢', '肿', '胀', '朋', '股', '肮', '肪', '肥', '服', '胁', '周', '昏', '鱼', '兔', '狐', '忽', '狗',
        '狞', '备', '饰', '饱', '饲', '变', '京', '享', '庞', '店', '夜', '庙', '府', '底', '疟', '疙', '疚', '剂', '卒', '郊', '庚', '废',
        '净', '盲', '放', '刻', '育', '氓', '闸', '闹', '郑', '券', '卷', '单',
        '炬', '炒', '炊', '炕', '炎', '炉', '沫', '浅', '法', '泄', '沽', '河', '沾', '泪', '沮', '油', '泊', '沿', '泡', '注', '泣', '泞',
        '泻', '泌', '泳', '泥', '沸', '沼', '波', '泼', '泽', '治', '怔', '怯', '怖', '性', '怕', '怜', '怪', '怡', '学', '宝', '宗', '定',
        '宠', '宜', '审', '宙', '官', '空', '帘', '宛', '实', '试', '郎', '诗',
        '肩', '房', '诚', '衬', '衫', '视', '祈', '话', '诞', '诡', '询', '该', '详', '建', '肃', '录', '隶', '帚', '屉', '居', '届', '刷',
        '屈', '弧', '弥', '弦', '承', '孟', '陋', '陌', '孤', '陕', '降', '函', '限', '妹', '姑', '姐', '姓', '妮', '始', '姆', '迢', '驾',
        '叁', '参', '艰', '线', '练', '组', '绅', '细', '驶', '织', '驹', '终',
        '驻', '绊', '驼', '绍', '绎', '经', '贯', '契', '贰', '奏', '春', '帮', '玷', '珍', '玲', '珊', '玻', '毒', '型', '拭', '挂', '封',
        '持', '拷', '拱', '项', '垮', '挎', '城', '挟', '挠', '政', '赴', '赵', '挡', '拽', '哉', '挺', '括', '垢', '拴', '拾', '挑', '垛',
        '指', '垫', '挣', '挤', '拼', '挖', '按', '挥', '挪', '拯', '某', '甚',
        '荆', '茸', '革', '茬', '荐', '巷', '带', '草', '茧', '茵', '茶', '荒', '茫', '荡', '荣', '荤', '荧', '故', '胡', '荫', '荔', '南',
        '药', '标', '栈', '柑', '枯', '柄', '栋', '相', '查', '柏', '栅', '柳', '柱', '柿', '栏', '柠', '树', '勃', '要', '柬', '咸', '威',
        '歪', '研', '砖', '厘', '厚', '砌', '砂', '泵', '砚', '砍', '面', '耐',
        '耍', '牵', '鸥', '残', '殃', '轴', '轻', '鸦', '皆', '韭', '背', '战', '点', '虐', '临', '览', '竖', '省', '削', '尝', '昧', '盹',
        '是', '盼', '眨', '哇', '哄', '哑', '显', '冒', '映', '星', '昨', '咧', '昭', '畏', '趴', '胃', '贵', '界', '虹', '虾', '蚁', '思',
        '蚂', '虽', '品', '咽', '骂', '勋', '哗', '咱', '响', '哈', '哆', '咬',
        '咳', '咪', '哪', '哟', '炭', '峡', '罚', '贱', '贴', '贻', '骨', '幽', '钙', '钝', '钞', '钟', '钢', '钠', '钥', '钦', '钧', '钩',
        '钮', '卸', '缸', '拜', '看', '矩', '毡', '氢', '怎', '牲', '选', '适', '秒', '香', '种', '秋', '科', '重', '复', '竿', '段', '便',
        '俩', '贷', '顺', '修', '俏', '保', '促', '俄', '俐', '侮', '俭', '俗',
        '俘', '信', '皇', '泉', '鬼', '侵', '禹', '侯', '追', '俊', '盾', '待', '徊', '衍', '律', '很', '须', '叙', '剑', '逃', '食', '盆',
        '胚', '胧', '胆', '胜', '胞', '胖', '脉', '胎', '勉', '狭', '狮', '独', '狰', '狡', '狱', '狠', '贸', '怨', '急', '饵', '饶', '蚀',
        '饺', '饼', '峦', '弯', '将', '奖', '哀', '亭', '亮', '度', '迹', '庭',
        '疮', '疯', '疫', '疤', '咨', '姿', '亲', '音', '帝', '施', '闺', '闻', '闽', '阀', '阁', '差', '养', '美', '姜', '叛', '送', '类',
        '迷', '籽', '娄', '前', '首', '逆', '兹', '总', '炼', '炸', '烁', '炮', '炫', '烂', '剃', '洼', '洁', '洪', '洒', '柒', '浇', '浊',
        '洞', '测', '洗', '活', '派', '洽', '染', '洛', '浏', '济', '洋', '洲',
        '浑', '浓', '津', '恃', '恒', '恢', '恍', '恬', '恤', '恰', '恼', '恨', '举', '觉', '宣', '宦', '室', '宫', '宪', '突', '穿', '窃',
        '客', '诫', '冠', '诬', '语', '扁', '袄', '祖', '神', '祝', '祠', '误', '诱', '诲', '说', '诵', '垦', '退', '既', '屋', '昼', '屏',
        '屎', '费', '陡', '逊', '眉', '孩', '陨', '除', '险', '院', '娃', '姥',
        '姨', '姻', '娇', '姚', '娜', '怒', '架', '贺', '盈', '勇', '怠', '癸', '蚤', '柔', '垒', '绑', '绒', '结', '绕', '骄', '绘', '给',
        '绚', '骆', '络', '绝', '绞', '骇', '统', '耕', '耘', '耗', '耙', '艳', '泰', '秦', '珠', '班', '素', '匿', '蚕', '顽', '盏', '匪',
        '捞', '栽', '捕', '埂', '捂', '振', '载', '赶', '起', '盐', '捎', '捍',
        '捏', '埋', '捉', '捆', '捐', '损', '袁', '捌', '都', '哲', '逝', '捡', '挫', '换', '挽', '挚', '热', '恐', '捣', '壶', '捅', '埃',
        '挨', '耻', '耿', '耽', '聂', '恭', '莽', '莱', '莲', '莫', '莉', '荷', '获', '晋', '恶', '莹', '莺', '真', '框', '梆', '桂', '桔',
        '栖', '档', '桐', '株', '桥', '桦', '栓', '桃', '格', '桩', '校', '核',
        '样', '根', '索', '哥', '速', '逗', '栗', '贾', '酌', '配', '翅', '辱', '唇', '夏', '砸', '砰', '砾', '础', '破', '原', '套', '逐',
        '烈', '殊', '殉', '顾', '轿', '较', '顿', '毙', '致', '柴', '桌', '虑', '监', '紧', '党', '逞', '晒', '眠', '晓', '哮', '唠', '鸭',
        '晃', '哺', '晌', '剔', '晕', '蚌', '畔', '蚣', '蚊', '蚪', '蚓', '哨',
        '哩', '圃', '哭', '哦', '恩', '鸯', '唤', '唁', '哼', '唧', '啊', '唉', '唆', '罢', '峭', '峨', '峰', '圆', '峻', '贼', '贿', '赂',
        '赃', '钱', '钳', '钻', '钾', '铁', '铃', '铅', '缺', '氧', '氨', '特', '牺', '造', '乘', '敌', '秤', '租', '积', '秧', '秩', '称',
        '秘', '透', '笔', '笑', '笋', '债', '借', '值', '倚', '俺', '倾', '倒',
        '倘', '俱', '倡', '候', '赁', '俯', '倍', '倦', '健', '臭', '射', '躬', '息', '倔', '徒', '徐', '殷', '舰', '舱', '般', '航', '途',
        '拿', '耸', '爹', '舀', '爱', '豺', '豹', '颁', '颂', '翁', '胰', '脆', '脂', '胸', '胳', '脏', '脐', '胶', '脑', '脓', '逛', '狸',
        '狼', '卿', '逢', '鸵', '留', '鸳', '皱', '饿', '馁', '凌', '凄', '恋',
        '桨', '浆', '衰', '衷', '高', '郭', '席', '准', '座', '症', '病', '疾', '斋', '疹', '疼', '疲', '脊', '效', '离', '紊', '唐', '瓷',
        '资', '凉', '站', '剖', '竞', '部', '旁', '旅', '畜', '阅', '羞', '羔', '瓶', '拳', '粉', '料', '益', '兼', '烤', '烘', '烦', '烧',
        '烛', '烟', '烙', '递', '涛', '浙', '涝', '浦', '酒', '涉', '消', '涡',
        '浩', '海', '涂', '浴', '浮', '涣', '涤', '流', '润', '涧', '涕', '浪', '浸', '涨', '烫', '涩', '涌', '悖', '悟', '悄', '悍', '悔',
        '悯', '悦', '害', '宽', '家', '宵', '宴', '宾', '窍', '窄', '容', '宰', '案', '请', '朗', '诸', '诺', '读', '扇', '诽', '袜', '袖',
        '袍', '被', '祥', '课', '冥', '谁', '调', '冤', '谅', '谆', '谈', '谊',
        '剥', '恳', '展', '剧', '屑', '弱', '陵', '祟', '陶', '陷', '陪', '娱', '娟', '恕', '娥', '娘', '通', '能', '难', '预', '桑', '绢',
        '绣', '验', '继', '骏', '球', '琐', '理', '琉', '琅', '捧', '堵', '措', '描', '域', '捺', '掩', '捷', '排', '焉', '掉', '捶', '赦',
        '堆', '推', '埠', '掀', '授', '捻', '教', '掏', '掐', '掠', '掂', '培',
        '接', '掷', '控', '探', '据', '掘', '掺', '职', '基', '聆', '勘', '聊', '娶', '著', '菱', '勒', '黄', '菲', '萌', '萝', '菌', '萎',
        '菜', '萄', '菊', '菩', '萍', '菠', '萤', '营', '乾', '萧', '萨', '菇', '械', '彬', '梦', '婪', '梗', '梧', '梢', '梅', '检', '梳',
        '梯', '桶', '梭', '救', '曹', '副', '票', '酝', '酗', '厢', '戚', '硅',
        '硕', '奢', '盔', '爽', '聋', '袭', '盛', '匾', '雪', '辅', '辆', '颅', '虚', '彪', '雀', '堂', '常', '眶', '匙', '晨', '睁', '眯',
        '眼', '悬', '野', '啪', '啦', '曼', '晦', '晚', '啄', '啡', '距', '趾', '啃', '跃', '略', '蚯', '蛀', '蛇', '唬', '累', '鄂', '唱',
        '患', '啰', '唾', '唯', '啤', '啥', '啸', '崖', '崎', '崭', '逻', '崔',
        '帷', '崩', '崇', '崛', '婴', '圈', '铐', '铛', '铝', '铜', '铭', '铲', '银', '矫', '甜', '秸', '梨', '犁', '秽', '移', '笨', '笼',
        '笛', '笙', '符', '第', '敏', '做', '袋', '悠', '偿', '偶', '偎', '偷', '您', '售', '停', '偏', '躯', '兜', '假', '衅', '徘', '徙',
        '得', '衔', '盘', '舶', '船', '舵', '斜', '盒', '鸽', '敛', '悉', '欲',
        '彩', '领', '脚', '脖', '脯', '豚', '脸', '脱', '象', '够', '逸', '猜', '猪', '猎', '猫', '凰', '猖', '猛', '祭', '馅', '馆', '凑',
        '减', '毫', '烹', '庶', '麻', '庵', '痊', '痒', '痕', '廊', '康', '庸', '鹿', '盗', '章', '竟', '商', '族', '旋', '望', '率', '阎',
        '阐', '着', '羚', '盖', '眷', '粘', '粗', '粒', '断', '剪', '兽', '焊',
        '焕', '清', '添', '鸿', '淋', '涯', '淹', '渠', '渐', '淑', '淌', '混', '淮', '淆', '渊', '淫', '渔', '淘', '淳', '液', '淤', '淡',
        '淀', '深', '涮', '涵', '婆', '梁', '渗', '情', '惜', '惭', '悼', '惧', '惕', '惟', '惊', '惦', '悴', '惋', '惨', '惯', '寇', '寅',
        '寄', '寂', '宿', '窒', '窑', '密', '谋', '谍', '谎', '谐', '袱', '祷',
        '祸', '谓', '谚', '谜', '逮', '敢', '尉', '屠', '弹', '隋', '堕', '随', '蛋', '隅', '隆', '隐', '婚', '婶', '婉', '颇', '颈', '绩',
        '绪', '续', '骑', '绰', '绳', '维', '绵', '绷', '绸', '综', '绽', '绿', '缀', '巢', '琴', '琳', '琢', '琼', '斑', '替', '揍', '款',
        '堪', '塔', '搭', '堰', '揩', '越', '趁', '趋', '超', '揽', '堤', '提',
        '博', '揭', '喜', '彭', '揣', '插', '揪', '搜', '煮', '援', '搀', '裁', '搁', '搓', '搂', '搅', '壹', '握', '搔', '揉', '斯', '期',
        '欺', '联', '葫', '散', '惹', '葬', '募', '葛', '董', '葡', '敬', '葱', '蒋', '蒂', '落', '韩', '朝', '辜', '葵', '棒', '棱', '棋',
        '椰', '植', '森', '焚', '椅', '椒', '棵', '棍', '椎', '棉', '棚', '棕',
        '棺', '榔', '椭', '惠', '惑', '逼', '粟', '棘', '酣', '酥', '厨', '厦', '硬', '硝', '确', '硫', '雁', '殖', '裂', '雄', '颊', '雳',
        '暂', '雅', '翘', '辈', '悲', '紫', '凿', '辉', '敞', '棠', '赏', '掌', '晴', '睐', '暑', '最', '晰', '量', '鼎', '喷', '喳', '晶',
        '喇', '遇', '喊', '遏', '晾', '景', '畴', '践', '跋', '跌', '跑', '跛',
        '遗', '蛙', '蛛', '蜓', '蜒', '蛤', '喝', '鹃', '喂', '喘', '喉', '喻', '啼', '喧', '嵌', '幅', '帽', '赋', '赌', '赎', '赐', '赔',
        '黑', '铸', '铺', '链', '销', '锁', '锄', '锅', '锈', '锋', '锌', '锐', '甥', '掰', '短', '智', '氮', '毯', '氯', '鹅', '剩', '稍',
        '程', '稀', '税', '筐', '等', '筑', '策', '筛', '筒', '筏', '答', '筋',
        '筝', '傲', '傅', '牌', '堡', '集', '焦', '傍', '储', '皓', '皖', '粤', '奥', '街', '惩', '御', '循', '艇', '舒', '逾', '番', '释',
        '禽', '腊', '脾', '腋', '腔', '腕', '鲁', '猩', '猬', '猾', '猴', '惫', '然', '馈', '馋', '装', '蛮', '就', '敦', '斌', '痘', '痢',
        '痪', '痛', '童', '竣', '阔', '善', '翔', '羡', '普', '粪', '尊', '奠',
        '道', '遂', '曾', '焰', '港', '滞', '湖', '湘', '渣', '渤', '渺', '湿', '温', '渴', '溃', '溅', '滑', '湃', '渝', '湾', '渡', '游',
        '滋', '渲', '溉', '愤', '慌', '惰', '愕', '愣', '惶', '愧', '愉', '慨', '割', '寒', '富', '寓', '窜', '窝', '窖', '窗', '窘', '遍',
        '雇', '裕', '裤', '裙', '禅', '禄', '谢', '谣', '谤', '谦', '犀', '属',
        '屡', '强', '粥', '疏', '隔', '隙', '隘', '媒', '絮', '嫂', '媚', '婿', '登', '缅', '缆', '缉', '缎', '缓', '缔', '缕', '骗', '编',
        '骚', '缘', '瑟', '鹉', '瑞', '瑰', '瑙', '魂', '肆', '摄', '摸', '填', '搏', '塌', '鼓', '摆', '携', '搬', '摇', '搞', '塘', '摊',
        '聘', '斟', '蒜', '勤', '靴', '靶', '鹊', '蓝', '墓', '幕', '蓬', '蓄',
        '蒲', '蓉', '蒙', '蒸', '献', '椿', '禁', '楚', '楷', '榄', '想', '槐', '榆', '楼', '概', '赖', '酪', '酬', '感', '碍', '碘', '碑',
        '碎', '碰', '碗', '碌', '尴', '雷', '零', '雾', '雹', '辐', '辑', '输', '督', '频', '龄', '鉴', '睛', '睹', '睦', '瞄', '睫', '睡',
        '睬', '嗜', '鄙', '嗦', '愚', '暖', '盟', '歇', '暗', '暇', '照', '畸',
        '跨', '跷', '跳', '跺', '跪', '路', '跤', '跟', '遣', '蜈', '蜗', '蛾', '蜂', '蜕', '嗅', '嗡', '嗓', '署', '置', '罪', '罩', '蜀',
        '幌', '错', '锚', '锡', '锣', '锤', '锥', '锦', '键', '锯', '锰', '矮', '辞', '稚', '稠', '颓', '愁', '筹', '签', '简', '筷', '毁',
        '舅', '鼠', '催', '傻', '像', '躲', '魁', '衙', '微', '愈', '遥', '腻',
        '腰', '腥', '腮', '腹', '腺', '鹏', '腾', '腿', '鲍', '猿', '颖', '触', '解', '煞', '雏', '馍', '馏', '酱', '禀', '痹', '廓', '痴',
        '痰', '廉', '靖', '新', '韵', '意', '誊', '粮', '数', '煎', '塑', '慈', '煤', '煌', '满', '漠', '滇', '源', '滤', '滥', '滔', '溪',
        '溜', '漓', '滚', '溢', '溯', '滨', '溶', '溺', '粱', '滩', '慎', '誉',
        '塞', '寞', '窥', '窟', '寝', '谨', '褂', '裸', '福', '谬', '群', '殿', '辟', '障', '媳', '嫉', '嫌', '嫁', '叠', '缚', '缝', '缠',
        '缤', '剿', '静', '碧', '璃', '赘', '熬', '墙', '墟', '嘉', '摧', '赫', '截', '誓', '境', '摘', '摔', '撇', '聚', '慕', '暮', '摹',
        '蔓', '蔑', '蔡', '蔗', '蔽', '蔼', '熙', '蔚', '兢', '模', '槛', '榴',
        '榜', '榨', '榕', '歌', '遭', '酵', '酷', '酿', '酸', '碟', '碱', '碳', '磁', '愿', '需', '辖', '辗', '雌', '裳', '颗', '瞅', '墅',
        '嗽', '踊', '蜻', '蜡', '蝇', '蜘', '蝉', '嘛', '嘀', '赚', '锹', '锻', '镀', '舞', '舔', '稳', '熏', '箕', '算', '箩', '管', '箫',
        '舆', '僚', '僧', '鼻', '魄', '魅', '貌', '膜', '膊', '膀', '鲜', '疑',
        '孵', '馒', '裹', '敲', '豪', '膏', '遮', '腐', '瘩', '瘟', '瘦', '辣', '彰', '竭', '端', '旗', '精', '粹', '歉', '弊', '熄', '熔',
        '煽', '潇', '漆', '漱', '漂', '漫', '滴', '漾', '演', '漏', '慢', '慷', '寨', '赛', '寡', '察', '蜜', '寥', '谭', '肇', '褐', '褪',
        '谱', '隧', '嫩', '翠', '熊', '凳', '骡', '缩', '慧', '撵', '撕', '撒',
        '撩', '趣', '趟', '撑', '撮', '撬', '播', '擒', '墩', '撞', '撤', '增', '撰', '聪', '鞋', '鞍', '蕉', '蕊', '蔬', '蕴', '横', '槽',
        '樱', '橡', '樟', '橄', '敷', '豌', '飘', '醋', '醇', '醉', '磕', '磊', '磅', '碾', '震', '霄', '霉', '瞒', '题', '暴', '瞎', '嘻',
        '嘶', '嘲', '嘹', '影', '踢', '踏', '踩', '踪', '蝶', '蝴', '蝠', '蝎',
        '蝌', '蝗', '蝙', '嘿', '嘱', '幢', '墨', '镇', '镐', '镑', '靠', '稽', '稻', '黎', '稿', '稼', '箱', '篓', '箭', '篇', '僵', '躺',
        '僻', '德', '艘', '膝', '膛', '鲤', '鲫', '熟', '摩', '褒', '瘪', '瘤', '瘫', '凛', '颜', '毅', '糊', '遵', '憋', '潜', '澎', '潮',
        '潭', '鲨', '澳', '潘', '澈', '澜', '澄', '懂', '憔', '懊', '憎', '额',
        '翩', '褥', '谴', '鹤', '憨', '慰', '劈', '履', '豫', '缭', '撼', '擂', '操', '擅', '燕', '蕾', '薯', '薛', '薇', '擎', '薪', '薄',
        '颠', '翰', '噩', '橱', '橙', '橘', '整', '融', '瓢', '醒', '霍', '霎', '辙', '冀', '餐', '嘴', '踱', '蹄', '蹂', '蟆', '螃', '器',
        '噪', '鹦', '赠', '默', '黔', '镜', '赞', '穆', '篮', '篡', '篷', '篱',
        '儒', '邀', '衡', '膨', '雕', '鲸', '磨', '瘾', '瘸', '凝', '辨', '辩', '糙', '糖', '糕', '燃', '濒', '澡', '激', '懒', '憾', '懈',
        '窿', '壁', '避', '缰', '缴', '戴', '擦', '藉', '鞠', '藏', '藐', '檬', '檐', '檀', '礁', '磷', '霜', '霞', '瞭', '瞧', '瞬', '瞳',
        '瞩', '瞪', '曙', '蹋', '蹈', '螺', '蟋', '蟀', '嚎', '赡', '穗', '魏',
        '簧', '簇', '繁', '徽', '爵', '朦', '臊', '鳄', '癌', '辫', '赢', '糟', '糠', '燥', '懦', '豁', '臀', '臂', '翼', '骤', '藕', '鞭',
        '藤', '覆', '瞻', '蹦', '嚣', '镰', '翻', '鳍', '鹰', '瀑', '襟', '璧', '戳', '孽', '警', '蘑', '藻', '攀', '曝', '蹲', '蹭', '蹬',
        '巅', '簸', '簿', '蟹', '颤', '靡', '癣', '瓣', '羹', '鳖', '爆', '疆',
        '鬓', '壤', '馨', '耀', '躁', '蠕', '嚼', '嚷', '巍', '籍', '鳞', '魔', '糯', '灌', '譬', '蠢', '霸', '露', '霹', '躏', '黯', '髓',
        '赣', '囊', '镶', '瓤', '罐', '矗', '栟', '桉', '栩', '逑', '逋', '彧', '鬲', '豇', '酐', '逦', '厝', '孬', '砝', '砹', '砺', '砧',
        '砷', '砟', '砼', '砥', '砣', '剞', '砻', '轼', '轾', '辂', '鸫', '趸',
        '龀', '鸬', '虔', '逍', '眬', '唛', '晟', '眩', '眙', '哧', '哽', '唔', '晁', '晏', '鸮', '趵', '趿', '畛', '蚨', '蚜', '蚍', '蚋',
        '蚬', '蚝', '蚧', '唢', '圄', '唣', '唏', '盎', '唑', '崂', '崃', '罡', '罟', '峪', '觊', '赅', '钰', '钲', '钴', '钵', '钹', '钺',
        '钽', '钼', '钿', '铀', '铂', '铄', '铆', '铈', '铉', '铊', '铋', '铌',
        '铍', '铎', '氩', '氤', '氦', '毪', '舐', '秣', '秫', '盉', '笄', '笕', '笊', '笏', '笆', '俸', '倩', '俵', '偌', '俳', '俶', '倬',
        '倏', '恁', '倭', '倪', '俾', '倜', '隼', '隽', '倌', '倥', '臬', '皋', '郫', '倨', '衄', '颀', '徕', '舫', '釜', '奚', '衾', '胯',
        '胱', '胴', '胭', '脍', '胼', '朕', '脒', '胺', '鸱', '玺', '鸲', '狷',
        '猁', '狳', '猃', '狺', '逖', '桀', '袅', '饽', '凇', '栾', '挛', '亳', '疳', '疴', '疸', '疽', '痈', '疱', '痂', '痉', '衮', '凋',
        '颃', '恣', '旆', '旄', '旃', '阃', '阄', '訚', '阆', '恙', '粑', '朔', '郸', '烜', '烨', '烩', '烊', '剡', '郯', '烬', '涑', '浯',
        '涞', '涟', '娑', '涅', '涠', '浞', '涓', '浥', '涔', '浜', '浠', '浣',
        '浚', '悚', '悭', '悝', '悒', '悌', '悛', '宸', '窈', '剜', '诹', '冢', '诼', '袒', '袢', '祯', '诿', '谀', '谂', '谄', '谇', '屐',
        '屙', '陬', '勐', '奘', '牂', '蚩', '陲', '姬', '娠', '娌', '娉', '娲', '娩', '娴', '娣', '娓', '婀', '畚', '逡', '绠', '骊', '绡',
        '骋', '绥', '绦', '绨', '骎', '邕', '鸶', '彗', '耜', '焘', '舂', '琏',
        '㺭', '玚', '塸', '坜', '坉', '埨', '坋', '扺', '㧑', '毐', '芰', '芣', '苊', '苉', '芘', '䒜', '芴', '芠', '芤', '杕', '杙', '杄',
        '杋', '杧', '杩', '尪', '尨', '轪', '軏', '坒', '芈', '旴', '旵', '呙', '㕮', '岍', '㠣', '岠', '岜', '呇', '冏', '觃', '岙', '伾',
        '㑇', '伭', '佖', '佁', '肜', '飏', '狃', '疕', '闶', '汧', '汫', '𠱃',
        '沄', '漙', '沘', '浿', '汭', '㳇', '沕', '沇', '忮', '忳', '忺', '諓', '祃', '诇', '邲', '诎', '诐', '屃', '彄', '岊', '阽', '䢺',
        '阼', '妌', '妧', '媁', '妘', '姂', '纮', '驲', '馼', '纻', '紞', '駃', '纼', '玤', '玞', '珼', '瑽', '玪', '玱', '玟', '邽', '邿',
        '坫', '坥', '坰', '坬', '坽', '弆', '耵', '䢼', '苼', '茋', '苧', '苾',
        '苠', '枅', '㭎', '枘', '枍', '厔', '矼', '矻', '匼', '軝', '暐', '晛', '旿', '昇', '昄', '昒', '昈', '甽', '咉', '咇', '咍', '岵',
        '岽', '岨', '岞', '峂', '㟃', '囷', '釴', '钐', '钔', '钖', '䢾', '牥', '佴', '垈', '侁', '侹', '佸', '佺', '隹', '㑊', '侂', '佽',
        '侘', '㑮', '㑎', '郈', '郐', '郃', '攽', '肭', '肸', '肷', '狉', '狝',
        '㹣', '颹', '饳', '忞', '於', '並', '炌', '炆', '泙', '沺', '泂', '泜', '泃', '泇', '怊', '峃', '穸', '祋', '詷', '詪', '鄩', '鸤',
        '弢', '弨', '陑', '隑', '陎', '隮', '卺', '乸', '㚰', '㚴', '妭', '妰', '姈', '嬣', '妼', '娙', '迳', '叕', '駓', '驵', '駉', '䌹',
        '驺', '䮄', '绋', '绐', '砉', '耔', '㛃', '玵', '玶', '瓐', '珇', '珅',
        '珃', '瓅', '玽', '珋', '玸', '玹', '珌', '玿', '㺹', '韨', '垚', '垯', '垙', '垲', '㧥', '埏', '垍', '耇', '垎', '垴', '垟', '垞',
        '挓', '垏', '拶', '荖', '荁', '荙', '荛', '茈', '茽', '荄', '茺', '蔄', '荓', '茳', '茛', '荭', '㭕', '柷', '柃', '柊', '枹', '栐',
        '柖', '郙', '郚', '剅', '䴓', '迺', '䣅', '厖', '砆', '砑', '砄', '耏',
        '奓', '䶮', '轵', '轷', '轹', '轺', '昺', '睍', '昽', '盷', '咡', '咺', '昳', '昣', '哒', '昤', '昫', '昡', '咥', '昪', '虷', '虸',
        '哃', '峘', '峏', '峛', '峗', '峧', '帡', '钘', '鈇', '鍏', '钜', '鋹', '釿', '錀', '钪', '钬', '钭', '矧', '秬', '俫', '舁', '俜',
        '俙', '俍', '垕', '衎', '㣝', '舣', '弇', '侴', '鸧', '䏡', '胠', '胈',
        '胩', '胣', '朏', '飐', '䫾', '訄', '饻', '庤', '疢', '炣', '炟', '㶲', '洭', '洘', '洓', '洏', '洿', '㳚', '泚', '浉', '洸', '洑',
        '洢', '洈', '洚', '洺', '洨', '浐', '㳘', '洴', '洣', '恔', '宬', '窀', '扂', '謰', '袆', '祏', '祐', '祕', '叚', '陧', '陞', '娀',
        '姞', '姱', '娍', '姯', '嬅', '姤', '姶', '姽', '枲', '绖', '骃', '絪',
        '駪', '綎', '綖', '彖', '骉', '恝', '珪', '珬', '珛', '珹', '玼', '珖', '珚', '勣', '珽', '珦', '珘', '珨', '珫', '珒', '璕', '珢',
        '珕', '珝', '埗', '垾', '垺', '埆', '垿', '埌', '埇', '莰', '茝', '䓣', '鄀', '莶', '莝', '䓂', '莙', '栻', '桠', '梜', '桄', '梠',
        '栴', '梴', '栒', '栘', '酎', '酏', '頍', '砵', '砠', '砫', '砬', '硁',
        '恧', '翃', '郪', '辀', '辁', '剕', '赀', '哢', '晅', '晊', '唝', '哳', '哱', '冔', '晔', '晐', '晖', '畖', '蚄', '蚆', '鄳', '帱',
        '崁', '峬', '峿', '輋', '崄', '帨', '崀', '赆', '鉥', '钷', '鑪', '鉮', '鉊', '鉧', '眚', '甡', '笫', '倻', '倴', '脩', '倮', '倕',
        '倞', '僤', '倓', '倧', '衃', '虒', '舭', '舯', '舥', '瓞', '鬯', '鸰',
    ]
    for first_name in first_name_list:
        print('-------------------'+first_name+"-字：开始爬取-------------------")
        title = '失信被执行人名单'
        url_list = ['https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php' \
                    '?resource_id=6899'
                    '&query=' + title + ''
                    '&cardNum='
                    '&iname=' + first_name + ''
                    '&areaName='
                    '&ie=utf-8'
                    '&oe=utf-8'
                    '&format=json'
                    '&t=1504228484424'
                    '&cb=jQuery110203450799221787775_1504227514772'
                    '&_=1504227514784'
                    ]
        # 爬取姓氏的前30页
        for page_num in range(0, 30):
            url_list.append(
                        'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php'
                        '?resource_id=6899'
                        '&query=' + title + ''
                        '&cardNum='
                        '&iname=' + first_name + ''
                        '&areaName='
                        '&pn='+str(page_num*10)+''
                        '&rn=10'
                        '&ie=utf-8'
                        '&oe=utf-8'
                        '&format=json'
                        '&t=1504259202271'
                        '&cb=jQuery110205604198048294293_1504254835087'
                        '&_=1504254835152'
                        )
        re_spider_page_data(url_list)
    print('-----------------------end:' + str(strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + '-----------------------')
