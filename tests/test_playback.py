import allure
from model.crud_case import db_insert_api
from model.models import PPlFormal
from utils.httpRequest import Http
h = Http()


@allure.story("API流量回放:test_playback")
@allure.step("originRequest：{param}")
def test_playback(param):
    file_type = param.pop('file', None)
    h.http_main(param, print_=1, db_model=PPlFormal,
                db_obj_insert=db_insert_api, file=file_type)
