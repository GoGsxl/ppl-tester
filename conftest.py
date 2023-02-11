import pytest
from configparser import ConfigParser
from utils.httpReq import Http
from utils.playback import Playback
H = Http('run')
P = Playback(H)


def pytest_addoption(parser):
    """ choose """
    help1 = 'choose env  : --env=domain,env'
    help2 = 'choose param: --param={"a":"master"}'
    help3 = 'choose play : --play=1'
    help4 = 'choose file : --file=file_path'
    help5 = 'choose init : --init=true'
    help6 = 'choose count: --count=1'
    help7 = 'choose move : --move=1 default config.ini new_db_url'
    parser.addoption("--env", action="store", help=help1)
    parser.addoption("--param", action="store", help=help2)
    parser.addoption("--play", action="store", help=help3)
    parser.addoption("--file", action="store", help=help4)
    parser.addoption("--init", action="store", help=help5)
    parser.addoption("--count", action="store", help=help6)
    parser.addoption("--move", action="store", help=help7)
    parser.addini('env', help=help1)
    parser.addini('param', help=help3)
    parser.addini('play', help=help4)
    parser.addini('file', help=help2)
    parser.addini('init', help=help5)
    parser.addini('count', help=help6)
    parser.addini('move', help=help7)


def env_vars(metafunc):
    """ get env param or pytest.ini[tested]"""
    config, variables = metafunc.config, {}
    cur_env = config.getoption('--env') or config.getini('env')
    cur_param = config.getoption('--param') or config.getini('param')
    cur_play = config.getoption('--play') or config.getini('play')
    cur_file = config.getoption('--file') or config.getini('file')
    cur_init = config.getoption('--init') or config.getini('init')
    cur_move = config.getoption('--move') or config.getini('move')
    case_count = config.getoption('--count') or config.getini('count')
    conf, ini_file = ConfigParser(), config.inifile
    conf.read(ini_file)
    if conf.has_section('tested'): variables.update(conf.items('tested'))
    if cur_env: variables['env'] = cur_env
    if cur_param: variables['param'] = cur_param
    if cur_play: variables['play'] = cur_play
    if cur_file: variables['file'] = cur_file
    if cur_init: variables['init'] = cur_init
    if cur_move: variables['move'] = cur_move
    if case_count: variables['count'] = case_count
    env_section = variables.get('env').split(',')[1] if variables.get('env') else 'test'
    variables.update(conf.items(env_section)) if conf.has_section(env_section) else {}
    return variables


def pytest_generate_tests(metafunc):
    """ Custom parameterization """
    # get env param
    variables = env_vars(metafunc)
    # get cases
    all_data, paths = P.pytest_run(variables)
    H.logs.info(f'testcases data count is {len(all_data)}')
    # pytest param
    if "param" in metafunc.fixturenames: metafunc.parametrize("param", all_data, ids=paths, scope="function")


@pytest.fixture(scope="session")
def obj():
    return H, P
