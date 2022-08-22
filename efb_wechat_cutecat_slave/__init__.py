import logging, tempfile
import threading
from traceback import print_exc
from pydub import AudioSegment

import re
import time
from ehforwarderbot.chat import PrivateChat , SystemChatMember
from typing import Optional, Collection, BinaryIO, Dict, Any , Union
from datetime import datetime

from ehforwarderbot import MsgType, Chat, Message, Status, coordinator
from CuteCat import CuteCat

from . import __version__ as version

from ehforwarderbot.channel import SlaveChannel
from ehforwarderbot.types import MessageID, ChatID, InstanceID
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.exceptions import EFBException
from ehforwarderbot.message import MessageCommand, MessageCommands

from .ChatMgr import ChatMgr
from .CustomTypes import EFBGroupChat, EFBPrivateChat, EFBGroupMember
from .MsgDecorator import efb_text_simple_wrapper
from .WechatPcMsgProcessor import MsgProcessor
from .utils import download_file , emoji_telegram2wechat , emoji_wechat2telegram , load_config

TYPE_HANDLERS = {
    'text'              : MsgProcessor.text_msg,
    'image'             : MsgProcessor.image_msg,
    'video'             : MsgProcessor.video_msg,
    'voice'             : MsgProcessor.voice_msg,
    'qqmail'            : MsgProcessor.qqmail_msg,
    'share'             : MsgProcessor.share_link_msg,
    'location'          : MsgProcessor.location_msg,
    'other'             : MsgProcessor.other_msg,
    'animatedsticker'   : MsgProcessor.image_msg,
    'unsupported'       : MsgProcessor.unsupported_msg,
    'revokemsg'         : MsgProcessor.revoke_msg,
    'file'              : MsgProcessor.file_msg,
    'transfer'          : MsgProcessor.transfer_msg,
    'groupannouncement' : MsgProcessor.group_announcement_msg,
    'eventnotify'       : MsgProcessor.event_notify_msg,
    'miniprogram'       : MsgProcessor.miniprogram_msg,
    'scancashmoney'     : MsgProcessor.scanmoney_msg,
}

