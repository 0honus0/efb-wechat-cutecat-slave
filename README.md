使用方法

1. 配置可爱猫客户端**

运行该项目需要可爱猫与efb从端在 **同一局域网** 或 **两者均有公网IP**

#### 1.1 下载可爱猫及对应微信版本

[下载链接](https://t.me/efb_wechat_cutecat_slave/3) 点击后跳转到tg消息进行下载

#### 1.2 解压安装微信到可爱猫根路径

安装之后文件夹内容如图所示（file 文件夹为可选）

![文件夹](https://fastly.jsdelivr.net/gh/0honus0/PicCDN@master/2022_04_09_1.png)

#### 1.3启动可爱猫登录微信

#### 1.4 在账号栏获取 wxid 作为 robot_wxid

#### 1.5 在插件列表启用 iHttp 插件，双击点开设置界面，如图所示

![插件](https://fastly.jsdelivr.net/gh/0honus0/PicCDN@master/2022_04_09_2.png)

##### 远程处理接口格式为 http:// ip:18888/event

ip为运行efb从端所在的内网或者外网ip

#### 1.6 如果启动鉴权需要注册插件账号并登录，建议运行在公网的用户设置

启用后可在 可爱猫根路径路径/app/iHttp.cat/配置 文件中找到 `Authorization`字段

# 2. 配置efb-wechat-cutecat-slave 从端

#### 2.1 安装依赖

```
sudo apt-get install libopus0 ffmpeg libmagic1 python3-pip git libssl-dev

pip3 install -U git+https://github.com/0honus0/python-CuteCat-iHttp.git

pip3 install -U git+https://github.com/0honus0/efb-wechat-cutecat-slave.git

pip3 install efb-telegram-master

为启用telegram 动态Animation转gif功能，需要额外安装一下两个依赖，并安装efb-telegram-master开发版

pip3 install lottie

pip3 install cairosvg

pip3 install -U git+https://github.com/ehForwarderBot/efb-telegram-master.git
```

#### 2.2 创建配置文件

```
mkdir -p ~/.ehforwarderbot/profiles/WeChat
mkdir -p ~/.ehforwarderbot/profiles/WeChat/blueset.telegram
mkdir -p ~/.ehforwarderbot/profiles/WeChat/honus.CuteCatiHttp
touch ~/.ehforwarderbot/profiles/WeChat/config.yaml
touch ~/.ehforwarderbot/profiles/WeChat/blueset.telegram/config.yaml
touch ~/.ehforwarderbot/profiles/WeChat/honus.CuteCatiHttp/config.yaml
```

建好之后的文件结构如图所示

```
WeChat/
├── blueset.telegram
│   └── config.yaml
├── config.yaml
└── honus.CuteCatiHttp
    └── config.yaml
```

#### 2.3 配置主从端

##### 2.3.1 通过配置文件设置主端

编辑 `/.ehforwarderbot/profiles/WeChat/config.yaml`(设置主端为telegram，从端为微信)

```
master_channel: blueset.telegram
slave_channels:
- honus.CuteCatiHttp
```

##### 2.3.2进行主端配置

###### (1) 创建机器人及配置机器人

创建一个新的 Bot，从tg向 [@BotFather](https://t.me/BotFather) 发起会话。发送指令 `/newbot` 以启动向导。指定Bot 的名称与用户名（用户名必须以 bot 结尾）。设置完成之后可以获取token

###### (2) 进一步配置机器人

发送 `/setprivacy` 到 @BotFather，选择刚刚创建好的 Bot 用户名，然后选择 “Disable”.
发送 `/setjoingroups` 到 @BotFather，选择刚刚创建好的 Bot 用户名，然后选择 “Enable”.
发送 `/setcommands` 到 @BotFather，选择刚刚创建好的 Bot 用户名，然后发送如下内容：

```
link - 将会话绑定到 Telegram 群组
chat - 生成会话头
recog - 回复语音消息以进行识别
update_info - 更新群组名与头像
extra - 获取更多功能
```

###### (3) 获取Telegram ID

建议从已有bot获取

[@get_id_bot](https://t.me/get_id_bot) 发送 `/start`
[@GroupButler_Bot](https://t.me/GroupButler_Bot) 发送 `/id`
[@userinfobot](https://t.me/userinfobot) 发送任意文字
[@orzdigbot](https://t.me/orzdigbot) 发送 `/user`

编辑 `/.ehforwarderbot/profiles/WeChat/blueset.telegram/config.yaml`

```
token: "12345678:QWFPGJLUYarstdheioZXCVBKM"   #从tg @BotFather处获得的token
admins:
- 123456789                                   #设置管理员
```

##### 2.3.3 进行从端配置

编辑 `/.ehforwarderbot/profiles/WeChat/honus.CuteCatiHttp/config.yaml`

```
api_url: "http://127.0.0.1:8090"               #可爱猫运行所在ip + port
self_url: "http://127.0.0.1:18888"             #efb从端运行所在ip + port
receive_self_msg: True                         #接收自己发送的消息，只通知消息类型，默认为False
robot_wxid: ""                                 #配置可爱猫时获取的 robot_wxid
access_token: ""                               #配置可爱猫时获取的 Authorization
```

**根据情况填写ip地址，不要无脑写127.0.0.1这样的地址，这里只是示例，填写的ip地址需要另一个程序可以访问**

api_url 若是正确的，则在浏览器访问之后如图所示

![api_url](https://fastly.jsdelivr.net/gh/0honus0/PicCDN@master/2022_04_10_1.jpg)

self_url 若是正确的，则在浏览器访问之后如图所示

![self_url](https://fastly.jsdelivr.net/gh/0honus0/PicCDN@master/2022_04_10_2.png)

# 3. 启动efb

```
python3 -m ehforwarderbot -p WeChat

or

ehforwarderbot -p WeChat
```

[详细教程 点击查看](https://honus.top/2022/04/09/569.html)

1. 安装 python-CuteCat-iHttp 插件

   ```
   pip3 install -U git+https://github.com/0honus0/python-CuteCat-iHttp.git
   ```
2. 安装efb-telegram-master

   ```
   pip3 install efb-telegram-master
   ```
3. 安装efb-wechat-cutecat-slave

   ```
   pip3 install -U git+https://github.com/0honus0/efb-wechat-cutecat-slave.git
   ```
4. 配置 config.yaml (路径 honus.CuteCatiHttp/config.yaml)

   ```
   api_url: "http://127.0.0.1:8090"
   self_url: "http://127.0.0.1:18888"
   receive_self_msg: True
   label_style: True
   robot_wxid: ""
   access_token: ""
   ```

api_url 为运行可爱猫的ip + iHttp 插件的 port

self_url 为运行efb从端的 ip + port

reveice_self_msg True为接收自己发送的消息，默认为False

label_style True，在用户名前面添加#便于查找，默认为False

robot_wxid 为作为机器人的微信id

access_token 鉴权使用，可在iHttp路径下配置文件中找到，如果开启则需要设置，否则不需要
