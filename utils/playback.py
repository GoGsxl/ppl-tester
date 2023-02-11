import urllib.parse, sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from utils.httpReq import *
from utils.monitor import AliLog
from sqlalchemy import *
from datetime import datetime


def get_db_engine(db_url=None, new=False, key='db_url'):
    if new: key = 'new_db_url'
    db_url = db_url if db_url else read_config(db_url=True).get(key, '')
    if 'mysql' in db_url:
        db_engine = create_engine(db_url, json_serializer=dumps, pool_size=0, max_overflow=-1)
    else:
        if not os.path.exists(db_url) and not new:
            if not db_url: db_url = os.path.join(os.getcwd(), 'data', 'tester.db')
        db_engine = create_engine(f'sqlite:///{db_url}', json_serializer=dumps)
    return db_engine, db_url


engine, get_db_url = get_db_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def db_create_all(new_Base=Base, new=False, db_url=None):
    new_engine, new_db_url = get_db_engine(new=new)
    if db_url: new_engine, new_db_url = get_db_engine(db_url=db_url, new=new)
    back_db_url, is_db = db_url, False
    try:
        # new mysql database tester
        new_db_url = db_url if db_url else new_db_url
        if not new_db_url: return False, 'Not new_db_url', new_engine
        str_split, port = new_db_url.split(':'), ''
        if '/' in str_split[-1]:
            port = str_split[-1].split('/')
            if port: port = port[0]
        str_split[-1] = port
        db_url = ':'.join(str_split)
        try:
            new_Base.metadata.create_all(new_engine)
            is_db = True
        except:
            new_engine, new_db_url = get_db_engine(db_url, new)
            new_engine.execute('commit')
            sql_ = 'CREATE DATABASE IF NOT EXISTS tester DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_unicode_ci'
            new_engine.execute(sql_)
            new_engine.execute("USE tester")
            new_Base.metadata.create_all(new_engine)
            is_db = True
        back_db_url = db_url
        return is_db, 'succeeded', new_engine
    except:
        return is_db, f'connect db error {back_db_url}', new_engine


class PPlConfig(Base):
    __tablename__ = 'ppl_config'
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(32), comment="domain")
    env = Column(String(32), comment="env")
    Tester = Column(JSON, comment="testcases config")


class PPlPlayback(Base):
    __tablename__ = 'ppl_playback'
    id = Column(Integer, primary_key=True, index=True)
    msg = Column(TEXT, comment='assertion results')
    domain = Column(String(32), comment="domain", index=True)
    gray = Column(String(32), comment="AB gray cases", index=True)
    api_name = Column(String(64), comment='api name')
    method = Column(String(32), comment='request type GET/POST...')
    host = Column(String(255), comment='host ip', index=True)
    path = Column(String(255), comment='api path', index=True)
    uri = Column(TEXT, comment='path + query')
    headers = Column(JSON, comment='request headers')
    body = Column(JSON, comment='request  body(json or data or en_base64)')
    keys = Column(TEXT, comment='keys, compare whether the use case is repeated')
    response = Column(JSON, comment='response')
    schema_response = Column(JSON, comment='response json schema')
    grade = Column(Integer, comment="cases level")
    create_time = Column(DateTime, default=datetime.now, comment='create time')
    update_time = Column(DateTime, onupdate=datetime.now, default=datetime.now, comment='update time')
    curl = Column(TEXT, comment='curl')
    skip = Column(Integer, default=0, comment='skip cases:1')
    collects = Column(JSON, comment='collects')
    assert_list = Column(JSON, comment="assert list")


