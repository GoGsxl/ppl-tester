# PPL-Tester
### 简介
http工具集,通过代理获取到API的请求与响应信息,将这些请求信息进行流量回放/锲约测试或快速生成用例, 亦可通过人工进行修改参数化提取、变量引用、断言等形成API自动化测试用例等！
你以为只是流量回放吗？错~走去瞧瞧！

看官~请记得给个**star**呗？
**项目地址：** 

 [github](https://github.com/git-gsxl/FastTester.git)  
 [gitee](https://gitee.com/qq772262624/FastTester.git)

---
# 功能介绍
#### 流程图 (简陋ing···)
![ppl-tester](./desc/ppl-tester.jpg)

    ps：
    1、作者 Windows exe 运行,其它系统可自行打包或以 Python ppl x 执行.
    2、运行程序需要在项目根目录下运行...

需要安装Python3环境及依赖库:
```shell
pip install -r requirements.txt
```

## 1、proxy http
    
    command: ppl.exe f   (python ppl.py f)
        2023-01-20 10:39:53.628 | INFO     | __main__:cmd:37 - run:http flows cat. exit:Ctrl+C
        2023-01-20 10:39:53.642 | INFO     | utils.flows:cat_mock_load:25 - loaded mock*.json match to will mock！
        2023-01-20 10:39:53.644 | INFO     | utils.flows:__init__:114 - Proxy server listening at http://0.0.0.0:8888
![proxy-http](./desc/proxy-http.png)

基本代理等使用请参阅博文：[点击跳转](https://blog.csdn.net/qq_42675140/article/details/125128261 "PPL")

官方文档：https://docs.mitmproxy.org/stable

中文文档：https://ptorch.com/docs/10/mitmproxy_introduction

---
## 2、mock http response
可对 response 进行mock！

### 2.1 配置 config.ini

    mock = ON
        mock ON ：开启mock
        mock OFF：关闭mock
    mode = ON
        mode ON ：向远程服务器发送任何数据，且根据mock数据交集返回数据从而响应
        mode OFF：不向远程服务器发送任何数据

### 2.2 mock文件格式：mock*.json 

### 2.3 随机参数引用格式：${faker}
    
    结合 faker 的方法进行随机模式,文档请参考：https://faker.readthedocs.io/en/master/providers/faker.providers.python.html
    mock demo：
    {
      "api/user/info": {
        "bool": "${pybool}",
        "name": "${name}",
        "int": "${pyint}",
        "float": "${pyfloat(0,1)}",
        "data|1-3": [
          {
            "name": "${name}"
          }
        ]
      }
    }
mock demo 输出
![mock demo 输出](./desc/flows-mock.png)

---
## 3、http flows replace
request 正则替换支持替换(headers url body cookie)

    replace = {"pattern":"value","pattern1":"value1"}
    使用场景:
        1.鉴权：将 token 设置为空,如：
            replace = {"old token xxx":""}
        2.越权：将 token 设置为另用户token,越权又分为①水平越权(同角色)②垂直越权(向上级),如：
            replace = {"old token xxx":"new token xxx"}
        3.流量转发, 将test环境的前端去访问正式环境的数据(前端问题复现)
            {"old host":"new host"}
        PS：因前端本就发出 old host 请求,所以前端看到请求还是 old host 但真实是请求到 new host.

## 4、https证书过期检测
config.ini -> check_ssl hosts
    
    check_ssl = app.xxx.com,web.xxx.com
    command:
        ppl.exe s
---
## 5、api playback
### 5.1 接口用例集合获取
#### 方式1：[Fiddler](https://blog.csdn.net/qq_42675140/article/details/127349890 "Fiddler")

1、将项目下`desc/fiddler.txt`复制文本粘贴,FiddlerScript

2、更改为符合自己业务领域配置,是项目绝对路径`app`目录,注意要用两个扛`\\`

![在这里插入图片描述](https://img-blog.csdnimg.cn/bef7d987ec8f4f02a97f8dcea3b2aa31.png)
#### 方式2(推荐)：[mitmproxy](https://blog.csdn.net/qq_42675140/article/details/125128261 "mitmproxy")
1、将项目下`config.ini`过滤域名改为自己需要配置的域名以及业务领域,**如果填写db_url则流量信息直接入库**

![flows-config](./desc/flows-config.png)

2、需要配置代理证书等,详看[mitmproxy使用文档](https://blog.csdn.net/qq_42675140/article/details/125128261 "mitmproxy使用文档")

3、运行
    
    command:
        ppl.exe f
![flows-run](./desc/flows-run.png)

#### 以上方式1及方式2 会得到txt文件 或直接入库
如果基于方式2(mitmproxy),配置db_url可直接流量入库回放测试.
![flows-db](./desc/flows-db.png)
1、你会得到：./data/api-xxx.txt 或 fiddler-xxx.txt

2、如需要用例入库,则执行命令行：
```shell
ppl.exe --play=0
```
另外可能需要进行数据库连接配置`./config.ini.db_url`,默认为`sqlite`

mysql:`db_url = mysql+pymysql://root:123456@127.0.0.1:3306/tester?charset=utf8`

数据迁移:`ppl.exe --move=new_db_url`

---
### 5.2 执行测试
命令行参数说明(部分可在pytest.ini下默认配置),与pytest框架一致,并且新增以下参数：
1) --env：查询业务领域=ppl及环境=test的用例
   
         如：--env=ppl,test   
   
2) --param：附加将version参数替换为1或追加
   
         如(Windows)：--param={\"version\":\"1\"}
   
3) --file：读取app目录下所有txt文件进行流量回放,详细使用看流量回放
   
         如：--file=1
   
4) --play：读取txt文件进行用例入库
         如：--play=0  
   
         0：读取txt用例入库
         1：读取db用例进行回放测试
         2：读取txt文件流量回放
         3: 读取阿里云日志流量并入库
   
5) --init：db表结构初始化,一般不需要用到
         如：--init=1

#### 方式1：txt文件流量回放
` ps：不支持下载/上传文件回放,不要将txt文件换行或格式变化哦(只回放API响应码为200)`

      1）方式1：默认为app目录下全部txt文件(以下2-3不存在文件时亦是)：pytest --file=1
      
      2）方式2：指定app目录下的文件：pytest --file=fiddler_2022-7-31.txt
      
      3）方式3：绝对路径指定文件(注意win下需要\\)：pytest --file=E:\\fiddler_2022-7-31.txt
      
      4）方式4：相对路径指定文件：pytest --file=./fiddler_2022-7-31.txt
      
#### 方式2：经过用例入库,执行db用例测试 
需要先配置 pytest.ini(推荐) 或 config db在进行运行.

详情查看 5.6 db或pytest config说明.

配置pytest.ini,作用与db用例映射执行对应环境测试.
![pytest-config](./desc/pytest-config.png)
```shell
ppl.exe --env=domain,env --param={\"version\":\"1\"}
```
`ps：Windows可以生成allure报告：ppl.exe r
(支持替换变量,存储变量,引用变量,响应断言)`

---

### 5.3 后置处理器介绍：http_collect
参数提取器,默认是取第1个值(支持提取response与headers接口的返参)
Jsonpath语法请参考：https://goessner.net/articles/JsonPath
#### 1.Jsonpath 区分大小写

1）获取key的值：`['key'] ---->  {'key':'value'}`

2）获取key的值并重新命名：`[{'key':'name'}] ----> {'name':'value'}`

3）获取key的值并指定取第n个：`['key':n] ----> {'key':values[n]}`

4）获取key的值并重新命名及指定取第n个：`['key':['name',n]] ----> {'name':values[n]}`

5）原生Jsonpath语法：`['$.data.key'] ----> {'key':'value'}`

6）原生Jsonpath语法并重新命名：`[{'$.data.key':'name'}] ----> {'name':'value'}`

7）原生Jsonpath语法并指定取第n个：`[{'$.data.key':n}] ---->  {'key':values[n]}`

8）原生Jsonpath语法并重新命名及指定取第n个：`[{'$.data.key':['name',n]}] ---->  {'name':values[n]}`
#### 2.正则表达式
1）获取正则表达式的值并命名为env：`[{'re':['env','http://(.+?)/']}] ---->  {'env':'value'}`

2）获取正则表达式的值并命名为env及取第n个值：`[{'re':['env','http://(.+?)/', -1]}] ----> {'name':'value'}`

---
### 5.4 断言使用介绍：http_assert
##### 1.Jsonpath 断言
1.字符在里面：["msgId"]
   
      `实际为：assert "msgId" in response.text`
   
2.变量在里面：["${msgId}"]

    `实际为：assert "${msgId}" in response.text`

2.字符相等：[{"msgId":"123456"}]

    `实际为：assert 123456 == json_path(result.json(), 'msgId')`

3.字符在里面or其它：[{"msgId":["123456","in"]}]   `注：in 可以是== != not in`

      `assert 123456 in response.get('msgId')`

4.长度：1 == len(response.get('msgId'))：[{"msgId":[1,"len"]}]
   
      `assert 1 == len(response.get('msgId'))`

##### 2.正则表达式断言
1.直接写正则表达式即可,如：`[{'re':'http://(.+?)/'}]`

---
### 5.5 变量引用(参数化关联)
使用本系统且遵循Faker语法直接引用：${Faker语法}

ppl_开头,为自定义生成数据方法

Faker 更多请查阅官方文档：https://faker.readthedocs.io/en/stable/locales/zh_CN.html#faker-providers-address
![pytest-run](./desc/pytest-run.png)
字段数据结构及解释,亦可查阅代码model：
![data-word](./desc/data-word.png)

#### 1.号码相关：
1）手机号：${phone_number}
`18520149907`

2）身份证号码：${ssn}
`410622198603154708`
#### 2.时间日期相关
1）当前日期时间：${ppl_now_datetime}
`2022-07-02 12:56:58`

2）当前时间戳：${ppl_time}
`1656737818`

3）当前日期：${ppl_now_date}
`2022-07-02`

4）当前时间：${ppl_now_time}
`12:56:58`

5）过去7天的日期时间：${ppl_datetime(-7)}
`2022-06-25 00:00:00`

6）未来7天的日期时间：${ppl_datetime(7)}
`2022-07-09 23:59:59`

7）随机年-月-日：${date}
`1996-03-20`

8）随机(时:分:秒)：${time}
`04:52:23`

9）未来的日期时间：${future_datetime(end_date=+7d)}
`2022-07-07 16:01:23`

10）过去的日期时间：${past_datetime(end_date=-7d)}
`2022-06-29 13:29:20`

#### 3.名字相关：
1）姓名：${name}
`王凯`

2）姓名(女)：${name_female}
`戴丽丽`

3）姓名(男)：${name_male}
`刘荣`

4）姓：${last_name}
`宋`

5）名字：${first_name}
`强`
#### 4.地址相关
1）地址：${address}
`香港特别行政区大冶县上街钟街k座 664713`

2）省：${province}
`河北省`

3）市：${city}
`长春县`

4）地区：${district}
`白云`

5）街道地址：${street_address}
`武汉街D座`

---
### 5.6 db或pytest config说明
使用`pytest.ini`.`tester`配置 或 db config表配置,配置一种即可。
推荐使用pytest.ini
#### 账号环境配置
    
    1、pytest.ini 例子(需要压缩json,不可格式化)
        [test]
        tester = {"gray":"gray","Tester":[{"https://blog.csdn.net":{"url":"/qq_42675140","body":{},"method":"GET","collects":["ppl_cookie"]}},{"http://open-ppl-getaway.com":{"Authorization":"Bearer ","key":"nf9vMghQLyEZkeyxxxxx0ln9klsPz","secret":"ylJhZzwvaa2NxxxsecretlDtNsJSyMh"}}],"filter_code":{},"filter_path":["/user/logout","/user/login"]}
          
      [test]：表示定义的环境 test,可以多个.
      tester：pytest 账号登录/过滤等配置
          1) gray：默认gray就好,一般用于AB测试模型则需要配置.
          2) Tester：登录获取token或cookie初始化,可配置多个登录信息
                collects：表示后置处理器 collect (使用详细查看第三点[后置处理器使用]),用例提取token或cookie作为登录态
          3) filter_code：过滤某些接口响应内容,可不写
          4) filter_path：过滤某些接口url,一般用于过滤登录及退出登录以免执行测试时影响登录态

    2、db config如下例子, 直接复制粘贴保存即可(可格式化)：
    {
        "gray":"gray",
        "Tester":[
            {
                "https://app-xxx.com":{
                    "url":"/api/user/login",
                    "json":{
                        "mobile":18888888888,
                        "Password":"mVs6NwvIFRgN0aaUo4KZOiW9QZWbKZjqVX1eW9Gr2s4rgZ5atS3ppY39ZlyE37Tb2/zo6YWJV6VJV="
                    },
                    "method":"POST",
                    "collects":[
                        "clienttoken"
                    ]
                }
            },
            {
                "https://web-xxx.com":{
                    "url":"/api/index.php?r=data/login",
                    "data":"user=admin&password=4076f862096d1536b6cac6866e386655=",
                    "method":"POST",
                    "headers":{
                        "content-Type":"application/x-www-form-urlencoded"
                    },
                    "collects":[
                        "ppl_cookie"
                    ]
                }
            }
        ],
        "filter_code":{
            "$response_key":[
                200,
                "200"
            ]
        },
        "filter_path":[
            "/api/user/logout",
            "/api/user/login"
        ]
    }
### 5.7 mysql等断言
待开发

## 6、web页面管理用例等
待开发

## 7、flows客户端,集成以上功能...
待开发

### 如有建议/疑问请联系我：https://blog.csdn.net/qq_42675140
![WeChat](./desc/WeChat.png)
