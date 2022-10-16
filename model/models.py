from datetime import datetime
from sqlalchemy import *
from model.dbBase import Base


class PPlConfig(Base):
    __tablename__ = 'ppl_config'
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(32), comment="业务领域")
    env = Column(String(32), comment="环境")
    fastTester = Column(JSON, comment="测试配置")


class PPlPlayback(Base):
    __tablename__ = 'ppl_playback'
    id = Column(Integer, primary_key=True, index=True)
    msg = Column(TEXT, comment='断言结果')
    domain = Column(String(32), comment="业务领域", index=True)
    gray = Column(String(32), comment="AB灰度测试时使用", index=True)
    api_name = Column(String(64), comment='接口名称,预留用')
    method = Column(String(32), comment='请求类型GET/POST')
    host = Column(String(255), comment='域名环境', index=True)
    path = Column(String(255), comment='接口路径', index=True)
    headers = Column(JSON, comment='请求headers')
    body = Column(JSON, comment='请求body(json或data)')
    keys = Column(TEXT, comment='小写字母的keys，用来对比是否重复用例')
    response = Column(JSON, comment='响应结果')
    schema_response = Column(JSON, comment='json_schema结构体')
    grade = Column(Integer, comment="用例执行优先级，用来排序")
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, onupdate=datetime.now, default=datetime.now, comment='更新时间')
    uri = Column(TEXT, comment='path + query')
    curl = Column(TEXT, comment='生成的curl')
    skip = Column(Integer, default=0, comment='1为跳过此数据')
    collects = Column(JSON, comment='后置提取器')
    assert_list = Column(JSON, comment="断言数组逗号隔开")


class PPlFormal(Base):
    __tablename__ = 'ppl_formal'
    id = Column(Integer, primary_key=True, index=True)
    msg = Column(TEXT, comment='断言结果')
    domain = Column(String(32), comment="业务领域", index=True)
    gray = Column(String(32), comment="AB灰度测试时使用", index=True)
    api_name = Column(String(64), comment='接口名称,预留用')
    method = Column(String(32), comment='请求类型GET/POST')
    host = Column(String(255), comment='域名环境', index=True)
    path = Column(String(255), comment='接口路径', index=True)
    headers = Column(JSON, comment='请求headers')
    body = Column(JSON, comment='请求body(json或data)')
    keys = Column(TEXT, comment='小写字母的keys，用来对比是否重复用例')
    response = Column(JSON, comment='响应结果')
    schema_response = Column(JSON, comment='json_schema结构体')
    grade = Column(Integer, comment="用例执行优先级，用来排序")
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, onupdate=datetime.now, default=datetime.now, comment='更新时间')
    uri = Column(TEXT, comment='path + query')
    curl = Column(TEXT, comment='生成的curl')
    skip = Column(Integer, default=0, comment='1为跳过此数据')
    collects = Column(JSON, comment='后置提取器')
    assert_list = Column(JSON, comment="断言数组逗号隔开")
