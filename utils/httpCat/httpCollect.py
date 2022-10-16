import time, json, os, io, sys
from configparser import ConfigParser
# 改变标准输出的默认编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gb18030')


def config_read(file=None):
    """ 读取 ini 配置文件 """
    config_file = os.path.join(os.getcwd(), 'config.ini')
    file = file if file else config_file
    if not os.path.exists(file): return f'Error config.ini文件路径不存在：{file}'
    config = ConfigParser()
    config.read(file, encoding="utf-8")
    list_hosts = config.get('filter', 'host').split(',')
    ini_domain = config.get('filter', 'domain')
    result_path = config.get('filter', 'path')
    return list_hosts, ini_domain, result_path


hosts, domain, ini_path = config_read()


def dumps(txt, beaut=0):
    """ json序列化：dict -> json """
    try:
        if beaut: txt = json.dumps(txt, sort_keys=True, indent=4, ensure_ascii=False)
        else: txt = json.dumps(txt, ensure_ascii=False)
    except: txt = txt
    return txt


def loads(txt):
    """ json反序列化：json -> dict """
    try: txt = json.loads(txt, encoding='UTF-8')
    except: txt = txt
    return txt


def response(flow):
    # 加上过滤条件
    if flow.request.host in hosts and str(flow.response.status_code)[0] in ['2', '3']:
        request_data, headers = {}, {}
        # 请求信息组装
        request_data['method'] = flow.request.method
        request_data['url'] = flow.request.pretty_url
        # headers
        for key, value in flow.request.headers.items(): headers[key] = value
        request_data['headers'] = headers
        # body
        is_body = loads(flow.request.content.decode('utf-8'))
        if is_body: request_data['body'] = is_body
        request_data['response'] = loads(flow.response.content.decode('utf-8'))
        request_data['domain'] = domain
        # 打印日志
        print(dumps(request_data))
        # 写入文件
        file = f'{ini_path}/mitm-{time.strftime("%Y-%m-%d", time.localtime())}.txt'
        with open(file, 'a+', encoding='utf-8')as f:
            f.write(dumps(request_data) + '\n')
