import pytest
import requests, time, re, traceback
from loguru import logger as log
from faker import Faker
from utils.jsonSchema import *
from model.models import *


class Http:
    """ Http 处理相关方法 """
    s, faker, = requests.session(), Faker("zh_CN")
    http_variable = {
        'ppl_now_date': time.strftime('%Y-%m-%d'),
        'ppl_now_time': time.strftime('%H:%M:%S'),
        'ppl_now_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'ppl_time': int(time.time())
    }

    def __init__(self, count=2, sleep=3):
        self.count = count  # retry count
        self.sleep = sleep  # Interval retry second
        self.result = object
        self.request_data = {}
        self.curl = str
        self.msg = 'pass'

    def http_setup(self, request_data, replace_dict=None):
        """ 前置处理器 """
        body = request_data.get('body')
        if isinstance(body, str): request_data['body'] = loads(body)
        # 将默认变量替换，如token
        if replace_dict: request_data = self.http_replace(replace_dict, request_data)
        # 将引用变量替换：${key}
        str_request_data = dumps(request_data)
        re_keys = re.findall('\${(.+?)}', str_request_data)
        for re_key in re_keys:
            value = self.http_variable.get(re_key)
            if not value:
                try:
                    # 执行自定义 ppl 方法
                    if 'ppl' in re_key: value = eval(f'self.http_{re_key}')
                    # 执行 faker 方法
                    else: value = eval(f'self.faker.{re_key}()')
                except: value = f'Error:key={re_key} not value'
            if value:
                if isinstance(value, str):
                    try: value = int(value)
                    except: value = f'"{value}"'
                str_request_data = str_request_data.replace(('"${%s}"' % re_key), str(value))
                str_request_data = str_request_data.replace(('${%s}' % re_key), value.replace('"', ''))
        return loads(str_request_data)

    def http(self, request_data):
        self.request_data = request_data.copy()
        # method url
        method = request_data.pop('method', None)
        url = request_data.pop('url', None)
        # request body -->data?-->json
        body = request_data.pop('body', None)
        if isinstance(body, str): request_data['data'] = body.encode('utf-8')
        if isinstance(body, dict): request_data['json'] = body
        # default：result, status_code, response
        result, status_code, response = 0, 0, ''
        # retry request
        while self.count > -1:
            result = self.s.request(method, url, **request_data)
            self.result = result
            status_code = result.status_code
            try: response = result.json()
            except: response = result.text
            if status_code != 200:
                # No retry count：break
                if self.count <= 0: break
                self.count -= 1
                time.sleep(self.sleep)
                continue
            break
        return status_code, response, result

    def http_collect(self, response, collects, result):
        """ 后置处理器,参数化变量收集器 (默认返回 index=0)
        todo jsonpath -->  ['$.data.key','key',{'key':index}]
        todo 正则表达式 --> [{'token:'正则表达式'},{'token:['正则表达式',index]}]
        """
        value = None
        if not collects: return 0
        if 'ppl_body' in collects: return self.http_variable.update(response)
        if 'ppl_all' in collects:
            self.http_variable.update(result.headers)
            return self.http_variable.update(response)
        if 'ppl_cookie' in collects: return result.cookies
        if result: response.update(result.headers)
        collects = list(collects)
        for collect in collects:
            if isinstance(collect, dict):
                if collect.get('re'): response = dumps(response)
            if isinstance(response, dict) or isinstance(response, list):
                # todo jsonpath
                if isinstance(collects, list) or isinstance(collects, tuple):
                    if '$' in str(collect):
                        # todo 原生 jsonpath
                        if isinstance(collect, str):
                            value = jsonpath(response, collect)
                            collect = collect.split('.')[-1]
                            if value: value = value[0]
                        if isinstance(collect, dict):
                            for k, v in collect.items():
                                if isinstance(v, str):
                                    value = jsonpath(response, k)
                                    collect = v
                                if isinstance(v, int):
                                    value = jsonpath(response, k)
                                    if value: value = value[v]
                                    collect = k.split('.')[-1]
                                if isinstance(v, list):
                                    value = jsonpath(response, k)
                                    if value: value = value[v[1]]
                                    collect = v[0]
                    elif isinstance(collect, dict):
                        for k, v in collect.items():
                            if isinstance(v, str):
                                value = json_path(response, k)
                                collect = v
                            if isinstance(v, int):
                                value = json_path(response, k, v)
                                collect = k
                            if isinstance(v, list):
                                value = json_path(response, k, v[1])
                                collect = v[0]
                    else:
                        value = json_path(response, collect)
                    if value: self.http_variable.update({collect: value})
            if isinstance(response, str):
                # todo 正则表达式 [{'re':['env','https://(.+?)/'}]]
                if isinstance(collects, list) or isinstance(collects, tuple):
                    if isinstance(collect, dict):
                        for k, v in collect.items():
                            if isinstance(v, list) or isinstance(v, tuple):
                                if len(v) >= 3:
                                    re_str = v[1]
                                    re_index = v[2] - 1
                                    value = re.findall(f'{re_str}', response)[re_index]
                                else:
                                    value = re.findall(f'{v[1]}', response)
                                    if value: value = value[0]
                            self.http_variable.update({v[0]: value})
        return self.http_variable

    def http_assert(self, assert_list=[], print_=0, result=None, curl=None, schema_response={}, old_response=''):
        """
        断言：
        1.txt in result.text
        2.txt == result.json().get('key')
        """
        curl = curl if curl else self.http_curl(self.request_data)
        result = result if result else self.result
        status_code = result.status_code
        txt, log_txt = '断言结果：', ''
        msg, exp = 'fail', '正则表达式无匹配'
        if assert_list and isinstance(assert_list, list):
            for assert_ in assert_list:
                # todo 自定义的断言
                if isinstance(assert_, str) and assert_ in 'ppl_schema':
                    exp = schema_exp(result.json(), schema_response)
                    msg = self.http_assert_custom(f'"{str(exp)}" == "pass"')
                elif isinstance(assert_, str):
                    exp = str(assert_)
                    if '$' in assert_:
                        k = re.findall('\${(.+?)}', assert_)
                        if k: k = k[0]
                        exp = str(self.http_variable.get(k))
                    msg = self.http_assert_custom(f'"{exp}" in "{loads(result.text)}"')
                elif isinstance(assert_, dict):
                    for k, v in assert_.items():
                        response_value = json_path(result.json(), k)
                        if k == 're':
                            re_str = re.findall(f'{v}', result.text)
                            if re_str: exp = 'pass'
                            msg = self.http_assert_custom(f'"{exp}" == "pass"', f'正则表达式匹配值：{re_str} ')
                        elif isinstance(v, str) or isinstance(v, int):
                            exp = str(v)
                            msg = self.http_assert_custom(f'"{exp}" == "{response_value}"')
                        elif isinstance(v, list) or isinstance(v, tuple):
                            selector = v[1]
                            exp = str(v[0])
                            if selector in ['eq', 'equals', '==', 'is', '=']:
                                msg = self.http_assert_custom(f'"{exp}" == "{response_value}"')
                            elif selector in ['in']:
                                msg = self.http_assert_custom(f'"{exp}" in "{response_value}"')
                            elif selector in ['len', 'count']:
                                msg = self.http_assert_custom(f'{exp} == {len(str(response_value))}')
                            elif selector in ['not', 'not in']:
                                msg = self.http_assert_custom(f'"{exp}" not in "{response_value}"')
                            elif selector in ['!=', '≠']:
                                msg = self.http_assert_custom(f'"{exp}" != "{response_value}"')
                log_txt = f'{txt}{msg}\n--->assert_list={assert_list}\n\n{curl}\n\nResponse：statusCode={status_code}\n{dumps(result.json(), 1)}\n'
                if msg != 'pass':
                    if print_: log.info(log_txt)
                    return msg
                txt = '断言结果：'
            if print_: log.info(log_txt)
        else:
            msg = schema_exp(result.text, schema_response)
            if 'schema_create Error' in str(schema_response):
                txt += 'Response String Exp ---> '
                if self.http_assert_custom(f'{old_response} == {dumps(result.text)}'): msg = 'pass'
            txt += f'{msg}\n\n{curl}\n\nResponse：statusCode={status_code}\n{dumps(result.text, 1)}\n'
            if print_: log.info(txt)
            self.http_assert_custom(f'{status_code} == 200')
            self.http_assert_custom(f'"{msg}" == "pass"')
        return msg

    def http_assert_custom(self, str_assert, txt=None):
        """ 断言封装 """
        try:
            exec(f'assert {str_assert}')
            msg = self.msg
        except:
            msg = f'http_assert_custom Error：[{str_assert}]'
            if 'AssertionError' in traceback.format_exc(): msg = f'AssertionError：Not [{str_assert}]'
        if txt: msg = txt + msg
        return msg

    def http_main(self, request_data: dict, print_=1, db_obj_insert=None, db_model=None, file=0, add_replace={}):
        """ 主程序入口
        request_data: request data
        """
        # 必要的参数
        collects = request_data.pop('collects', None)
        assert_list = request_data.pop('assert_list', None)
        schema_response = request_data.pop('schema_response', None)
        if not assert_list: assert_list = {}
        if file:
            # 请求
            request_data.pop('domain', None)
            request_data_response = request_data.pop('response', None)
            status_code, response, result = self.http(request_data)
            schema_response = schema_create(request_data_response)
            # 断言
            msg = self.http_assert(result=result, print_=print_,
                                   schema_response=schema_response, old_response=request_data_response)
        else:
            # 前置
            self.http_variable.update(add_replace)
            res_request_data = {
                'method': request_data.get('method'),
                'url': request_data.get('url'),
                'headers': request_data.get('headers'),
                'body': request_data.get('body')}
            res_request_data = self.http_setup(res_request_data)
            # 请求
            res_request_data['cookies'] = request_data.get('cookies')
            status_code, response, result = self.http(res_request_data)
            # 后置
            self.http_collect(response, collects, result)
            # 断言
            msg = self.http_assert(assert_list, print_=print_, schema_response=schema_response)
            if isinstance(db_obj_insert, object) and db_obj_insert is not None:
                # 插入数据库
                request_data['msg'] = msg
                request_data['response'] = response
                request_data_copy = self.http_default_data(request_data)
                db_obj_insert(request_data_copy, db_model=db_model)
        if msg != 'pass': pytest.fail(msg)
        return msg

    def http_curl(self, request_data=None):
        """ 生成curl
        :param request_data:
        :return:
        """
        request_data: dict = request_data if request_data else self.request_data
        url = request_data.pop('url', None)
        method = request_data.get('method')
        headers = request_data.get('headers')
        body = request_data.get('body')
        if isinstance(body, dict):
            body = dumps(body)
            if not headers: headers = {'Content-Type': 'application/json'}
        header = ''
        if headers:
            header += '\n'
            for k, v in headers.items():
                header += f'  -H \'{k}: {v}\' \\\n'
            header = header[:-2]
        self.curl = f'curl -X {method} \\\n  \'{url}\''
        if header: self.curl += f'\\{header}'
        if method == 'POST' and body:
            if '&' in body and '%' in body and '=' in body:
                import urllib.parse
                body = urllib.parse.unquote(body)
            self.curl += f'\\\n  -d \'{body}\'\n'
        return self.curl

    def http_split_url(self, url=None, split_url_handle={}):
        """ 解析 host path query
        :param url:
        :param split_url_handle: 特殊处理表达式
        :return: host, path, query or host, path
        """
        url = url if url else self.request_data.get('url')
        host_split = url.split('//')
        host = f'{host_split[0]}//{host_split[1].split("/")[0]}'
        path = '/' + '/'.join(host_split[1].split("/")[1:])
        uri = path
        query = None
        if '?' in path and '=' in path:
            query = path.split('?')[1]
            path = path.split('?')[0]
            query = dict([x.split('=', 1) for x in query.split('&')])
            # 接口特殊处理
            for k, v in split_url_handle.items():
                if k in path: path = eval(v)
        return host, path, query, uri

    def http_replace(self, replace_dict, request_data=None):
        """
        :param request_data: 只要替换这几种 url、headers、data/json
        :param replace_dict: 需要适配大小写
        :return:
        """
        request_data: dict = request_data if request_data else self.request_data
        # url or data 转 dict：?a=1 → {'a':1}
        request_data = self.http_un_data(request_data)
        # 遍历需要替换的 key 进行替换
        dumps_request_data = dumps(request_data)
        for k, v in replace_dict.items():
            re_kye = set(re.findall(k, dumps_request_data, flags=re.IGNORECASE))
            for re_k in re_kye:
                paths = jsonpath(request_data, f'$..{re_k}', 'PATH')
                if paths:
                    for path in paths:
                        key_path: str = path[1:]
                        exec(f'request_data{key_path}=v')
        # 拼接会原样
        request_data = self.http_un_data(request_data, en_data=True)
        return request_data

    def http_un_data(self, request_data=None, en_data=False):
        """
        1、en_data=False str → dict 如：?a=1&b=2 → {'a':1,'b':2}
        2、en_data=True dict → str 如：{'a':1,'b':2} → ?a=1&b=2
        """
        request_data: dict = request_data if request_data else self.request_data
        url = request_data.get('url')
        data = request_data.get('data')
        body = request_data.get('body')
        if isinstance(body, str):
            data = body
        if en_data:
            url, data = f'{url}?', ''
            query = request_data.pop('query', None)
            data_ = request_data.pop('data', None)
            if query:
                for uk, uv in query.items():
                    url += f'{uk}={uv}&'
                url = url[:-1]
                request_data['url'] = url
            if data_:
                for dk, dv in data_.items():
                    data += f'{dk}={dv}&'
                data = data[:-1]
                request_data['body'] = data
        else:
            # 将 url、data 分别拆成 dict：query、data
            if url and '?' in url:
                query = url.split('?')[1]
                host = url.split('?')[0]
                request_data['url'] = host
                request_data['query'] = dict([x.split('=', 1) for x in query.split('&')])
            if data:
                data = dict([x.split('=', 1) for x in data.split('&')])
                request_data['data'] = data
        return request_data

    def http_default_data(self, request_data=None, add_request_data={}):
        """ 新数据都需要生成的默认 requestData
        :param request_data:
        :param add_request_data:
        :return:
        """
        request_data: dict = request_data if request_data else self.request_data
        # 附加的参数
        request_data.update(add_request_data)
        response = request_data.get('response')
        request_data['response'] = response
        request_data['schema_response'] = schema_create(response)
        request_data['curl'] = self.http_curl(request_data)
        return request_data

    def http_ppl_datetime(self, days=-7):
        """ 过去七天 """
        import datetime
        day = ((datetime.datetime.now()) + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        day_time = f'{day} 00:00:00'
        if days > 0: day_time = f'{day} 23:59:59'
        self.http_variable[f'ppl_datetime{days}'] = day_time
        return day_time

    def http_notice(self, txt, key=None):
        """ http 请求通知：企微或钉钉推送
        :param txt: 要发送的文字
        :param key:
        :return:
        """
        if not key: return f'未配置推送key,本次不推送测试结果：\n{txt}'
        request_data = {'method': 'POST',
                        'url': f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}',
                        'json': {'msgtype': 'text', 'text': {'content': f'{txt}\n\n时间：{datetime.now()}'}}}
        # 如果是钉钉推送需要改动以下，钉钉key=64长度
        if len(key) == 64:
            request_data['url'] = f'https://oapi.dingtalk.com/robot/send?access_token={key}'
            request_data['json'] = {'msgtype': 'text', 'at': {'atMobiles': [], 'isAtAll': False},
                                    'text': {'content': f'{txt}\n\n时间：{datetime.now()}'}}
        res_carry = self.http(request_data)
        return res_carry

    @staticmethod
    def http_crete_replace(response: dict = None, pop=[], replace_data={}, old_response=None):
        """ 递归
        :param response: 遍历 key：value 生成可替换参数
        :param pop: 剔除
        :param replace_data:
        :param old_response:
        :return:
        """
        old_result = old_response if old_response else response.copy()
        for k, v in response.items():
            if isinstance(v, dict):
                try: old_result.pop(k)
                except: pop.append(k)
                Http.http_crete_replace(v, pop, replace_data, old_result)
            if isinstance(v, list) and len(v) >= 1: v = v[0]
            if k not in pop: replace_data[k] = v
        if old_result and old_result != 1: Http.http_crete_replace(old_result, pop, replace_data, 1)
        return replace_data

    @staticmethod
    def http_filter_data(request_data, filter_path, filter_code, filter_headers, split_url_handle={}, file_type=None):
        """ 过滤不必要的数据
        :param request_data:
        :param filter_path:
        :param filter_code:
        :param filter_headers:
        :param split_url_handle:
        :param file_type:
        """
        response = request_data.get('response')
        if isinstance(response, str):
            response = {'ppl_response': response}
        if not isinstance(response, dict): return 0
        if not file_type:
            # 过滤接口，比如退出登录，重新登录
            url = request_data.get('url')
            host, path, query, uri = Http().http_split_url(url, split_url_handle)
            if path in str(filter_path): return 0
            request_data['host'] = host
            request_data['uri'] = uri
            request_data['path'] = path
            request_data['query'] = query
            # 过滤返参code是否符合要求
            if not response.get('ppl_response'):
                if filter_code:
                    for k, v in filter_code.items():
                        err_code, ret_code = True, response.get(k)
                        for i in v:
                            if ret_code == i: err_code = False
                        if err_code: return 0
        # headers 删除非必要的参数
        origin_headers, headers = request_data.get('headers'), {}
        if isinstance(origin_headers, dict):
            for k, v in origin_headers.items():
                if k.lower() not in filter_headers: headers[k] = v
        if isinstance(origin_headers, str):
            for i in origin_headers.split(','):
                i = i.split(': ')
                if len(i) > 1 and i[0].lower() not in filter_headers: headers[i[0]] = i[1]
        request_data['headers'] = headers
        return request_data
