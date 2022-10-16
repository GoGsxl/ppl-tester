## FastTester：流量录制

有以下两种方式进行录制 ①Fiddler ②mitmproxy

一、Fiddler

1. 项目文件：utils/httpCat/fiddler.txt
2. 将 fiddler.txt 内容粘贴至 fiddler FiddlerScript
3. 更改业务领域等参数,保存,进行抓包即可

设置请参阅：[fiddler-13-修改脚本保存流量文件](https://blog.csdn.net/qq_42675140/article/details/127349890 "PPL")


二、mitmproxy

1、安装依赖包`mitmproxy`：`pip install -r requirements.txt`

2、`config.ini`设置,Windows下直接双击运行：startCollect.cmd

代理等使用文档请参阅：[点击跳转](https://blog.csdn.net/qq_42675140/article/details/125128261 "PPL")

注：(如果出现冲突使用：`pip install mitmproxy==5.0.0`)