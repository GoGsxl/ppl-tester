import os, traceback
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.jsonSchema import dumps


def get_db_file():
    """ sqlite使用 """
    pwd = os.getcwd()
    db_name = 'fastTester.db'
    db_path = os.path.join(pwd, 'model', db_name)
    if not os.path.exists(db_path):
        pwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(pwd, 'model', db_name)
    return db_path


# todo MySQL
# SQLALCHEMY_DATABASE_URL = 'mysql+pymysql://root:123456@localhost:3306/fast_tester?charset=utf8'
# engine = create_engine(SQLALCHEMY_DATABASE_URL, json_serializer=dumps, pool_size=0, max_overflow=-1)
# todo sqlite
SQLALCHEMY_DATABASE_URL = f'sqlite:///{get_db_file()}'
engine = create_engine(SQLALCHEMY_DATABASE_URL, json_serializer=dumps)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def db_insert(db, sql_, mark=''):
    try:
        db.add(sql_)
        db.commit()
        db.refresh(sql_)
    except:
        msg = f'Error db_insert {mark}：\n{traceback.format_exc()}'
        print(msg)
        return msg


def db_update(db, select_obj, sql_: dict, mark=''):
    try:
        select_obj.update(sql_)
        db.commit()
    except:
        msg = f'Error db_update {mark}：\n{traceback.format_exc()}'
        print(msg)
        return msg


def db_is_none(data):
    return_data = None
    if data:
        if isinstance(data, dict): return_data = dumps(data)
        else: return_data = data
    return return_data
