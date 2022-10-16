import re
from model.crud_case import *
from utils.httpRequest import Http
from utils.jsonSchema import loads
h = Http()


def app_env_gray(request_data: dict, re_list=[]):
    """ 定制化区分环境：可能执行同个环境但不同的客户数据，如：灰度AB测试模型
    gray：标识AB测试的环境
    request_data: 请求与响应的数据
    re_txt：匹配字符
    """
    request_data['gray'] = 'gray'
    if not re_list: return request_data
    url, gray = request_data.get('uri'), None
    headers = request_data.get('headers')
    if url:     # 先通过 url 获取 gray
        url_gray1 = re.findall(f'{re_list[0]}=(.+?)&', url, flags=re.IGNORECASE)
        url_gray2 = re.findall(f'{re_list[0]}=(.+?)$', url, flags=re.IGNORECASE)
        if url_gray1: gray = url_gray1[0]
        if url_gray2 and not url_gray1 or len(url_gray1) > 12: gray = url_gray2[0]
    if isinstance(headers, dict):
        str_cookies = headers.get('cookie')
        if not str_cookies: str_cookies = headers.get('Cookie')
    else: str_cookies = headers
    try:
        env_gray1 = re.findall(f'{re_list[1]}=(.+?);', str_cookies, flags=re.IGNORECASE)
        env_gray2 = re.findall(f' {re_list[1]}=(.+?);', str_cookies, flags=re.IGNORECASE)
        env_gray3 = re.findall(f'{re_list[1]}=(.+?)&', str_cookies, flags=re.IGNORECASE)
        env_gray4 = re.findall(f'{re_list[1]}=(.+?)$', str_cookies, flags=re.IGNORECASE)
        if not gray and env_gray1: gray = env_gray1[0]
        if not gray and env_gray2: gray = env_gray2[0]
        if not gray and env_gray3: gray = env_gray3[0]
        if not gray and env_gray4: gray = env_gray4[0]
    except: pass
    if gray: request_data['gray'] = gray
    return request_data


def app_txt_for(file=None, db=None, dir_path=None, key=None):
    """ 循环解析 fiddler/mitmdump 流量文件
    :param file:
    :param db:
    :param dir_path:
    :param key: 企微或钉钉推送key
    :return: 原始数据写入：origin Data
    """
    # SQL 查询配置文件
    tester, count = db_select(conf_type=1, db=db).fastTester, 0
    # db过滤的配置
    split_url_handle, re_list = tester.get('split_url_handle'), tester.get('re_list')
    filter_path, filter_code = tester.get('filter_path'), tester.get('filter_code')
    filter_headers, file_dir = tester.get('filter_headers'), os.path.join(os.getcwd(), 'app')
    if dir_path: file_dir = dir_path
    file_list = [os.path.join(file_dir, file)] if file else [os.path.join(file_dir, file_txt) for file_txt in
                                                             os.listdir(path=file_dir) if '.txt' in file_txt]
    file_list.reverse()
    for file in file_list:
        if not os.path.isfile(file): return h.http_notice(f'[ERROR]方法 app_txt_for() 文件路径不存在：{file}')
        f = open(file, encoding='utf-8')
        while 1:
            line = f.readline()
            request_data: dict = loads(line)
            if isinstance(request_data, dict):
                # 定制化的 request_data,不符合就下一条数据
                request_data = h.http_filter_data(request_data, filter_path, filter_code,
                                                  filter_headers, split_url_handle)
                if not request_data: continue
                request_data = h.http_default_data(request_data)
                request_data = app_env_gray(request_data, re_list)
                # 数据库插入
                db_insert_api(request_data)
                count += 1
            if not line: break
        f.close()
    msg = f'【用例入库】fiddler文件已解析完成 | 共处理数据：{count} 条\n文件路径：{file_list}'
    h.http_notice(msg, key)
    return msg


def app_pytest_txt(file=''):
    """ pytest 执行流量文件测试 """
    all_data, paths, is_file = [], [], False
    file_dir = os.path.join(os.path.abspath(os.path.join(os.getcwd(), "..")), 'app')
    file_path = os.path.join(file_dir, file)
    if len(file) > 23 or file.count('.') > 1: file_path = file
    file_path_all = [os.path.join(file_dir, file_txt) for file_txt in os.listdir(path=file_dir) if '.txt' in file_txt]
    if os.path.isfile(file_path): is_file = True
    file_list = [file_path] if is_file else file_path_all
    for file in file_list:
        if not os.path.isfile(file):
            return h.http_notice(f'[ERROR]方法 app_pytest_txt() 文件路径不存在：{file}')
        f = open(file, encoding='utf-8')
        while 1:
            line = f.readline()
            request_data: dict = loads(line)
            if isinstance(request_data, dict):
                if not request_data: continue
                if not request_data.get('response'): continue
                request_data['file'] = 1
                all_data.append(request_data)
                paths.append(request_data.get('url'))
            else: break
        f.close()
    return all_data, paths, file_list
