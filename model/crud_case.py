import urllib.parse
from model.models import *
from model.dbBase import *
from utils.jsonSchema import dumps


def db_insert_api(dict_data, db_model=None, db=None):
    db_model = db_model if db_model else PPlPlayback
    db = db if db else SessionLocal()
    # 先前需要处理的数据
    response, body = dict_data.get('response'), dict_data.get('body')
    host, uri = dict_data.get('host'), dict_data.get('uri')
    path, keys, dict_body = dict_data.get('path'), dict_data.get('keys'), body
    # 响应报错数据不写入：如果response=None 不写入
    if not response: return 0
    lower_keys = []
    if keys: lower_keys = keys
    else:
        # 如果为 data str 转 dict
        if isinstance(body, str):
            body = urllib.parse.unquote(body)
            if len(body) > 2: dict_body = dict([x.split('=', 1) for x in body.split('&')])
            else: dict_body = {}
        # 如果都没有 dict_body 那么拿 query 进行对比
        query = dict_data.get('query')
        if not dict_body: dict_body = query
        """ 因为有些参数区分大小写，不能改变原有值，可通过全小写进行对比 """
        if dict_body: lower_keys = [key.lower() for key in dict_body.keys()]
        lower_keys.sort()
        lower_keys = dumps(lower_keys)
    # 参数入库处理
    dict_data.pop('cookies', None)
    msg, domain = dict_data.get('msg'), dict_data.get('domain')
    api_name,method = dict_data.get('api_name'),dict_data.get('method')
    headers, collects = dict_data.get('headers'), dict_data.get('collects')
    curl, schema_ = dict_data.get('curl'), dict_data.get('schema_response')
    grade, gray = dict_data.get('grade'), dict_data.get('gray')
    assert_ = dict_data.get('assert_list')
    # SQL 查询是否有，如果用例是失败的，则覆盖更新原表：PPlPlayback
    if db_model == PPlFormal and msg != 'pass':
        db_model = PPlPlayback
        dict_data = {'response': response, 'msg': msg}
    select_sql = db.query(db_model).filter(db_model.host == host, db_model.path == path,
                                           db_model.gray == gray, db_model.keys == lower_keys)
    is_data = select_sql.first()
    if not is_data:
        # 查询不到，新增一条数据
        insert_ = db_model(msg=msg, domain=domain, host=host, curl=curl, method=method,
                           path=path, headers=headers, keys=lower_keys, api_name=api_name,
                           response=response, schema_response=schema_, grade=grade, uri=uri, gray=gray)
        if body: insert_.body = body
        if collects: insert_.collects = collects
        if assert_: insert_.assert_list = assert_
        db_insert(db, insert_, f'{host} | {path}')
    else:
        # 如果是None或通过的用例，则不再更新
        if msg is None or msg == 'pass' and is_data.msg == 'pass': return 0
        # 如果没有则pop掉，避免入口数据非null
        if not body: dict_data.pop('body', None)
        if not collects: dict_data.pop('collects', None)
        if not assert_: dict_data.pop('assert_list', None)
        # 查询到覆盖更新
        db_update(db, select_sql, dict_data, f'{host} | {path}')
    return db.close()


def db_select(host=None, domain='default', env=None, conf_type=None, db=None, db_model=None, gray=None):
    """
    :param host: host
    :param domain: domain
    :param env: env (test/beta)
    :param conf_type: config type
    :param db: db SessionLocal
    :param db_model: model class
    :param gray: AB test gray
    :return:
    """
    db = db if db else SessionLocal()
    db_model = db_model if db_model else PPlPlayback
    gray = gray if gray else 'gray'
    if not conf_type:
        # SQL 查询用例
        select_sql = db.query(db_model).filter(db_model.domain == domain, db_model.gray == gray,
                                               db_model.host == host, db_model.skip == 0)
        db_data = select_sql.order_by(desc('grade')).all()
    else:
        # SQL 查询配置文件
        select_sql = db.query(PPlConfig).filter(PPlConfig.domain == domain, PPlConfig.env == env)
        db_data = select_sql.first()
    return db_data
