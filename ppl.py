from utils.flows import run
from utils.playback import *
from subprocess import run as command
H = Http('run')
doc = """
        ppl command
        1.ppl h      ：ppl command help
        2.ppl s      ：http check ssl
        3.ppl f      ：http flows cat
        4.ppl m      ：monitor get ali error log
        5.ppl g      ：read ali log insert db
        6.ppl r      ：Windows report generate
        7.ppl -s ... ：pytest param... --play： 0 txt insert | 2 playback txt | 3 aliLog insert
        8.ppl n      ：jenkins pytest notice: ppl n $BUILD_URL $domain $env $param $key
        9.ppl q      ：quit ppl
       10.ppl p      ：build ppl.py package

        WeChat：GoGsxl
        Blog  ：https://blog.csdn.net/qq_42675140
------------------------------------------------------------
        """


def cmd(argv):
    arg = 'h'
    if argv: arg = argv[0].lower()
    if arg in ['help', 'h', 'v', 'version', '--version']:
        H.logs.info(ppl_text + doc)
        time.sleep(0.2)
        input_cmd = input("please input ppl command：")
        H.logs.info(f'input cmd：{input_cmd}')
        return cmd(input_cmd)
    elif arg in ['ssl', 's']:
        H.logs.info('run:http check ssl')
        return H.http_check_ssl()
    elif arg in ['flows', 'f']:
        H.logs.info('run:http flows cat. exit:Ctrl+C')
        return run(H)
    elif arg in ['monitor', 'm']:
        H.logs.info('run:monitor get ali error log')
        return AliLog(H).ali_get_error()
    elif arg in ['get', 'g']:
        cmd_str = 'pytest --play=3 -s'
        H.logs.info(f'run:http playback：{cmd_str}')
    elif arg in ['report', 'r']:
        system = sys.platform
        if 'win' in system:
            cmd_str = '%cd%/reports/allure/bin/allure serve %cd%/reports/report'
            H.logs.info(f'run:report generate {system}')
        else: return H.logs.warning(f'{system}:Report generation is not supported')
    elif arg in ['n', 'notice']:
        argv = argv[1:] if not isinstance(argv, str) else argv[1:].split(' ')[1:]
        return Playback(H).pytest_report_notice(argv)
    elif arg in ['q', 'quit']:
        H.logs.info('success exit')
        return os._exit(0)
    elif arg in ['p', 'pkg']:
        cmd_str = 'pyinstaller -F -i ./desc/build.ico ppl.py'
        H.logs.info(f'run:build ppl.py package')
    else:
        cmd_str = 'pytest'
        if isinstance(argv, list):
            for p in argv: cmd_str += f' {p}'
        else: cmd_str = f'pytest {argv}'
        if '--init' in cmd_str or '--play=0' in cmd_str: cmd_str += ' -s'
        H.logs.info(f'run:http playback：{cmd_str}')
    return command(cmd_str, shell=True)


if __name__ == '__main__':
    import py._path, py._path.local
    cmd(sys.argv[1:])
