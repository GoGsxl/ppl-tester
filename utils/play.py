import allure


@allure.story("Api playback:play.py")
@allure.step("originRequest：{param}")
def test_play(param: dict, obj):
    is_file = param.pop('file', None)
    obj[0].http_main(param, True, obj[1].db_insert, is_file)
