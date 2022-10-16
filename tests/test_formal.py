import allure
from model.models import PPlPlayback
from model.crud_case import db_insert_api
from utils.httpRequest import Http
h = Http()


@allure.story("API流量回放:test_formal")
@allure.step("originRequest：{param}")
def test_formal(param):
    replace_dict = param.pop('replace_dict', None)
    file_type = param.pop('file', None)
    if replace_dict: h.http_variable.update(replace_dict)
    h.http_main(param, print_=1, db_model=PPlPlayback,
                db_obj_insert=db_insert_api, file=file_type)
