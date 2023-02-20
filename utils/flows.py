import random
from mitmdump import DumpMaster, Options
from mitmproxy.utils import human
from mitmproxy.http import HTTPFlow, HTTPResponse, flow as flows
from utils.playback import *


class PPLMock:

    def __init__(self, http_obj):
        self.h = http_obj
        self.logs = self.h.logs
        self.faker = self.h.faker
        self.conf = read_config()

    def cat_mock_load(self):
        """ Load mock*.json file """
        pwd, dict_mock = os.getcwd(), {}
        files = [os.path.join(pwd, file) for file in os.listdir(path=pwd) if 'mock' in file and '.json' in file]
        if not files: return self.logs.warning('not mock*.json no mock！')
        for file in files:
            dict_data = loads('', file)
            dict_mock.update(dict_data)
        return dict_mock

    def cat_mock_range(self, mock_response, record_mock_response=None):
        """ | for range crete object"""
        record_mock_response = record_mock_response if record_mock_response else mock_response
        str_mock_all_key = dumps(mock_response)
        if '|' in str_mock_all_key:
            for k, v in mock_response.items():
                old_key = k
                if '|' in k:
                    try:
                        paths = jsonpath(mock_response, f'$..{old_key}', 'PATH')
                        if paths: paths = paths[0][1:]
                        k = k.split('|')
                        new_key, new_value = k[0], ''
                        k = k[1].split('-')
                        if '' in k: k.remove('')
                        if len(k) > 1:
                            min_count = abs(int(k[0]))
                            max_count = abs(int(k[1]))
                            if min_count > max_count: min_count, max_count = max_count, min_count
                            count = random.randint(min_count, max_count)
                        else: count = abs(int(k[0]))
                        if isinstance(v, list):
                            new_value = []
                            for n in range(count): new_value.append(v[0])
                        if new_value: exec(f'mock_response{paths}=new_value')
                        mock_response.pop(old_key, None)
                        mock_response[new_key] = new_value
                    except: continue
                else: self.cat_mock_range(v, record_mock_response)
        return mock_response

    def cat_mock_faker(self, mock_response):
        """ Faker crete mock_response
        document：https://faker.readthedocs.io/en/master
        """
        if isinstance(mock_response, dict): mock_response = self.cat_mock_range(mock_response)
        str_mock_response = dumps(mock_response)
        keys = re.findall('\${(.+?)}', str_mock_response)
        for key in keys:
            try:
                if '(' in key and ')' in key:
                    value = eval(f'self.faker.{key}')
                    try:
                        if '.' in value: value = float(value)
                        else: value = int(value)
                    except: value = value
                else: value = eval(f'self.faker.{key}()')
            except: value = key
            if isinstance(value, (bool, int, float)):
                str_mock_response = str_mock_response.replace(('"${%s}"' % key), str(value).lower(), 1)
            else: str_mock_response = str_mock_response.replace(('${%s}' % key), str(value), 1)
        return loads(str_mock_response)

    def cat_mock_update_dict(self, mock_dict: dict, response_dict: dict):
        """ mock_dict --> update response_dict """
        try:
            for k, v2 in response_dict.items():
                v1 = mock_dict.pop(k, None)
                if isinstance(v1, dict) and isinstance(v2, dict): self.cat_mock_update_dict(v1, v2)
                if isinstance(v1, (bool, int, str, list, dict)) and not isinstance(v2, dict): response_dict[k] = v1
            response_dict.update(mock_dict)
        except: self.logs.error('update_dict error!')
        return response_dict

    def cat_mock_response(self, pretty_url, all_mock_dict):
        """ Read all mock*.json file --> Mock Response """
        if not all_mock_dict: return None, None
        host, path, query, uri = self.h.http_split_url(pretty_url)
        mock_data = all_mock_dict.get(path)
        if not mock_data: return None, path
        mock_data = self.cat_mock_faker(mock_data)
        str_mock_data = dumps(mock_data)
        self.logs.warning(f'mock response hit：{path} \nmock response：{str_mock_data}')
        return str_mock_data, path


