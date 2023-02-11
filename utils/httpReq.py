import base64, ssl, socket
from urllib import parse
from urllib3 import encode_multipart_formdata
import pytest, requests, time, re, traceback
from hyper.contrib import HTTP20Adapter
from faker import Faker
from dateutil import parser
from utils.public import *


class Http:
    """ http method """

    def __init__(self, log_name='http', count=2, sleep=3, ini_file=None, locale: list = ['zh_CN'], lower_=True):
        self.s = requests.session()
        self.logs = ppl_log(True, log_name)
        self.count = count  # retry count
        self.sleep = sleep  # Interval retry second
        self.result, self.curl = object, str
        self.request_data, self.upload = {}, {}
        self.msg, self.conf = 'pass', read_config(ini_file, self.logs, lower_)
        self.faker = Faker(locale if self.conf.get('locale') else locale)
        self.http_variable = {'ppl_now_date': time.strftime('%Y-%m-%d'),
                              'ppl_now_time': time.strftime('%H:%M:%S'),
                              'ppl_now_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                              'ppl_time': int(time.time())}

    def http_setup(self, request_data, replace_dict={}):
        """ setup """
        body = request_data.get('body')
        if isinstance(body, str): request_data['body'] = loads(body)
        # Default variable replace cases:token
        if replace_dict: request_data = self.http_replace(replace_dict, request_data)
        # Replace reference variable:${key}
        str_request_data = dumps(request_data)
        re_keys = re.findall('\${(.+?)}', str_request_data)
        for re_key in re_keys:
            value = self.http_variable.get(re_key)
            if not value:
                try:
                    # custom ppl method
                    if 'ppl' in re_key: value = eval(f'self.http_{re_key}')
                    # faker method
                    else:
                        if '(' in re_key and ')' in re_key:
                            value = eval(f'self.faker.{re_key}')
                            if '.' in value: value = float(value)
                            else: value = int(value)
                        else: value = eval(f'self.faker.{re_key}()')
                except:
                    value = replace_dict.get(re_key)
                    if not value: value = f'Error:key={re_key} not value'
            if value:
                if isinstance(value, str):
                    try: value = int(value)
                    except: value = f'"{value}"'
                str_request_data = str_request_data.replace(('"${%s}"' % re_key), str(value))
                try: str_request_data = str_request_data.replace(('${%s}' % re_key), value.replace('"', ''))
                except: str_request_data = str_request_data.replace(('${%s}' % re_key), str(value).replace('"', ''))
        return loads(str_request_data)

    def http(self, request_data):
        self.request_data = request_data.copy()
        # method url
        method = request_data.pop('method', 'GET')
        url = request_data.pop('url', '')
        # compatible with http2 (:authority)
        try:
            if ':' in ''.join(list(request_data.get('headers').keys())):
                host, path, query, uri = self.http_split_url(url)
                self.s.mount(host, HTTP20Adapter())
        except: pass
        # request body -->data?-->json
        body = request_data.pop('body', None)
        if isinstance(body, str): request_data['data'] = body.encode('utf-8')
        if isinstance(body, dict):
            request_data['json'] = body
            # compatible with upload file: multipart/form-data
            if isinstance(body.get('file'), list):
                if 'multipart/form-data' in ''.join(list(request_data.get('headers', {}).values())):
                    file_tuple = tuple(body.get('file', []))
                    if len(file_tuple) >= 2:
                        body['file'] = (file_tuple[0], base64.b64decode(file_tuple[1]))
                        encode_data = encode_multipart_formdata(body)
                        headers = request_data.get('headers', {})
                        headers['Content-Type'] = encode_data[1]
                        request_data['headers'] = headers
                        request_data['data'] = encode_data[0]
                        request_data.pop('json')
        # default：result, status_code, response
        result, status_code, response = 0, 0, ''
        # retry request
        while self.count > -1:
            result = self.s.request(method, url, **request_data)
            self.result = result
            status_code = result.status_code
            if status_code != 200:
                # No retry count：break
                if self.count <= 0: break
                self.count -= 1
                time.sleep(self.sleep)
                continue
            try: response = result.json()
            except:
                response = result.text
                # compatible with upload file response
                if 'filename=' in ''.join([str(k) for k in result.headers.values()]):
                    self.upload = base64.b64encode(result.content).decode()
            break
        return status_code, response, result

    def http_collect(self, response, collects, result):
        """ http collect (default index=0)
        jsonpath -->  ['$.data.key','key',{'key':index}]
        regular  -->  [{'token:'pattern'},{'token:['pattern',index]}]
        """
        if not collects: return 0
        value, headers = None, {}
        if result:
            for k, v in result.headers.items(): headers[k] = v
        if 'ppl_body' in collects:
            self.http_variable.update(response)
            return self.http_variable
        if 'ppl_all' in collects:
            self.http_variable.update(headers)
            self.http_variable.update(response)
            return self.http_variable
        if 'ppl_cookie' in collects: return result.cookies
        if isinstance(response, dict): response.update(headers)
        collects = list(collects)
        for collect in collects:
            if isinstance(collect, dict):
                if collect.get('re'): response = dumps(response)
            if isinstance(response, dict) or isinstance(response, list):
                # Get jsonpath value
                if isinstance(collects, list) or isinstance(collects, tuple):
                    if '$' in str(collect):
                        # origin jsonpath
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
                    else: value = json_path(response, collect)
                    if value: self.http_variable.update({collect: value})
            if isinstance(response, str):
                # regular expression：[{'re':['host','https://(.+?)/'}]]
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
        """ assert
        1.txt in result.text
        2.txt == result.json().get('key')
        """
        curl = curl if curl else self.http_curl(self.request_data)
        result = result if result else self.result
        status_code = result.status_code
        txt, log_txt = 'Assertion results：', ''
        msg, exp = 'fail', 'Regular expression does not match'
        assert_response = self.upload if self.upload else result.text
        if assert_list and isinstance(assert_list, list):
            for assert_ in assert_list:
                # custom assert
                if isinstance(assert_, str) and assert_ in 'ppl_schema':
                    exp = schema_exp(result.json(), schema_response)
                    msg = self.http_assert_custom(f'"{str(exp)}" == "pass"')
                elif isinstance(assert_, str):
                    exp = str(assert_)
                    if '$' in assert_:
                        k = re.findall(r'\${(.+?)}', assert_)
                        if k: k = k[0]
                        exp = str(self.http_variable.get(k))
                    msg = self.http_assert_custom(f'"{exp}" in "{loads(assert_response)}"', exp, assert_response)
                elif isinstance(assert_, dict):
                    for k, v in assert_.items():
                        response_value = json_path(result.json(), k)
                        if k == 're':
                            re_str = re.findall(f'{v}', assert_response)
                            if re_str: exp = 'pass'
                            msg = self.http_assert_custom(f'"{exp}" == "pass"', f'Regular match value：{re_str} ')
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
                log_txt = f'{txt}{msg}\n--->assert_list={assert_list}\n\n{curl}\n\nResponse：statusCode={status_code}'
                log_txt += f'\n{dumps(assert_response, 1)}\n'
                if msg != 'pass':
                    if print_: self.logs.info(log_txt)
                    return msg
                txt = 'Assertion result：'
            if print_: self.logs.info(log_txt)
        else:
            msg = schema_exp(assert_response, schema_response)
            if 'schema_create Error' in str(schema_response):
                txt += 'Response String Exp ---> '
                msg = self.http_assert_custom(f'{old_response == assert_response}')
            txt += f'{msg}\n\n{curl}\n\nResponse：statusCode={status_code}\n{dumps(loads(assert_response), 1)}\n'
            if print_: self.logs.info(txt)
            self.http_assert_custom(f'{status_code} == 200')
            self.http_assert_custom(f'"pass" == "{msg}"')
        self.upload = {}
        return msg

    def http_assert_custom(self, str_assert, exp=None, res_str=None, txt=None):
        """ assert custom """
        try:
            exec(f'assert {str_assert}')
            msg = self.msg
        except:
            if exp and res_str:
                exec(f'assert "{exp}" in {dumps(res_str)}')
                msg = self.msg
            else:
                msg = f'http_assert_custom Error：[{str_assert}]'
                if 'AssertionError' in traceback.format_exc(): msg = f'AssertionError：Not [{str_assert}]'
                if str_assert.lower() == 'false': msg = 'Expected response != Actual response'
        if txt: msg = txt + msg
        return msg

    def http_main(self, request_data: dict, print_=1, db_obj_insert=None, file=0, add_replace={}):
        """ main """
        # Required parameters
        collects = request_data.pop('collects', None)
        assert_list = request_data.pop('assert_list', None)
        schema_response = request_data.pop('schema_response', None)
        old_response = request_data.pop('response', None)
        if not assert_list: assert_list = {}
        if file:
            # file playback
            request_data.pop('domain', None)
            request_data.pop('gray', None)
            status_code, response, result = self.http(request_data)
            schema_response = schema_create(old_response)
            msg = self.http_assert(result=result, old_response=old_response,
                                   print_=print_, schema_response=schema_response)
        else:
            # db cases:Setup
            self.http_variable.update(add_replace)
            res_request_data = {'method': request_data.get('method'), 'url': request_data.get('url'),
                                'headers': request_data.get('headers'), 'body': request_data.get('body')}
            res_request_data = self.http_setup(res_request_data)
            # Request
            res_request_data['cookies'] = request_data.get('cookies')
            status_code, response, result = self.http(res_request_data)
            # Post
            cp_response = response
            if isinstance(response, dict): cp_response = response.copy()
            self.http_collect(cp_response, collects, result)
            # Assert
            msg = self.http_assert(assert_list, print_, schema_response=schema_response, old_response=old_response)
            if isinstance(db_obj_insert, object) and db_obj_insert is not None and msg == 'pass':
                # Insert database
                request_data['msg'] = msg
                request_data['response'] = response
                request_data_copy = self.http_default_data(request_data)
                db_obj_insert(request_data_copy)
        if msg != 'pass': pytest.fail(msg)
        return msg

    def http_curl(self, request_data={}):
        """ crete curl """
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
            for k, v in headers.items(): header += f'  -H \'{k}: {v}\' \\\n'
            header = header[:-2]
        self.curl = f'curl -X {method} \\\n  \'{url}\''
        if header: self.curl += f'\\{header}'
        if body:
            if '&' in body and '%' in body and '=' in body: body = parse.unquote(body)
            self.curl += f'\\\n  -d \'{body}\'\n'
        return self.curl

    def http_split_url(self, url=None):
        """ analysis URL """
        try:
            host_split = url.split('//')
            host = f'{host_split[0]}//{host_split[1].split("/")[0]}'
            path = '/' + '/'.join(host_split[1].split("/")[1:])
            query, uri = None, path
            if '?' in path and '=' in path:
                query = path.split('?')[1]
                path = path.split('?')[0]
                query = dict([x.split('=', 1) for x in query.split('&')])
                # php Api
                if '.php' in path: path = path + '?r=' + query.pop('r')
            return host, path, query, uri
        except:
            self.logs.error(f'analysis URL error：{url}')
            return None, None, None, None

    def http_replace(self, replace_dict, request_data={}):
        """ replace request data """
        request_data: dict = request_data if request_data else self.request_data
        # url or data -> dict：?a=1 → {'a':1}
        request_data = self.http_un_data(request_data)
        # for key replace
        dumps_request_data = dumps(request_data)
        for k, v in replace_dict.items():
            re_kye = set(re.findall(k, dumps_request_data, flags=re.IGNORECASE))
            for re_k in re_kye:
                paths = jsonpath(request_data, f'$..{re_k}', 'PATH')
                if paths:
                    for path in paths:
                        key_path: str = path[1:]
                        exec(f'request_data{key_path}=v')
        # join origin
        request_data = self.http_un_data(request_data, en_data=True)
        return request_data

    def http_un_data(self, request_data={}, en_data=False):
        """
        1、en_data=False str → dict as：?a=1&b=2 → {'a':1,'b':2}
        2、en_data=True dict → str as：{'a':1,'b':2} → ?a=1&b=2
        """
        request_data: dict = request_data if request_data else self.request_data
        url = request_data.get('url')
        data = request_data.get('data')
        body = request_data.get('body')
        if isinstance(body, str): data = body
        if en_data:
            url, data = f'{url}?', ''
            query = request_data.pop('query', None)
            data_ = request_data.pop('data', None)
            if query:
                for uk, uv in query.items(): url += f'{uk}={uv}&'
                url = url[:-1]
                request_data['url'] = url
            if data_:
                for dk, dv in data_.items(): data += f'{dk}={dv}&'
                data = data[:-1]
                request_data['body'] = data
        else:
            # dict：query、data
            if url and '?' in url:
                query = url.split('?')[1]
                host = url.split('?')[0]
                request_data['url'] = host
                request_data['query'] = dict([x.split('=', 1) for x in query.split('&')])
            if data:
                data = dict([x.split('=', 1) for x in data.split('&')])
                request_data['data'] = data
        return request_data

    def http_default_data(self, request_data={}, add_request_data={}):
        """ default request data
        :param request_data:
        :param add_request_data:
        """
        request_data: dict = request_data if request_data else self.request_data
        # Add parameter
        request_data.update(add_request_data)
        response = request_data.get('response')
        request_data['response'] = response
        request_data['schema_response'] = schema_create(response)
        request_data['curl'] = self.http_curl(request_data)
        return request_data

    def http_ppl_datetime(self, days=-7):
        """ ppl datetime """
        import datetime
        day = ((datetime.datetime.now()) + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        day_time = f'{day} 00:00:00'
        if days > 0: day_time = f'{day} 23:59:59'
        self.http_variable[f'ppl_datetime{days}'] = day_time
        return day_time

    def http_notice(self, txt, key=None):
        """ notice """
        if not key: key = self.conf.get('notice_key', None)
        if not key: return -1, 'Notification key is not configured!', None
        request_data = {'method': 'POST',   # WeChat
                        'url': f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}',
                        'json': {'msgtype': 'markdown', 'markdown': {'content': txt}}}
        if len(key) == 64:                  # DingTalk len(key)=64
            request_data['url'] = f'https://oapi.dingtalk.com/robot/send?access_token={key}'
            request_data['json'] = {'msgtype': 'markdown', 'markdown': {'text': txt}}
        return self.http(request_data)

    def http_check_ssl(self, domains=None, key=None, le=None):
        """ check ssl domain expiration """
        domains = domains if domains else self.conf.get('check_ssl')
        key = key if key else self.conf.get('notice_key')
        le = le if le else self.conf.get('check_ssl_days')
        expires_txt, count = f'> ** check ssl domain length {len(domains)} **', 0
        if isinstance(domains, str): domains = [domains]
        for domain in set(domains):
            try:
                s = ssl.create_default_context().wrap_socket(socket.socket(), server_hostname=domain)
                s.connect((domain, 443))
                certs = s.getpeercert().get('notAfter')
                end_timestamp = parser.parse(certs).timestamp()
                days = int((end_timestamp - time.time()) / (3600 * 24))
                if days <= le:
                    count += 1
                    expires_txt += f'\n{count}、{days} days | {domain}'
            except:
                self.logs.error(f'connect error | {domain}')
        if not count: return self.logs.info(f'check ssl domain length {len(domains)} no expiration {domains}')
        self.logs.info(expires_txt)
        return self.http_notice(expires_txt, key)

    def http_filter_data(self, request_data, filter_path, filter_code, file_type=None):
        """ default filter data
        :param request_data:
        :param filter_path:
        :param filter_code:
        :param file_type:
        """
        filter_header = ['content-length', 'accept-encoding', 'host', 'accept', 'origin', 'referer', 'pragma',
                         'sec-ch-ua', 'connection', 'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
                         'accept-language', 'sec-ch-ua-mobile', 'sec-ch-ua-platform', 'postman-token',
                         'cache-control', 'x-requested-with', 'accept-encoding']
        response = request_data.get('response')
        if isinstance(response, str): response = {'ppl_response': response}
        if not file_type:
            # Filter interface, such as log out and log in again
            url = request_data.get('url')
            if not url: return {}
            host, path, query, uri = self.http_split_url(url)
            if not host: return {}
            if filter_path and path in filter_path: return {}
            request_data['host'] = host
            request_data['uri'] = uri
            request_data['path'] = path
            request_data['query'] = query
            # Whether the filter return parameter code meets the requirements
            if not response.get('ppl_response'):
                if filter_code:
                    for k, v in filter_code.items():
                        err_code, ret_code = True, response.get(k)
                        for i in v:
                            if ret_code == i: err_code = False
                        if err_code: return 0
        # headers:Delete unnecessary parameters
        origin_headers, headers = request_data.get('headers'), {}
        if isinstance(origin_headers, dict):
            for k, v in origin_headers.items():
                if k.lower() not in filter_header: headers[k] = v
        if isinstance(origin_headers, str):
            for i in origin_headers.split(','):
                i = i.split(': ')
                if len(i) > 1 and i[0].lower() not in filter_header: headers[i[0]] = i[1]
        request_data['headers'] = headers
        return request_data
