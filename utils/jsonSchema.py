import json
from jsonpath import jsonpath
from genson import SchemaBuilder
from jsonschema.validators import validate
from jsonschema.exceptions import ValidationError


def schema_create(data: dict):
    """ 生成 jsonschema """
    if isinstance(data, str):
        try:data = json.loads(data)
        except: return {'jsonschema': 'schema_create Error'}
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()


def schema_exp(response: dict, schema: dict):
    """ 对比 schema """
    if not response or not schema:
        return None
    if isinstance(response, str):
        try: response = json.loads(response)
        except: return f'JsonSchema校验不通过：Response Not Json Object'
    try:
        validate(instance=response, schema=schema)
        return f'pass'
    except ValidationError as e:
        return f'JsonSchema校验不通过：{e.message}'


def dumps(txt, beaut=0):
    """ json序列化：dict -> json """
    if isinstance(txt, str):txt = loads(txt)
    try:
        if beaut: txt = json.dumps(txt, sort_keys=True, indent=4, ensure_ascii=False)
        else: txt = json.dumps(txt, ensure_ascii=False)
    except: txt = txt
    return txt


def loads(txt: str):
    """ json反序列化：json -> dict """
    try: txt = json.loads(txt, encoding='UTF-8')
    except: txt = txt
    return txt


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
