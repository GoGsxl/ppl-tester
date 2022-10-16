import os
from configparser import ConfigParser
from model.crud_case import db_select
from model import models, dbBase
from utils.httpRequest import *
from app.write_api import app_pytest_txt, app_txt_for
h = Http()


def pytest_addoption(parser):
    """ env 参数的说明 """
    help_txt = 'choose env: --env domain,env'
    help_txt1 = 'choose file: --file 1'
    help_txt2 = 'choose param: --param {"a":"master"}'
    help_txt3 = 'choose red_txt: --red_txt false'
    help_txt4 = 'choose init: --init false'
    help_txt5 = 'choose key: --key xxx'
    parser.addoption("--env", action="store", help=help_txt)
    parser.addoption("--file", action="store", help=help_txt1)
    parser.addoption("--param", action="store", help=help_txt2)
    parser.addoption("--red_txt", action="store", help=help_txt3)
    parser.addoption("--init", action="store", help=help_txt4)
    parser.addoption("--key", action="store", help=help_txt5)
    parser.addini('env', help=help_txt)
    parser.addini('file', help=help_txt1)
    parser.addini('param', help=help_txt2)
    parser.addini('red_txt', help=help_txt3)
    parser.addini('init', help=help_txt4)
    parser.addini('key', help=help_txt5)


def env_vars(metafunc):
    """ 获取命令行参数的值 --env 或 env 没有则默认ini文件[tested]"""
    config = metafunc.config
    cur_env = config.getoption('--env') or config.getini('env')
    cur_param = config.getoption('--param') or config.getini('param')
    file_env = config.getoption('--file') or config.getini('file')
    red_txt = config.getoption('--red_txt') or config.getini('red_txt')
    init = config.getoption('--init') or config.getini('init')
    key = config.getoption('--key') or config.getini('key')
    variables, conf, inifile = {}, ConfigParser(), config.inifile
    conf.read(inifile)
    if conf.has_section('tested'): variables.update(conf.items('tested'))
    if cur_env:variables['env'] = cur_env
    if cur_param:variables['param'] = cur_param
    if file_env:variables['file'] = file_env
    if red_txt:variables['red_txt'] = red_txt
    if init:variables['init'] = init
    if init:variables['key'] = key
    # 获取当前运行的test_*.py文件
    variables['python_file'] = config.inicfg.get('python_files')
    return variables


def get_data(param, db_conf, domain, play_type=None):
    """ 查询测试数据以及替换参数
    :param param: param 多参数
    :param db_conf: db_conf 配置的对象
    :param domain: domain
    :param play_type: 是否流量回放？
    """
    add_replace_dict, replace_dict = {}, {}
    for k, v in param.items(): add_replace_dict[k] = v
    try: tester = db_conf.fastTester
    except: pytest.exit(f'Error db_conf.fastTester获取异常：{domain}', returncode=1)
    com_tester = db_select(conf_type=1).fastTester
    testers, db_all_obj, cases, paths, hosts, gray = tester.get('Tester'), [], [], [], [], tester.get('gray')
    for test in testers:
        for host, value in test.items():
            hosts.append(host)
            if play_type:db_data = db_select(host, domain, gray=gray)
            else:db_data = db_select(host, domain, db_model=PPlFormal, gray=gray)
            if not db_data:
                log.info(f'查询数据为空：{host}')
                break
            if value:
                collects = value.pop('collects', None)
                value['url'] = host + value['url']
                status_code, response, result = h.http(value)
                log.info(f'--->：域名：{host}，登录结果：{response}')
                cookie = result.cookies.get_dict()
                if cookie: add_replace_dict.update(cookie)
                replace_dict = h.http_collect(response, collects, result)
                replace_dict.update(add_replace_dict)
            for db in db_data:
                # 测试数据组装
                dict_data, path = db.__dict__, db.path
                for i in com_tester.get('db_pop'): dict_data.pop(i, None)
                if db.api_name: path = f'{db.api_name}_{path}'
                db.headers['Cookie'] = ''.join([f'{k}={v};' for k, v in add_replace_dict.items()])
                request_data = {'headers': db.headers, 'url': db.host + db.uri, 'body': db.body}
                request_data = h.http_replace(replace_dict, request_data)
                dict_data.update(request_data)
                paths.append(path)
                cases.append(dict_data)
    return cases, paths, hosts


def pytest_generate_tests(metafunc):
    """ 自定义参数化 """
    # 获取命令行参数
    variables = env_vars(metafunc)
    file_path = variables.pop('file', None)
    param = loads(variables.pop('param', None))
    red_txt = variables.pop('red_txt', None)
    key = variables.pop('key', None)
    # 判断是否创建初始化数据库表结构
    init = variables.pop('init', None)
    if init == 'true':
        models.Base.metadata.create_all(dbBase.engine)
        pytest.exit('-----------------> 新建表结构成功 <-----------------', returncode=1)
    # 判断是否是test_playback.py
    python_file = variables.pop('python_file', None)
    if not isinstance(param, dict): param = {}
    if not file_path:
        # 判断是否先读取txt文件用例入库
        proj_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if red_txt == 'true':   # 用例入库
            msg = app_txt_for(dir_path=os.path.join(proj_path, 'app'), key=key)
            pytest.exit(f'-----------------> {msg} <-----------------', returncode=1)
        # 切割 env 参数，db查询环境配置
        env_list = variables.pop('env').split(',')
        domain, env, play = env_list[0], env_list[1], None
        if 'playback' in python_file: play = True
        db_conf = db_select(domain=domain, env=env, conf_type=1)
        # db 获取用例
        all_data, paths, hosts = get_data(param, db_conf, domain, play)
        # 最后写入 environment.properties 文件
        txt = f'Tested={domain}-{env}\nHost={hosts}\nparam={dumps(param)}\n'
        txt += 'Author=PPL\nBlog=https://blog.csdn.net/qq_42675140'
    else:
        # 流量回放，读取文件数据
        all_data, paths, file_list = app_pytest_txt(file_path)
        # 最后写入 environment.properties 文件
        txt = f'file_list={file_list}\nexplain=This is the read file use case test\n'
        txt += 'Author=PPL\nBlog=https://blog.csdn.net/qq_42675140'
    if not all_data: pytest.exit('-----------------> 用例为空！ <-----------------', returncode=1)
    # 参数化
    if "param" in metafunc.fixturenames:
        metafunc.parametrize("param", all_data, ids=paths, scope="function")
    with open('allure/report/environment.properties', 'w')as f:
        f.write(txt)