class CuteCatChannel(SlaveChannel):
    channel_name: str = "Wechat Pc Slave"
    channel_emoji: str = "📱"
    channel_id = "honus.CuteCatiHttp"

    config: Dict[str, Any] = {}

    info_list = {}
    info_dict = {}
    group_member_info = {}

    __version__ = version.__version__
    logger: logging.Logger = logging.getLogger("plugins.%s.CuteCatiHttp" % channel_id)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s  %(filename)s : %(levelname)s  %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    supported_message_types = {MsgType.Text, MsgType.Sticker, MsgType.Image, MsgType.Video,
                                MsgType.File, MsgType.Link, MsgType.Voice, MsgType.Animation}

    def __init__(self, instance_id: InstanceID = None):
        super().__init__(instance_id)
        config_path = efb_utils.get_config_path(self.channel_id)
        self.config = load_config(config_path)
        if 'api_url' not in self.config:
            raise EFBException("api_url not found in config")
        if 'robot_wxid' not in self.config:
            raise EFBException("robot_wxid not found in config")
        self.api_url = self.config['api_url']
        self.robot_wxid = self.config['robot_wxid']
        self.self_url = self.config['self_url']
        self.receive_self_msg = self.config.get('receive_self_msg',False)
        self.label_style = self.config.get('label_style',False)
        self.access_token = self.config.get('access_token',None)
        self.real_wxid = self.config.get('real_wxid',False)
        self.sendtoself = self.config.get('sendtoself',True)
        self.bot = CuteCat(api_url = self.api_url, self_url = self.self_url, robot_wxid = self.robot_wxid, access_token = self.access_token)
        ChatMgr.slave_channel = self

        @self.bot.on('EventSendOutMsg')
        def on_self_msg(msg: Dict[str, Any]):
            self.logger.debug(msg)

            efb_msgs = []
            #只处理系统消息中的拍了拍消息
            if msg['type'] == 'sysmsg' and ('拍了拍' in msg['msg'] or 'tickled' in msg['msg']):
                to_wxid = msg['to_wxid']
                name = self.get_friend_info('nickname' , to_wxid)
                remark = self.get_friend_info('remark' , to_wxid)
                chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid= to_wxid ,
                    name= remark or name or msg['msg'].split('拍了拍')[0]
                ))
                author = chat.other
                self.handle_msg( msg = msg , author = author , chat = chat)
            if not self.receive_self_msg:
                return
            if msg['final_from_wxid'] == self.robot_wxid and msg['type'] != 'sysmsg':
                if self.sendtoself:
                    chat = ChatMgr.build_efb_chat_as_system_user(EFBPrivateChat(
                        uid= self.robot_wxid,
                        name= 'WeChat_Robot'
                    ))
                    author = chat.other
                else:
                    to_wxid = msg['to_wxid']
                    name = self.get_friend_info('nickname' , to_wxid)
                    remark = self.get_friend_info('remark' , to_wxid)
                    chat = ChatMgr.build_efb_chat_as_system_user(EFBPrivateChat(
                        uid= to_wxid,
                        name= remark or name
                    ))
                    author = chat.self
                self.handle_msg( msg = msg , author = author , chat = chat)

        @self.bot.on('EventGroupMsg')
        def on_group_msg(msg: Dict[str, Any]):
            self.logger.debug(msg)
            group_wxid = msg['from_wxid']
            group_name = msg['from_name']
            userwxid = msg['final_from_wxid'] or group_wxid
            username = msg['final_from_name'] or group_name
            group_nick_name = self.get_group_member_nameinfo('group_nickname', group_wxid , userwxid)
            chat = None
            author = None

            if '@app' in group_wxid:
                chat = ChatMgr.build_efb_chat_as_group(EFBGroupChat(
                    uid = 'wechat_applet_notification',
                    name = '微信小程序通知'
                ))
            else:
                chat = ChatMgr.build_efb_chat_as_group(EFBGroupChat(
                        uid= group_wxid,
                        name=group_name or group_wxid
                ))
            remark = self.get_friend_info('remark', userwxid)
            
            if self.label_style:
                name = "#" + (remark or username) 
                alias = ((group_nick_name if group_nick_name != remark else None) or (username if remark != None else None))
                if alias != None:
                    alias ="#" + alias
            else:
                name = (remark or username) 
                alias = ((group_nick_name if group_nick_name != remark else None) or (username if remark != None else None))
            author = ChatMgr.build_efb_chat_as_member(chat, EFBGroupMember(
                    name = name ,
                    alias =alias ,
                    uid = userwxid
            ))
            self.handle_msg( msg = msg , author = author , chat = chat)
        
        @self.bot.on('EventFriendMsg')
        def on_friend_msg(msg: Dict[str, Any]):
            self.logger.debug(msg)

            name = msg['final_from_name']
            wxid = msg['final_from_wxid']
            chat = None
            auther = None
            remark = self.get_friend_info('remark', wxid)
            if (not self.receive_self_msg) and (msg['robot_wxid'] == self.robot_wxid and msg['from_wxid'] == self.real_wxid):
                return
            if self.label_style:
                name = "#"+ (remark or name or wxid)
            else:
                name = remark or name or wxid
            chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid= wxid,
                    name= name,
            ))
            author = chat.other
            self.handle_msg( msg = msg , author = author , chat = chat)

        @self.bot.on("EventSysMsg")
        def on_sys_msg(msg: Dict[str, Any]):
            group_wxid = msg['msg']['group_wxid']
            modifier_nickname = msg['msg']["modifier_nickname"]
            old_group_name = msg['msg']['old_group_name']
            new_group_name = msg['msg']['new_group_name']
            content = {}
            content['message'] = f"\"{modifier_nickname}\" 修改了群名 \"{old_group_name}\" 为 \"{new_group_name}\""
            self.deliver_alert_to_master( content = content , uid = group_wxid , name = '\u2139 群组通知')

        @self.bot.on('EventFriendVerify')
        def on_friend_verify(msg : Dict[str, Any]):
            self.logger.debug(msg)
            content = {}
            name = "\u2139 好友请求"
            uid = "friend_request"
            text = (
                f"\"{msg['final_from_name']}\" 想要添加你为好友!\n"
                "验证消息为 :\n"
                f"{msg['msg']['from_content']}"
            )
            content["message"] = text
            commands = [
                MessageCommand(
                    name=("Accept"),
                    callable_name="process_friend_request",
                    kwargs={'msg' : msg['msg']},
                )
            ]
            content["commands"] = commands
            self.deliver_alert_to_master(content = content , uid = uid , name = name)
            

        @self.bot.on('EventScanCashMoney')
        def on_scan_cash_money(msg : Dict[str, Any]):
            self.logger.debug(msg)
            name = msg['final_from_name']
            wxid = msg['final_from_wxid']
            chat = None
            auther = None
            remark = self.get_friend_info('remark', wxid)

            if not name:
                #发送两次因为iHttp插件发送两次
                content = {}
                content['message'] = f"{msg['msg']['scene_desc']} 收款金额 : {msg['msg']['money']} 元"
                self.deliver_alert_to_master( content = content  , uid = 'scan_cash_money' , name = '\u2139 收款')
            else:
                chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                        uid= wxid,
                        name= remark or name or wxid,
                ))
                author = chat.other
                self.handle_msg( msg = msg , author = author , chat = chat)

            
        @self.bot.on('EventGroupMemberAdd' , 'EventGroupMemberDecrease')
        def on_group_member_change(msg : Dict[str, Any]):
            self.logger.debug(msg)
            group_wxid = msg['msg']['group_wxid']
            group_name = msg['msg']['group_name']
            chat = None
            author = None
            chat = ChatMgr.build_efb_chat_as_group(EFBGroupChat(
                    uid= group_wxid,
                    name=group_name or group_wxid
            ))
            author = ChatMgr.build_efb_chat_as_member(chat, EFBGroupMember(
                    name = group_name ,
                    alias = None ,
                    uid = group_wxid
            ))
            self.handle_msg( msg = msg , author = author , chat = chat)
            
            
        @self.bot.on('EventReceivedTransfer')
        def on_received_transfer(msg : Dict[str, Any]):
            self.logger.debug(msg)
            content = {}
            name = msg['final_from_name']
            wxid = msg['final_from_wxid']
            chat = None
            auther = None
            remark = self.get_friend_info('remark', wxid)
            # chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
            #         uid= wxid,
            #         name= remark or name or wxid,
            # ))
            #author = chat.other
            text = (
                f"收到 {name}({wxid}) 转账\n"
                "金额为 :\n"
                f"{msg['msg']['money']}"
            )
            content["message"] = text
            commands = [
                MessageCommand(
                    name=("Accept"),
                    callable_name="process_transfer",
                    kwargs={'msg' : msg['msg']},
                )
            ]
            content["commands"] = commands
            uid = "process_transfer"
            self.deliver_alert_to_master(content = content , uid = uid , name = name)
            #self.handle_msg( msg = msg , author = author , chat = chat)

    #处理消息
    def handle_msg(self , msg : Dict[str, Any] , author : 'ChatMember' , chat : 'Chat'):
        efb_msgs = []
        if msg['type'] == 'share':
            # 判断分享的是文件类型
            if 'get_file' in msg['msg']:
                efb_msgs.append(MsgProcessor.file_msg(msg))
            else:
                efb_msgs = TYPE_HANDLERS[msg['type']](msg)
                if not efb_msgs:
                    return
                else:
                    efb_msgs = tuple(efb_msgs)
        elif msg['type'] in ['miniprogram' , 'video' , 'image' , 'file' , 'location' , 'qqmail', 'animatedsticker' , 'other' , 'revokemsg' , 'groupannouncement' , 'eventnotify' , 'transfer' , 'scancashmoney']:
            efb_msg = TYPE_HANDLERS[msg['type']](msg)
            efb_msgs.append(efb_msg) if efb_msg else efb_msgs
        elif msg['type'] in ['voip' , 'card']:
            efb_msgs.append(TYPE_HANDLERS['unsupported'](msg))
        elif msg['type'] in ['voice']:
            efb_msgs.append(TYPE_HANDLERS['voice'](msg , chat))
        else:
            msg['msg'] = emoji_wechat2telegram(msg['msg'])
            efb_msgs.append(TYPE_HANDLERS['text'](msg , chat))

        for efb_msg in efb_msgs:
            efb_msg.author = author
            efb_msg.chat = chat
            efb_msg.uid = "{uni_id}".format(uni_id=str(int(time.time())))
            efb_msg.deliver_to = coordinator.master
            coordinator.send_message(efb_msg)
            if efb_msg.file:
                efb_msg.file.close()

    #警告信息
    def deliver_alert_to_master(self, uid : str = 'System', name : str = 'Alert' , content : dict = None , send_as_new : bool = False):
        if send_as_new:
            uid = "uid_%s" % int(time.time())

        chat = {
            'uid': uid,
            'name': name,
        }
        self.send_msg_to_master(chat , content)

    def process_friend_request(self , msg : Dict[str, Any]):
        data = self.bot.AgreeFriendVerify( msg = msg ) or {}
        if data.get('code') >=0:
            return 'Success'
        else:
            return 'Failed'

    def process_transfer(self , msg : Dict[str, Any]):
        data = self.bot.AcceptTransfer( msg = msg ) or {}
        if data.get('code') >=0:
            return 'Success'
        else:
            return 'Failed'

    def send_msg_to_master(self , chat  , content : str):
        self.logger.debug(repr(content))
        if not getattr(coordinator, "master", None):  # Master Channel not initialized
            raise Exception(context["message"])
        chat = ChatMgr.build_efb_chat_as_system_user(chat)
        try:
            author = chat.get_member(SystemChatMember.SYSTEM_ID)
        except KeyError:
            author = chat.add_system_member()
        msg = Message(
            uid="{uni_id}".format(uni_id=str(int(time.time()))),
            type=MsgType.Text,
            chat=chat,
            author=author,
            deliver_to=coordinator.master,
        )

        if "commands" in content:
            msg.commands = MessageCommands(content["commands"])
        if "message" in content:
            msg.text = content['message']
        coordinator.send_message(msg)

    #定时检查可爱猫状态
    def check_status(self , t_event):
        self.logger.debug("Start checking status...")
        interval = 1800
        res = self.bot.GetAppDir()
        if not res:
            content = {"message": "可爱猫已掉线，请检查设置"}
            self.deliver_alert_to_master( content = content )
        if t_event is not None and not t_event.is_set():
            self.check_status_timer = threading.Timer(interval, self.check_status, [t_event])
            self.check_status_timer.start()

    def cron_update_task(self , t_event):
        interval = 3600
        self.update_friend_info()
        for k in self.group_member_info:
            self.update_group_member_info(k)
        if t_event is not None and not t_event.is_set():
            self.cron_update_timer = threading.Timer(interval, self.cron_update_task, [t_event])
            self.cron_update_timer.start()

    #获取全部联系人
    def get_chats(self) -> Collection['Chat']:
        return self.update_friend_info()

    #获取联系人
    def get_chat(self, chat_uid: ChatID) -> 'Chat':
        if 'chat' not in self.info_list or not self.info_list['chat']:
            self.logger.debug("Chat list is empty. Fetching...")
            self.update_friend_info()

        if '@chatroom' in chat_uid:
            chat = EFBGroupMember(
                uid = chat_uid, 
                name = self.get_group_member_info('nickname' , chat_uid) or None
            )
            chat = ChatMgr.build_efb_chat_as_group(chat)
        else:
            chat = EFBPrivateChat(
                uid=chat_uid,
                name= self.get_friend_info('remark' , chat_uid) or self.get_group_member_info('nickname' , chat_uid) or None
            )
            chat = ChatMgr.build_efb_chat_as_private(chat)
        return chat

    # at获取群成员列表
    def atlist(self, msg):
        group_wxid = msg.chat.uid
        member_list = self.get_group_members_list(group_wxid)
        chat = msg.chat
        try:
            author = chat.get_member(SystemChatMember.SYSTEM_ID)
        except KeyError:
            author = chat.add_system_member()
        # in case failure
        if not member_list:
            msg = Message(
                text="Failed to get group member list...",
                uid="{uni_id}".format(uni_id=str(int(time.time()))),
                type=MsgType.Text,
                chat=chat,
                author=author,
                deliver_to=coordinator.master,
            )
            coordinator.send_message(msg)
            return
        # compose text
        text = ''
        for i in member_list:
            if i['group_nickname']:
                text += "{group_nickname}({nickname}):\n" \
                        "{wxid}\n".format(group_nickname=i['group_nickname'], nickname=i['nickname'], wxid=i['wxid'])
            else:
                text += "{nickname}:\n" \
                        "{wxid}\n".format(nickname=i['nickname'], wxid=i['wxid'])
        # send
        msg = Message(
            text=text,
            uid="{uni_id}".format(uni_id=str(int(time.time()))),
            type=MsgType.Text,
            chat=chat,
            author=author,
            deliver_to=coordinator.master,
        )
        coordinator.send_message(msg)
    
    #发送消息
    def send_message(self, msg : Message) -> Message:
        chat_uid = msg.chat.uid

        if msg.edit:
            pass  # todo
        
        #将语音转成mp3，按文件下发。
        if msg.type == MsgType.Voice:
            self.logger.debug("msg.file.name="+msg.file.name)
            f = tempfile.NamedTemporaryFile(suffix=".mp3")
            AudioSegment.from_ogg(msg.file.name).export(f, format="mp3")
            self.logger.debug("msg.file.new.name="+f.name)
            msg.file = f
            msg.file.name = f.name
            msg.type = MsgType.Video
            
        try:
            filename = msg.file.name.split('/')[-1] if msg.file else msg.file.name
            temp_msg = {'name' : filename , 'url': self.self_url + msg.file.name}
        except:
            pass

        if msg.type in [MsgType.Text , MsgType.Link]:
            temp_msg = emoji_telegram2wechat(msg.text)
            if msg.text.startswith('@') and re.search("^[0-9]+@chatroom$", chat_uid):
                at_member_wxid = msg.text[1:].split(' ')[0]
                try:
                    at_text = msg.text[1:].split(' ', 1)[1]
                except IndexError:
                    at_text = ''
                self.bot.SendGroupMsgAndAt(group_wxid=chat_uid, member_wxid=at_member_wxid, msg=at_text)
            elif msg.text == '/at' and re.search("^[0-9]+@chatroom$", chat_uid):
                self.atlist(msg)
            else:
                self.bot.SendTextMsg(to_wxid=chat_uid, msg=temp_msg)
        elif msg.type in [MsgType.Sticker]:
            data = self.bot.SendImageMsg( to_wxid=chat_uid , msg = temp_msg)
        elif msg.type in [MsgType.Image]:
            data = self.bot.SendImageMsg( to_wxid=chat_uid , msg = temp_msg)
            if msg.text:
                self.bot.SendTextMsg( to_wxid=chat_uid , msg= msg.text)
        elif msg.type in [MsgType.File]:
            data = self.bot.SendFileMsg( to_wxid=chat_uid , msg = temp_msg)
        elif msg.type in [MsgType.Video ]:
            data = self.bot.SendVideoMsg( to_wxid=chat_uid , msg = temp_msg)
            if msg.text:
                self.bot.SendTextMsg( to_wxid=chat_uid , msg= msg.text)
        elif msg.type in [MsgType.Animation]:
            data = self.bot.SendEmojiMsg( to_wxid=chat_uid , msg = temp_msg)
        if self.receive_self_msg:
            if msg.type in [MsgType.Video , MsgType.Animation , MsgType.Image , MsgType.Sticker , MsgType.File]:
                content = {}
                content['message'] = ("%s Send Success" % msg.type) if data.get('code') >= 0 else ("%s Send Failed" % msg.type)
                self.deliver_alert_to_master( content = content , uid = chat_uid)
            return msg
        return msg

    def get_chat_picture(self, chat: 'Chat') -> BinaryIO:
        wxid = chat.uid
        headimgurl = self.get_group_member_info('headimgurl' ,wxid)
        if headimgurl:
            headimgurl = '/'.join(headimgurl.split('/')[:-1]) + '/0'
            return download_file(url = headimgurl)
        return None

    def poll(self):
        timer = threading.Event()
        self.check_status(timer)

        cron_timer = threading.Event()
        self.cron_update_task(cron_timer)

        t = threading.Thread(target=self.bot.run)
        t.daemon = True
        t.start()

    def send_status(self, status: 'Status'):
        pass

    def stop_polling(self):
        pass

    def get_message_by_id(self, chat: 'Chat', msg_id: MessageID) -> Optional['Message']:
        pass

    #更新好友信息
    def update_friend_info(self):
        self.info_dict['chat'] = {}
        self.info_dict['friend'] = {}
        self.logger.debug('Fetching friend list...')
        self.get_friend_list()
        self.get_group_list()
        return self.process_friend_info() + self.process_group_info()

    def update_group_member_info(self, group_id: str):
        group_members = self.get_group_members_list( group_id )
        if not group_members:
            return

        self.group_member_info[group_id] = {}
        for group_member in group_members:
            self.group_member_info[group_id][group_member['wxid']] = {}
            self.group_member_info[group_id][group_member['wxid']]['group_nickname'] = group_member['group_nickname']
            self.group_member_info[group_id][group_member['wxid']]['nickname'] = group_member['nickname']

    #处理 好友 群组 信息
    def process_group_info(self):
        groups = []
        if not self.info_list['group']:
            self.logger.error('No group info , Check your config file')
            return []

        for group in self.info_list['group']:
            nickname = group['nickname']
            group_wxid = group['wxid']
            self.info_dict['friend'][group_wxid] = {}
            self.info_dict['friend'][group_wxid]['nickname'] = nickname
            new_entity = EFBGroupChat(
                    uid=group_wxid,
                    name=nickname
            )
            groups.append(ChatMgr.build_efb_chat_as_group(new_entity))
            self.info_dict['chat'][group_wxid] = new_entity
        return groups

    def process_friend_info(self):
        friends = []
        if not self.info_list['friend']:
            self.logger.error('No friend info , Check your config file')
            return []

        for friend in self.info_list['friend']:
            nickname = friend['nickname']
            #尝试支持可爱猫5.5.4
            try:
                remark = friend['remark']
            except:
                remark = friend['note']
            wxid = friend['wxid']
            self.info_dict['friend'][wxid] = {}
            self.info_dict['friend'][wxid]['nickname'] = nickname
            self.info_dict['friend'][wxid]['remark'] = remark

            new_entity = EFBPrivateChat(
                uid=friend['wxid'],
                name=nickname,
                alias=remark,
            )
            friends.append(ChatMgr.build_efb_chat_as_private(new_entity))
            self.info_dict['chat'][wxid] = new_entity
        new_entity = EFBPrivateChat(
            uid= self.robot_wxid,
            name= 'WeChat_Robot'
        )
        self.info_dict['chat'][self.robot_wxid] = new_entity
        return friends

    #获取好友
    def get_friend_list(self):
        friend_list = self.bot.GetFriendList()
        if friend_list:
            self.info_list['friend'] = friend_list.get('data', None)
        else:
            self.info_list['friend'] = []

    def get_group_list(self):
        group_list = self.bot.GetGroupList()
        if group_list:
            self.info_list['group'] = group_list.get('data', None)
        else:
            self.info_list['group'] = []

    def get_group_members_list(self , group_wxid):
        group_member_list = self.bot.GetGroupMemberList(group_wxid = group_wxid)
        if group_member_list:
            return group_member_list.get('data', None)
        else:
            return []

    def get_group_member_info(self , item ,member_wxid ):
        group_member_info = self.bot.GetGroupMemberInfo( member_wxid = member_wxid)
        try:
            return group_member_info.get('data').get(item)
        except:
            return None

    def get_group_member_nameinfo(self , item : str ,  group_wxid : str , member_wxid : str ):
        if self.group_member_info.get(group_wxid) == None:
            self.update_group_member_info(group_wxid)
        if self.group_member_info.get(group_wxid) == None:   #'''update failed'''
            return None
        if self.group_member_info[group_wxid].get(member_wxid , None) == None:
            return None
        return self.group_member_info[group_wxid][member_wxid][item] if self.group_member_info[group_wxid][member_wxid][item] else None

    def get_friend_info(self, item: str, wxid: str) -> Union[None, str]:
        if self.info_dict.get('friend', None) == None:
            return None
        if wxid not in self.info_dict['friend']:
            return None
        return self.info_dict['friend'][wxid].get(item, None)
