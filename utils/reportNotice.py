import os, sys
from httpRequest import *
sys.path.append(os.path.dirname(os.getcwd()))
h = Http()


def report_notice(build_url=None, domain='default', env='test', param={}, key=None):
    build_url = build_url if build_url else 'https://blog.csdn.net/qq_42675140'
    txt = '> **http流量回放-测试报告**\n'
    # 获取总数、失败、成功
    count_url = f'{build_url}/allure/widgets/summary.json'
    status_code, response, cookies = h.http({'method': 'GET', 'url': count_url})
    statistic = response.get('statistic')
    total, passed, failed = statistic.get('total'), statistic.get('passed'), statistic.get('failed')
    # 被测域名获取
    env_value_url = f'{build_url}/allure/widgets/environment.json'
    status_code, response, cookies = h.http({'method': 'GET', 'url': env_value_url})
    test_host = '被测域名：'
    for i in response:
        if not i: break
        if i.get('name') == 'Host':
            test_host += i.get('values')[0].replace('\'', '')
            test_host = test_host.replace(', ', '\n被测域名：').replace('[', '').replace(']', '')
    txt += f'附加参数：{dumps(param)}\n{test_host}\n被测领域：**{domain}-{env}**\n测试总数：{total}'
    txt += f'\n测试通过：<font color="info">{passed}</font>\n测试失败：<font color="comment">{failed}</font>\n'
    # 报告链接
    txt += f'[查看报告]({build_url}/allure)'
    new_txt = {'markdown': {'content': txt}, 'msgtype': 'markdown'}
    status_code, response, cookies = h.http_notice(new_txt, key=key)
    return response


if __name__ == '__main__':
    import sys, json
    argv = sys.argv[1:]
    print(f'自定义参数个数为：{len(argv)} -->{argv}')
    if len(argv) < 5:
        print('Error 参数缺少,格式为：python reportNotice.py build_url domain env param key')
        exit(0)
    result = report_notice(argv[0], argv[1], argv[2], json.loads(argv[3]), argv[4])
    print('请求成功：', result)
    """ Windows 执行配置：
    1、api-playback
        cd tests
        pytest --env=%domain%,%env% --param=%param%
    2、api-playback-post
        cd utils
        python reportNotice.py %BUILD_URL% %domain% %env% %param% %key%
    """