class PPLFlow:

    def __init__(self, http_obj, host, port):
        http_obj.logs.warning(f'Proxy server listening at http://{host}:{port}')
        self.http_obj = http_obj
        self.h, self.p = None, None
        self.hosts, self.domain = None, None
        self.db_url, self.mode = None, None
        self.codes, self.mock = None, self.http_obj.conf.get('mock')
        self.replace, self.addr_domain = None, None
        self.skip, self.filter = None, None
        self.write_db, self.write, self.all_write = None, None, None
        self.lastMock = self.mock
        if self.mock == 'on': http_obj.logs.warning('loaded mock*.json match to will mock')
        elif self.mock != 'on': http_obj.logs.warning('mock not open')

    def init(self):
        self.h, self.p = PPLMock(self.http_obj), Playback(self.http_obj)
        self.hosts, self.domain = self.h.conf.get('hosts'), self.h.conf.get('domain', 'ppl')
        self.db_url, self.mode = self.h.conf.get('db_url'), self.h.conf.get('mode')
        self.codes, self.mock = self.h.conf.get('codes'), self.h.conf.get('mock')
        self.replace, self.addr_domain = self.h.conf.get('replace'), self.h.conf.get('addr_domain')
        self.skip, self.filter = self.h.conf.get('skip'), self.h.conf.get('filter')
        self.write_db, self.write, self.all_write = True, True, True
        if self.mock == 'on' and self.lastMock != self.mock: self.h.logs.warning('loaded mock*.json match to will mock')
        elif self.mock != 'on' and self.lastMock != self.mock: self.h.logs.warning('mock not open')
        self.lastMock = self.mock

    def request(self, flow: HTTPFlow):
        self.init()
        if flow.request.host in self.hosts:
            # pattern replace:request all (host headers path body cookie)
            if isinstance(self.replace, dict) and self.replace and flow.request.path not in self.filter:
                for pattern, value in self.replace.items():
                    count = flow.request.replace(pattern, value, flags=re.I)
                    if count > 0: self.all_write = False

    def response(self, flow: flows):
        # filter host and status_code in codes=[2xx, 3xx]
        if flow.request.host in self.hosts and str(flow.response.status_code)[0] in self.codes:
            url, path = flow.request.pretty_url, flow.request.path
            try:
                res_response = loads(flow.response.text)
                if 'filename=' in ''.join(flow.response.headers.values()):
                    res_response = base64.b64encode(flow.response.content).decode()
            except: res_response = 'response error: utf-8 codec can‘t decode byte'
            if self.mock == 'on':
                # Get mock data
                all_mock_dict = self.h.cat_mock_load()
                if all_mock_dict:
                    mock_data, path = self.h.cat_mock_response(url, all_mock_dict)
                    mock_data_dict = loads(mock_data)
                    # Send a reply from the proxy without sending any data to the remote server.
                    if self.mode == 'off' and mock_data:
                        # mock status_code default 200
                        mock_status_code = mock_data_dict.pop('status_code', 200)
                        # mock headers default {}
                        mock_headers = mock_data_dict.pop('headers', {"Content-Type": "application/json; charset=utf-8"})
                        flow.response = HTTPResponse.make(mock_status_code, dumps(mock_data_dict), mock_headers)
                    # Get remote server response
                    # Send any data to remote server for re simulation
                    if self.mode != 'off' and mock_data:
                        if isinstance(mock_data_dict, dict) and isinstance(res_response, dict):
                            str_mock_response = dumps(self.h.cat_mock_update_dict(mock_data_dict, res_response))
                            flow.response.set_text(str_mock_response)
            request_data, headers = {}, {}
            request_data['method'] = flow.request.method
            request_data['url'] = url
            for key, value in flow.request.headers.items():
                if key == 'cookie': key = 'Cookie'
                headers[key] = value
            request_data['headers'] = headers
            try:  # compatible with upload file: multipart/form-data
                if flow.request.multipart_form:
                    is_body = {}
                    file_name = re.findall('filename="(.*?)"', flow.request.text)
                    file_name = file_name[0] if file_name else 'default.png'
                    for k, v in flow.request.multipart_form.items():
                        k = k.decode()
                        if k == 'file': is_body[k] = [file_name, base64.b64encode(v).decode()]
                        else: is_body[k] = v.decode()
                else: is_body = loads(flow.request.content.decode('utf-8'))
            except: is_body = {}
            if is_body: request_data['body'] = is_body
            request_data['response'] = res_response
            # get ip domain?
            addr = human.format_address(flow.client_conn.address)
            if addr and ':' in addr: addr = addr.split(':')[0]
            else: addr = '127.0.0.1'
            domain = self.addr_domain.get(addr, self.domain)
            request_data['domain'] = domain
            request_data = self.p.app_env_gray(request_data)
            self.h.logs.info(dumps(request_data))
            # flow request_data write file
            if self.skip and path in self.skip: return 0
            if self.db_url and self.write_db and self.all_write:
                # todo write db
                is_write = self.p.app_write_db(request_data)
                if not is_write:
                    self.write_db = False
                    self.h.logs.error('connect sql error... flows close insert db')
                if is_write: self.write = False
            if self.write and self.all_write:
                file = f'./data/api-{time.strftime("%Y-%m-%d", time.localtime())}.txt'
                with open(file, 'a+', encoding='utf-8')as f: f.write(dumps(request_data) + '\n')
            self.all_write = True


def run(http_obj):
    """
    doc：https://docs.mitmproxy.org/stable/concepts-options
    """
    conf_port = http_obj.conf.get('listen_port')
    conf_host = http_obj.conf.get('listen_host')
    listen_port = 8888 if not conf_port else conf_port
    listen_host = '0.0.0.0' if not conf_host else conf_host
    opts = Options(listen_host=listen_host, listen_port=listen_port, termlog_verbosity='error')
    m = DumpMaster(opts)
    addons = [PPLFlow(http_obj, listen_host, listen_port)]
    m.addons.add(*addons)
    m.run()
