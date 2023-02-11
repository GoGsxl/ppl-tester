from aliyun.log import LogClient
from utils.httpReq import *
from utils.public import read_config


class AliLog:
    # pip install -U aliyun-log-python-sdk

    def __init__(self, http_obj=None, log_name='monitor'):
        self.h = http_obj if http_obj else Http(log_name, lower_=False)
        config = read_config(logs=self.h.logs, lower_=False)
        self.monitor = config.get('monitor', {})
        self.key_id = config.get('key_id')
        self.key = config.get('key')
        self.proj = self.monitor.pop('proj')
        self.store = self.monitor.pop('store')
        self.endpoint = config.get('endpoint')
        if not self.key_id or not self.key or not self.proj or not self.store or not self.endpoint:
            self.h.logs.warning(f'config.ini monitor not configured or not dict：{self.monitor}')
            os._exit(0)
        self.client = LogClient(self.endpoint, self.key_id, self.key)
        self.second = self.monitor.pop('second', 7200)
        self.filter_msg = self.monitor.pop('filter_msg', [])
        self.str_data, self.start_time = '', ''
        self.aliLog = config.get('alilog', {})

    def ali_get_data(self, query=None):
        # query:ali_get_data
        if not query: return self.h.logs.warning(f'ali_get query is none.')
        to_time = time.time()
        from_time = to_time - self.second
        dict_resp = self.client.get_log(self.proj, self.store, from_time, to_time, size=-1, query=query).get_body()
        return dict_resp

    def ali_query(self, query=None):
        # config not or and word
        if not isinstance(self.monitor, dict): return self.h.logs.error(f'ini monitor not dict')
        service, query_list = [], []
        for serve, query_ in self.monitor.items():
            if not isinstance(query_, dict): return self.h.logs.error(f'monitor query not dict ')
            service.append(serve)
            not_word, and_word = query_.get('not_word'), query_.get('and_word')
            if not not_word and not and_word: self.h.logs.warning(f'monitor query word is none.')
            if isinstance(not_word, str): not_word = f'not {not_word}'
            if isinstance(and_word, str): and_word = f'and {and_word}'
            if isinstance(not_word, list): not_word = f'not {" not ".join(not_word)} '
            if isinstance(and_word, list): and_word = f'and {" and ".join(and_word)} '
            query = query if query else f'* and __tag__:_container_name_: {serve} {and_word} {not_word}'
            query_list.append(query)
        return service, query_list

    def ali_get_error(self):
        # get error logs notice
        service, query_list = self.ali_query()
        err_txt, count, push_count, err_msg_list = '', 1, 1, self.filter_msg
        for serve, query in zip(service, query_list):
            logs = self.ali_get_data(query)
            self.h.logs.info(f'Select {self.proj}_{self.store}_{query} len data is:{len(logs)}')
            for log in logs:
                self.str_data = log.get('data')
                trace_id = log.get('trace.id')
                gray = log.get('__tag__:_namespace_')
                if gray == 'default': gray = 'default_env'
                start_time = self.ali_format_time(log.get('startTime'))
                if not self.str_data: continue
                err_msg = self.ali_re(r'err: Error: (.*?)\n', ('err_msg ', ''))
                filter_err_msg = err_msg.strip('\n').split(': ')[1] if err_msg else '无'
                if err_msg in err_msg_list or filter_err_msg in err_msg_list: continue
                org = self.ali_re(r'"customer":\["(.*?)"]', ('customer ', f' | <font color="info">{gray}</font>'))
                request = self.ali_re(r'request: (.*?) metadata', ('request  ', ''))
                body = self.ali_re(r'api request: (.*?)}', ('body      ', '}')).replace('*', r'\*')
                proto = self.ali_re(r'grpc invoke: (.*?)\ds', ('proto     ', 's'))
                err_msg_list.append(filter_err_msg)
                txt = f'> **{count}-serve ：{serve}**\n{org}trace_id  ：{trace_id}\n'
                txt += f'{proto}{request}{body}{err_msg}time       ：{start_time}'
                err_txt += f'{txt}\n\n'
                count += 1
                push_count += 1
                self.h.logs.info(f'\n{txt}')
                if push_count > 5:
                    err_txt += f'> ** PPL err log **：{time.strftime("%Y-%m-%d %H:%M:%S")}'
                    self.h.logs.warning(self.h.http_notice(err_txt, self.h.conf.get('notice_key')))
                    err_txt, push_count = '', 1
                    continue
        if not err_txt: return self.h.logs.info(f'No notification without error')
        err_txt += f'> ** PPL err log **：{time.strftime("%Y-%m-%d %H:%M:%S")}'
        return self.h.logs.warning(self.h.http_notice(err_txt, self.h.conf.get('notice_key')))

    def ali_get_request(self):
        # get api request and response
        request_data = []
        self.store = self.aliLog.pop('store', None)
        self.second = self.aliLog.pop('second', 7200)
        gray = self.aliLog.pop('gray', 'gray')
        query = '* and __tag__:_container_name_: '
        for serve, v in self.aliLog.items():
            query += f'{serve} {v.get("query", "")}'
            add_path = v.get('path', '/api')
            host = v.get('host', None)
            headers = v.get('headers', {})
            if not host:
                self.h.logs.warning(f'serve host not configured')
                continue
            self.h.logs.info(f'AliLog get query: {query}')
            for i in self.ali_get_data(query):
                data = loads(i.get('data', ''))
                if isinstance(data, dict):
                    method = data.get('method', 'GET')
                    request_data.append({'method': method,
                                         'url': f'{host + add_path}{data.get("url", "")}',
                                         'headers': headers,
                                         'body': data.get('request') if method == 'POST' else None,
                                         'response': data.get('response'),
                                         'domain': self.h.conf.get('domain', 'ppl'),
                                         'gray': gray})
        return request_data

    def ali_format_time(self, start_time=''):
        # 2022-11-30T17:32:25.417Z -> 2022-11-30 17+8:32:25
        start_time = start_time[:-5] if start_time else self.start_time[:-5]
        re_string = re.findall('T(.*?):', start_time)
        number, old_string = '', ''
        if re_string:
            old_string = re_string[0]
            number = int(re_string[0]) + 8
        if number >= 24: number = f'0{number - 24}'
        return start_time.replace(f'T{old_string}:', f' {number}:')

    def ali_re(self, pattern, add_str=('', ''), string=None, flags=re.I):
        # re
        string = string if string else self.str_data
        re_str_data = re.findall(pattern, string, flags)
        if not re_str_data:
            if 'demo而已' in add_str[0]:
                re_str_data = re.findall(r'demo而已', string, flags)
                if re_str_data: re_str_data = [re_str_data[0] + 'demo而已']
                else: self.h.logs.warning(f'{string}')
            else: self.h.logs.error(f'{self.str_data}')
            if not re_str_data: return f'{add_str[0]}：无{add_str[1]}\n'
        return f'{add_str[0]}：{re_str_data[0]+add_str[1]}\n'
