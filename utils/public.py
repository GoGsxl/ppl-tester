import os, json, time, jwt, configparser
from loguru import logger
from jsonpath import jsonpath
from genson import SchemaBuilder
from jsonschema.validators import validate
from jsonschema.exceptions import ValidationError

ppl_text = """
..................... Welcome PPL-Tester ......................
.                                                             .
.        ************     ************     ****               .
.        ***  V   ***     ***  V   ***     ****               .
.        ***  1   ***     ***  1   ***     ****               .
.        ************     ************     ****               .
.        ****             ****             ****               .
.        ****             ****             ****               .
.        ****             ****             *************      .
.        ****             ****             *************      .
...............................................................
"""


def ppl_log(write=False, name=None):
    """ return: logger """
    if write:
        name = name + '_{time:YYYY-MM-DD}.log' if name else '{time:YYYY-MM-DD}.log'
        logger.add(f'./data/{name}', rotation='100MB', level='INFO', enqueue=True,
                   format='{time:YYYY-MM-DD HH:mm} | {level} | {module}:{function} | {line} {message}', encoding='UTF-8')
    return logger


def dumps(txt, beaut=0, file=None, logs=None):
    """ dict -> json = if json else txt """
    try:
        if beaut: txt = json.dumps(txt, sort_keys=True, indent=4, ensure_ascii=False)
        else:
            txt = json.dumps(txt, ensure_ascii=False)
            try:
                if file:
                    with open(file, encoding='UTF-8')as f: json.dump(txt, f)
            except:
                logs = logs if logs else ppl_log()
                logs.error(f'dump file error：{file}')
    except: txt = txt
    return txt


def loads(txt, file=None, logs=None, lower_=False):
    """ json -> dict = if dict else txt """
    try:
        if file:
            logs = logs if logs else ppl_log()
            if not os.path.exists(file): logs.warning(f'file non-existent：{file}')
            with open(file, encoding='utf-8')as f:
                try:
                    txt = json.load(f)
                    if not txt: logs.warning(f'file non-existent：{file}')
                except: logs.error(f'load json file error：{file} please check the format')
        else: txt = json.loads(txt, encoding='UTF-8')
    except:
        txt = txt
        if lower_: txt = txt.lower()
    return txt


def read_config(file=None, logs=None, lower_=True, db_url=False):
    """ Read config.ini """
    config_file = os.path.join(os.getcwd(), 'config.ini')
    file = file if file else config_file
    if not os.path.exists(file):
        logs = logs if logs else ppl_log()
        logs.error(f'file non-existent：{file}')
        return {}
    config = configparser.RawConfigParser()
    config.read(file, encoding="utf-8")
    config_dict, db_dict = {}, {}
    for section, _ in config.items():
        if section == 'DEFAULT': continue
        for option in config.options(section):
            value = config.get(section, option)
            if option in 'db_url' and db_url:
                db_dict[option] = value
                if len(db_dict) == 2: return db_dict
            if ',' in value and '{' not in value: value = value.split(',')
            else:
                value = loads(value, lower_=lower_)
                if '{' in str(value) and isinstance(value, str): value = {}
            config_dict[option] = value
    return config_dict


def schema_create(data: dict):
    """ create jsonschema """
    if isinstance(data, str):
        try:data = json.loads(data)
        except: return {'jsonschema': 'schema_create Error'}
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()


def schema_exp(response: dict, schema: dict):
    """ contrast schema """
    if not response or not schema: return None
    if isinstance(response, str):
        try: response = json.loads(response)
        except: return f'JsonSchema verification failed：Response Not Json Object'
    try:
        validate(instance=response, schema=schema)
        return 'pass'
    except ValidationError as e:
        return f'JsonSchema verification failed：{e.message}'


def json_path(data: dict, key, number=None, all_type=False):
    value = jsonpath(data, f'$..{key}')
    if all_type: return value
    if value:
        if isinstance(number, int):
            number -= 1
            value.sort()
            if number > len(value)-1: return value[-1]
            return value[number]
        value = value[0]
        if isinstance(value, list): value = value[0]
    return value


def jwt_encode(secret, key=None, payload={}):
    """
    :param secret: appSecret
    :param key: appKey
    :param payload:
    :return: encode
    """
    default_payload = {
        "exp": int(time.time()) + 7200,
        "iss": key
    }
    payload = payload if payload else default_payload
    encode = jwt.encode(payload, key=secret)
    return encode