class Playback:

    def __init__(self, http_obj, re_list=[]):
        self.H = http_obj
        self.logs = self.H.logs
        self.db = SessionLocal()
        self.re_list = re_list if re_list else self.H.conf.get('gray')
        self.variables = {}
        self.filter_path = []
        self.filter_code = {}
        self.gray = None

    def app_env_gray(self, request_data: dict):
        """ AB testcases method
        gray：mark AB testcases env
        request_data: flows request and response
        re_txt：re match word
        """
        is_gray = request_data.get('gray')
        if is_gray and is_gray != 'gray': return request_data
        request_data['gray'] = 'gray'
        if not self.re_list: return request_data
        url, gray = request_data.get('url', ''), None
        headers = request_data.get('headers', {})
        # url get gray
        for re_str in self.re_list:
            url_gray1 = re.findall(f'{re_str}=(.+?)&', url, flags=re.IGNORECASE)
            url_gray2 = re.findall(f'{re_str}=(.+?)$', url, flags=re.IGNORECASE)
            if url_gray1: gray = url_gray1[0]
            if url_gray2 and not url_gray1 or len(url_gray1) > 12: gray = url_gray2[0]
            if gray:
                request_data['gray'] = gray
                return request_data
        # headers get gray
        if isinstance(headers, dict):
            str_cookies = headers.get('Cookie', '') if headers.get('Cookie') else headers.get('cookie', '')
            try:
                for re_str in self.re_list:
                    env_gray1 = re.findall(f'{re_str}=(.+?);', str_cookies, flags=re.IGNORECASE)
                    env_gray2 = re.findall(f' {re_str}=(.+?);', str_cookies, flags=re.IGNORECASE)
                    env_gray3 = re.findall(f'{re_str}=(.+?)&', str_cookies, flags=re.IGNORECASE)
                    env_gray4 = re.findall(f'{re_str}=(.+?)$', str_cookies, flags=re.IGNORECASE)
                    if not gray and env_gray1: gray = env_gray1[0]
                    if not gray and env_gray2: gray = env_gray2[0]
                    if not gray and env_gray3: gray = env_gray3[0]
                    if not gray and env_gray4: gray = env_gray4[0]
                    if ',' in gray: gray = gray.split(',')[0] if gray.split(',') else gray
                    if ';' in gray: gray = gray.split(';')[0] if gray.split(';') else gray
                    if gray: request_data['gray'] = gray
            except: pass
        if gray == 'gray' and self.gray: request_data['gray'] = self.gray
        return request_data

    def app_write_db(self, request_data):
        if isinstance(request_data, str):
            old_data = re.findall('body":"(.*?)","response', request_data)
            if old_data: request_data = loads(request_data.replace(f'"{old_data[0]}"', old_data[0]))
        if isinstance(request_data, dict):
            # filter request_data
            request_data = self.H.http_filter_data(request_data, self.filter_path, self.filter_code)
            if not request_data or not isinstance(request_data, dict): return 1
            request_data = self.H.http_default_data(request_data)
            request_data = self.app_env_gray(request_data)
            # insert database
            return self.db_insert(request_data)
        else:
            self.logs.error(f'Not a dictionary request_data:{dumps(request_data)}')
            return 1

    def app_ali_for(self, tester={}):
        """ AliLog insert db  """
        # SQL query config
        tester = tester if tester else self.db_select(conf_type=1).Tester
        if not tester or not isinstance(tester, dict): self.pytest_exit('ini or db tester not config or not dict')
        request_data = AliLog(self.H).ali_get_request()
        self.logs.info(f'【AliLog】begin insert api count：{len(request_data)}')
        # db filter config
        self.filter_path = tester.get('filter_path')
        self.filter_code = tester.get('filter_code')
        for data in request_data: self.app_write_db(data)
        return f'【AliLog】end insert api count：{len(request_data)}'

    def app_txt_for(self, file=None, dir_path=None, tester={}):
        """ analysis flows file
        :param file:
        :param dir_path:
        :param tester:
        :return: result
        """
        # SQL query config
        count, tester = 0, tester if tester else self.db_select(conf_type=1).Tester
        if not tester or not isinstance(tester, dict): self.pytest_exit('ini or db tester not config or not dict')
        # db filter config
        self.filter_path, self.filter_code = tester.get('filter_path'), tester.get('filter_code')
        file_dir = os.path.join(os.getcwd(), 'data')
        if dir_path: file_dir = dir_path
        file_list = [os.path.join(file_dir, file)] if file else [os.path.join(file_dir, file_txt) for file_txt in
                                                                 os.listdir(path=file_dir) if '.txt' in file_txt]
        file_list.reverse()
        for file in file_list:
            if not os.path.isfile(file): return self.logs.error(f'[ERROR]method app_txt_for() not file：{file}')
            f = open(file, encoding='utf-8')
            while 1:
                line = f.readline()
                if not line: break
                request_data: dict = loads(line)
                self.app_write_db(request_data)
                count += 1
            f.close()
        msg = f'【cases insert】finish: {count} | {file_list}'
        return msg

    def app_pytest_txt(self, file=''):
        """ flows file pytest testcases """
        all_data, paths, is_file = [], [], False
        file_dir = os.path.join(os.path.abspath(os.path.join(os.getcwd(), "")), 'data')
        file_path = os.path.join(file_dir, file) if file else file_dir
        if len(str(file)) > 20 or str(file).count('.') > 1: file_path = file
        file_all = [os.path.join(file_dir, file_txt) for file_txt in os.listdir(path=file_dir) if '.txt' in file_txt]
        if os.path.isfile(file_path): is_file = True
        file_list = [file_path] if is_file else file_all
        for file in file_list:
            if not os.path.isfile(file): return self.H.http_notice(f'[ERROR]method app_pytest_txt() not file：{file}')
            f = open(file, encoding='utf-8')
            while 1:
                line = f.readline()
                request_data: dict = loads(line)
                if isinstance(request_data, dict):
                    if request_data.get('response') is None: continue
                    request_data['file'] = 1
                    request_data = self.H.http_filter_data(request_data, self.filter_path, self.filter_code, True)
                    if not request_data: continue
                    all_data.append(request_data)
                    paths.append(request_data.get('url'))
                else: break
            f.close()
        return all_data, paths, file_list

    def db_commit(self, sql_, modify=False, select_obj=None, mark='', db=None):
        rep, db = 0, db if db else self.db
        try:   # update
            if modify and select_obj:
                select_obj.update(sql_)
                db.commit()
                return 1
            db.add(sql_)
            db.commit()
            db.refresh(sql_)
            rep = 1
        except: self.logs.error(f'Error db_commit update={modify} {mark}：\n{traceback.format_exc()}')
        return rep

    def db_insert(self, dict_data, db=None):
        db = db if db else self.db
        # Process data first
        response, body = dict_data.get('response'), dict_data.get('body')
        host, uri = dict_data.get('host'), dict_data.get('uri')
        path, keys, dict_body = dict_data.get('path'), dict_data.get('keys'), body
        # not response return
        if not response: return 1
        lower_keys = []
        if keys: lower_keys = keys
        else:
            # data str -> dict
            if isinstance(body, str):
                body = urllib.parse.unquote(body)
                if len(body) > 2:  dict_body = dict([x.split('=', 1) for x in body.split('&')])
                else: dict_body = {}
            # not dict_body but query
            query = dict_data.get('query')
            if not dict_body: dict_body = query
            """ Lowercase comparison """
            if dict_body: lower_keys = [key.lower() for key in dict_body.keys()]
            lower_keys.sort()
            lower_keys = dumps(lower_keys)
        dict_data.pop('cookies', None)
        msg, domain = dict_data.get('msg'), dict_data.get('domain')
        api_name, method = dict_data.get('api_name'), dict_data.get('method')
        headers, collects = dict_data.get('headers'), dict_data.get('collects')
        curl, schema_ = dict_data.get('curl'), dict_data.get('schema_response')
        grade, gray = dict_data.get('grade'), dict_data.get('gray')
        assert_ = dict_data.get('assert_list')
        # SQL query
        select_sql = db.query(PPlPlayback).filter(PPlPlayback.host == host, PPlPlayback.path == path,
                                                  PPlPlayback.gray == gray, PPlPlayback.keys == lower_keys)
        is_data = select_sql.first()
        if not is_data:
            # Unable to query, add a new piece of data
            insert_ = PPlPlayback(msg=msg, domain=domain, host=host, curl=curl, method=method,
                                  path=path, headers=headers, keys=lower_keys, api_name=api_name,
                                  response=response, schema_response=schema_, grade=grade, uri=uri, gray=gray)
            if body: insert_.body = body
            if collects: insert_.collects = collects
            if assert_: insert_.assert_list = assert_
            self.db_commit(insert_, mark=f'{host} | {path}', db=db)
        else:
            # If it is None or passed use case, it will not be updated
            if msg is None or msg == 'pass' and is_data.msg == 'pass': return 1
            # If not, pop it to avoid non-null entry data
            if not body: dict_data.pop('body', None)
            if not collects: dict_data.pop('collects', None)
            if not assert_: dict_data.pop('assert_list', None)
            # Overwrite update found
            self.db_commit(dict_data, True, select_sql, f'{host} | {path}', db=db)
        db.close()
        return 1

    def db_select(self, host=None, domain='default', env=None, conf_type=None, model=None, gray=None, db=None):
        """
        :param host: host
        :param domain: domain
        :param env: env (test/beta)
        :param conf_type: config type
        :param model: model class
        :param gray: AB utils gray
        :param db:
        :return:
        """
        db = db if db else self.db if self.db else SessionLocal()
        model = model if model else PPlPlayback
        gray = gray if gray else 'gray'
        if domain == 'default' and not env and not conf_type:
            db_data = db.query(model).all()
        elif not conf_type:  # SQL query cases
            select_sql = db.query(model).filter(model.domain == domain, model.gray == gray,
                                                model.host == host, model.skip == 0)
            db_data = select_sql.order_by(desc('grade')).all()
        else:  # SQL query config
            select_sql = db.query(PPlConfig).filter(PPlConfig.domain == domain, PPlConfig.env == env)
            db_data = select_sql.first()
        return db_data

    def db_move(self, move):
        """ move old data --> new database"""
        old_data = self.db_select()
        if not old_data: return 'exit:old db data is none', 0
        # new db
        if move in [1, '1', 'true']: res, c_msg, c_engine = db_create_all(new=True)
        else: res, c_msg, c_engine = db_create_all(new=True, db_url=move)
        if not res: return c_msg, 0
        new_SessionLocal = sessionmaker(bind=c_engine, autocommit=False, autoflush=False)
        new_db = new_SessionLocal()
        pop_list = self.H.conf.get('db_pop_move_list', ['_sa_instance_state', 'create_time', 'update_time'])
        for d in old_data:
            dict_data = d.__dict__
            for i in pop_list: dict_data.pop(i, None)
            self.db_insert(dict_data, new_db)
        return c_msg, len(old_data)

    @staticmethod
    def db_is_none(data):
        return_data = None
        if data:
            if isinstance(data, dict): return_data = dumps(data)
            else: return_data = data
        return return_data

    def pytest_get_data(self, param, tester, domain):
        """ get testcases
        :param param: param
        :param tester: ini or db tester
        :param domain: domain
        """
        tester = tester if isinstance(tester, dict) else tester.Tester
        add_replace_dict, replace_dict, cookie, open_header = {}, {}, {}, {}
        # todo Delete if the field adding program cannot be used
        db_pop = ['id', 'curl', '_sa_instance_state', 'create_time', 'update_time']
        db_pop = self.H.conf.get('db_pop_play_list', db_pop)
        for k, v in param.items(): add_replace_dict[k] = v
        env_host = add_replace_dict.pop('host', None)
        testers, db_all_obj, cases, paths, hosts, gray = tester.get('Tester'), [], [], [], [], tester.get('gray')
        for test in testers:
            for host, value in test.items():
                hosts.append(host)
                db_data = self.db_select(host, domain, gray=gray)
                if not db_data:
                    self.logs.info(f'The query data is empty：{host}')
                    break
                # open api
                if value.get('Authorization'):
                    Authorization = value.pop('Authorization', None)
                    key = value.pop('key', None)
                    secret = value.pop('secret', None)
                    if not key or not secret:
                        self.logs.info(f'The open api (key,secret) is empty：{host}')
                        break
                    token = Authorization + jwt_encode(secret, key)
                    open_header = {'Authorization': token}
                else:
                    # setup get token or cookies
                    collects = value.pop('collects', None)
                    if value:
                        value['url'] = host + value['url']
                        status_code, response, result = self.H.http(value)
                        self.logs.info(f'--->：host：{host},Login results：{response}')
                        cookie = result.cookies.get_dict()
                        replace_dict = self.H.http_collect(response, collects, result)
                        replace_dict.update(add_replace_dict)
                for db in db_data:
                    # join testcases
                    dict_data, path = db.__dict__, db.path
                    for i in db_pop: dict_data.pop(i, None)
                    if db.api_name: path = f'{db.api_name}_{path}'
                    if add_replace_dict:
                        for k, v in add_replace_dict.items():
                            if not isinstance(v, str): continue
                            db.headers[k] = v
                        if cookie: add_replace_dict.update(cookie)
                        db.headers['Cookie'] = ''.join([f'{k}={v};' for k, v in add_replace_dict.items()])
                    if open_header: db.headers.update(open_header)
                    res_host = db.host
                    if env_host: res_host = env_host
                    request_data = {'headers': db.headers, 'url': res_host + db.uri, 'body': db.body}
                    request_data = self.H.http_replace(replace_dict, request_data)
                    dict_data.update(request_data)
                    paths.append(path)
                    cases.append(dict_data)
        if not cases: self.pytest_exit(f'No test cases exit...')
        return cases, paths, hosts

    def pytest_run(self, variables):
        file_path = variables.pop('file', None)
        play = str(variables.pop('play', 1))
        param = loads(variables.pop('param', {}))
        tester = loads(variables.pop('tester', {}))
        if not isinstance(param, dict): param = {}
        # Init database table structure
        init = variables.pop('init', 'false')
        if init in ['1', 'true']:
            db_create_all()
            self.pytest_exit('New table structure succeeded')
        # move old db data -> new db data
        move = variables.pop('move', None)
        if move:
            c_msg, c_count = self.db_move(move)
            self.pytest_exit(f'Move old db data -> new db data: count={c_count} | [{c_msg}]')
        # todo play=2：playback txt
        if play == '2' or file_path:
            # playback
            self.logs.info(f'play={play} read txt playback cases {file_path if file_path else "default"}')
            all_data, paths, file_list = self.app_pytest_txt(file_path)
            # write environment.properties file
            txt = f'file_list={file_list}\nexplain=This is the read file use case test\n'
            txt += 'Author=PPL\nBlog=https://blog.csdn.net/qq_42675140'
        # todo play=0：read txt insert db
        elif play == '0':
            proj_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            msg = self.app_txt_for(dir_path=os.path.join(proj_path, 'data'), tester=tester)
            return self.pytest_exit(msg)
        # todo play=3：read ali log insert db
        elif play == '3':
            msg = self.app_ali_for(tester=tester)
            return self.pytest_exit(msg, info=True)
        # todo read db cases pytest test insert db
        else:
            self.logs.info(f'play={play} read db test cases')
            # split env use db query config
            env_list = variables.pop('env', 'ppl,test').split(',')
            domain, env, play = env_list[0], env_list[1], None
            if not tester: tester = self.db_select(domain=domain, env=env, conf_type=1)
            if not tester: return self.pytest_exit('Not ini or db env config')
            # get db testcases
            all_data, paths, hosts = self.pytest_get_data(param, tester, domain)
            # write environment.properties file
            txt = f'Tested={domain}-{env}\nHost={hosts}\nparam={dumps(param)}\n'
            txt += 'Author=PPL\nBlog=https://blog.csdn.net/qq_42675140'
        if not all_data: self.pytest_exit(f'No executable use case. play={play}')
        with open('reports/report/environment.properties', 'w')as f: f.write(txt)
        case_count = variables.pop('count', None)
        if case_count:
            try: case_count = int(case_count)
            except: case_count = 1
            if case_count < 1: case_count = 1
            if len(all_data) >= case_count:
                all_data = all_data[:case_count]
                paths = paths[:case_count]
        return all_data, paths

    def pytest_exit(self, txt, out=True, info=False):
        origin_txt = txt
        txt = f'-----------------> {txt} <-----------------'
        if out:
            if info: self.logs.info(origin_txt)
            else: self.logs.warning(txt)
            time.sleep(0.2)
            return os._exit(0)
        return self.logs.warning(txt)

    def pytest_report_notice(self, argv=None, build_url=None, domain=None, env=None, param={}, key=None):
        """ python ppl.py n %BUILD_URL% %domain% %env% %param% %key% """
        argv = argv if argv else sys.argv[1:]
        self.logs.info(f'The number of custom parameters is：{type(argv)} -->{argv}')
        if len(argv) < 5: self.pytest_exit('Missing param：$build_url $domain $env $param $key')
        build_url = build_url if build_url else argv[0]
        domain, env = domain if domain else argv[1], env if env else argv[2]
        param, key = param if param else loads(argv[3]), key if key else argv[4]
        txt = '> **Http playback report**\n'
        try:
            # Get total, failure, success
            count_url = f'{build_url}/allure/widgets/summary.json'
            status_code, response, result = self.H.http({'method': 'GET', 'url': count_url})
            statistic = response.get('statistic')
            total, passed, failed = statistic.get('total'), statistic.get('passed'), statistic.get('failed')
            # Get tested domain name
            env_value_url = f'{build_url}/allure/widgets/environment.json'
            status_code, response, result = self.H.http({'method': 'GET', 'url': env_value_url})
            test_host = 'host   ：'
            for i in response:
                if not i: break
                if i.get('name') == 'Host':
                    test_host += i.get('values')[0].replace('\'', '')
                    test_host = test_host.replace(', ', '\nhost   ：').replace('[', '').replace(']', '')
            txt += f'param：{dumps(param) if isinstance(param, dict) else param}\n{test_host}\n'
            txt += f'env    ：**{domain}-{env}**\ntotal   ：{total}\nsuccess：<font color="info">{passed}</font>\n'
            txt += f'failure  ：<font color="comment">{failed}</font>\n[view report]({build_url}/allure)'
            status_code, response, result = self.H.http_notice(txt, key=key)
            return self.logs.info(f'push results: {response} \npush content: {txt}')
        except: self.logs.error(f'Push failed Please confirm "build_url": {build_url}')
