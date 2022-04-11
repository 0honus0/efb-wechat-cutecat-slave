import logging
import threading
from traceback import print_exc

import yaml
import re
from ehforwarderbot.chat import PrivateChat
from typing import Optional, Collection, BinaryIO, Dict, Any , Union
from datetime import datetime

from ehforwarderbot import MsgType, Chat, Message, Status, coordinator
from CuteCat import CuteCat

from . import __version__ as version

from ehforwarderbot.channel import SlaveChannel
from ehforwarderbot.types import MessageID, ChatID, InstanceID
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.exceptions import EFBException
from cachetools import TTLCache

from .ChatMgr import ChatMgr
from .CustomTypes import EFBGroupChat, EFBPrivateChat, EFBGroupMember
from .MsgDecorator import efb_text_simple_wrapper
from .WechatPcMsgProcessor import MsgProcessor
from .utils import process_quote_text, download_file

TYPE_HANDLERS = {
    'text'            : MsgProcessor.text_msg,
    'image'           : MsgProcessor.image_msg,
    'video'           : MsgProcessor.video_msg,
    'share'           : MsgProcessor.share_link_msg,
    'location'        : MsgProcessor.location_msg,
    'other'           : MsgProcessor.other_msg,
    'animatedsticker' : MsgProcessor.image_msg,
    'unsupported'     : MsgProcessor.unsupported_msg,
    'revokemsg'       : MsgProcessor.revoke_msg,
}

class CuteCatChannel(SlaveChannel):
    channel_name: str = "Wechat Pc Slave"
    channel_emoji: str = "📱"
    channel_id = "honus.CuteCatiHttp"

    config: Dict[str, Any] = {}

    info_list = TTLCache(maxsize=2, ttl=600)
    info_dict = TTLCache(maxsize=2, ttl=600)

    group_member_info = TTLCache(maxsize= 10000 ,ttl=3600)

    update_friend_event = threading.Event()

    __version__ = version.__version__

    logger: logging.Logger = logging.getLogger("plugins.%s.CuteCatiHttp" % channel_id)

    logger.setLevel(logging.DEBUG)

    supported_message_types = {MsgType.Text, MsgType.Sticker, MsgType.Image, MsgType.Video,
                                MsgType.File, MsgType.Link, MsgType.Voice, MsgType.Animation}

    def __init__(self, instance_id: InstanceID = None):
        super().__init__(instance_id)

        self.load_config()
        if 'api_url' not in self.config:
            raise EFBException("api_url not found in config")
        if 'robot_wxid' not in self.config:
            raise EFBException("robot_wxid not found in config")
        self.api_url = self.config['api_url']
        self.robot_wxid = self.config['robot_wxid']
        self.self_url = self.config['self_url']
        access_token = self.config.get('access_token',None)

        self.bot = CuteCat(api_url = self.api_url, robot_wxid = self.robot_wxid, access_token = access_token)

        ChatMgr.slave_channel = self
        @self.bot.on('EventSendOutMsg')
        def on_self_msg(msg: Dict[str, Any]):
            print(msg)
            if not self.config.get('receive_self_msg',False):
                return

            efb_msgs = []
            if msg['type'] == 'taptap' and '语音聊天' not in msg['msg']:
                to_wxid = msg['to_wxid']
                name = self.get_friend_info('nickname' , to_wxid)
                remark = self.get_friend_info('remark' , to_wxid)
                chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid= to_wxid ,
                    name= remark or name or msg['msg'].split('拍了拍')[0]
                ))
                author = chat.other
                self.handle_msg( msg = msg , author = author , chat = chat)
            elif msg['final_from_wxid'] == self.robot_wxid:
                chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid= msg['final_from_wxid'],
                    name= 'My_Robot'
                ))
                author = chat.other
                self.handle_msg( msg = msg , author = author , chat = chat)

        @self.bot.on('EventGroupMsg')
        def on_group_msg(msg: Dict[str, Any]):
            print(msg)

            group_wxid = msg['from_wxid']
            group_name = msg['from_name']

            userwxid = msg['final_from_wxid'] or group_wxid
            username = msg['final_from_name'] or group_name

            group_nick_name = None
            if not self.group_member_info.get(group_wxid , None):
                self.update_group_member_info(group_wxid)
            if self.group_member_info[group_wxid].get(userwxid , None):
                group_nick_name = self.group_member_info[group_wxid][userwxid]

            chat = None
            author = None
            chat = ChatMgr.build_efb_chat_as_group(EFBGroupChat(
                    uid= group_wxid,
                    name=group_name or group_wxid
            ))

            remark = self.get_friend_info('remark', userwxid)
            author = ChatMgr.build_efb_chat_as_member(chat, EFBGroupMember(
                    name = remark or username ,
                    alias = (group_nick_name if group_nick_name != remark else None) or (username if remark != None else None) ,
                    uid = userwxid
            ))

            self.handle_msg( msg = msg , author = author , chat = chat)
        
        @self.bot.on('EventFriendMsg')
        def on_friend_msg(msg: Dict[str, Any]):
            print(msg)

            name = msg['final_from_name']
            wxid = msg['final_from_wxid']
            chat = None
            auther = None
            remark = self.get_friend_info('remark', wxid)
            chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid=wxid,
                    name= remark or name or wxid,
            ))
            author = chat.other

            self.handle_msg( msg = msg , author = author , chat = chat)

        #系统消息 暂时未发现该类有通知
        def on_sys_msg(msg : Dict[str, Any]):
            print(msg)

        @self.bot.on('EventFriendVerify')
        def on_friend_verify(msg : Dict[str, Any]):
            print(msg)
        
        @self.bot.on('EventReceivedTransfer')
        def on_transfer(msg : Dict[str, Any]):
            print(msg)

        @self.bot.on('EventScanCashMoney')
        def on_scan_cash_money(msg : Dict[str, Any]):
            print(msg)

    def handle_msg(self , msg : Dict[str, Any] , author : 'ChatMember' , chat : 'Chat'):
        efb_msgs = []
        if msg['type'] == 'share':
            # 判断分享的是文件类型
            if '/WeChat/savefiles/' in msg['msg']:
                efb_msgs.append(MsgProcessor.file_msg(msg))
            else:
                efb_msgs = tuple(TYPE_HANDLERS[msg['type']](msg))
        elif msg['type'] in ['video', 'image', 'location' , 'animatedsticker' , 'other' , 'revokemsg']:
            efb_msg = TYPE_HANDLERS[msg['type']](msg)
            efb_msgs.append(efb_msg) if efb_msg else efb_msgs
        elif msg['type'] in ['miniprogram' , 'voip']:
            efb_msgs.append(TYPE_HANDLERS['unsupported'](msg))
        else:
            efb_msgs.append(TYPE_HANDLERS['text'](msg , chat))

        for efb_msg in efb_msgs:
            efb_msg.author = author
            efb_msg.chat = chat
            efb_msg.deliver_to = coordinator.master
            coordinator.send_message(efb_msg)
            if efb_msg.file:
                efb_msg.file.close()

#从本地读取配置
    def load_config(self):
        """
        Load configuration from path specified by the framework.
        Configuration file is in YAML format.
        """
        config_path = efb_utils.get_config_path(self.channel_id)
        if not config_path.exists():
            return
        with config_path.open() as f:
            d = yaml.full_load(f)
            if not d:
                return
            self.config: Dict[str, Any] = d

#获取全部联系人
    def get_chats(self) -> Collection['Chat']:
        return self.update_friend_info()

#获取联系人
    def get_chat(self, chat_uid: ChatID) -> 'Chat':
        if 'chat' not in self.info_list or not self.info_list['chat']:
            self.logger.debug("Chat list is empty. Fetching...")
            self.update_friend_info()
        for chat in self.info_dict['chat']:
            if chat_uid == chat:
                if '@chatroom' in chat:
                    return ChatMgr.build_efb_chat_as_group(self.info_dict['chat'][chat_uid])
                else:
                    return ChatMgr.build_efb_chat_as_private(self.info_dict['chat'][chat_uid])
        return None

#发送消息
    def send_message(self, msg : Message) -> Message:
        chat_uid = msg.chat.uid

        if msg.edit:
            pass  # todo

        try:
            filename = msg.file.name.split('/')[-1] if msg.file else msg.file.name
            temp_msg = {'name' : filename , 'url': self.self_url + msg.file.name}
        except:
            pass

        if msg.type in [MsgType.Text , MsgType.Link]:
            self.bot.SendTextMsg( to_wxid=chat_uid , msg=msg.text)
        elif msg.type in [MsgType.Image , MsgType.Sticker]:
            data = self.bot.SendImageMsg( to_wxid=chat_uid , msg = temp_msg) or {}
        elif msg.type in [MsgType.File]:
            data = self.bot.SendFileMsg( to_wxid=chat_uid , msg = temp_msg) or {}
        elif msg.type in [MsgType.Video , MsgType.Animation]:
            data = self.bot.SendVideoMsg( to_wxid=chat_uid , msg = temp_msg) or {}

        if self.config.get('receive_self_msg',False):
            if msg.type in [MsgType.Video , MsgType.Animation , MsgType.Image , MsgType.Sticker , MsgType.File]:
                temp_msg = ("%s Send Success" % msg.type) if data.get('code') >= 0 else ("%s Send Failed" % msg.type)
                self.bot.SendTextMsg( to_wxid= self.robot_wxid , msg= temp_msg)
            return msg
 
        return msg

#to do
    def get_chat_picture(self, chat: 'Chat') -> BinaryIO:
        wxid = chat.uid
        user_info = self.get_group_member_info(wxid)
        if user_info:
            headimgurl =  user_info.get('headimgurl' , None)
            if headimgurl:
                return download_file(url = headimgurl)
        return None

    def poll(self):
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
        if 'friend' in self.info_list and self.info_list['friend']:
            return
        self.info_dict['chat'] = {}
        self.info_dict['friend'] = {}
        self.logger.info('Fetching friend list...')
        self.get_all_info()
        friend_info = self.process_friend_info()
        group_info = self.process_group_info()
        return friend_info + group_info

    def update_group_member_info(self, group_id: str):
        group_members = self.get_group_members_list( group_id )
        if not group_members:
            return
        self.group_member_info[group_id] = {}
        for group_member in group_members:
            if group_member['group_nickname']:
                self.group_member_info[group_id][group_member['wxid']] = group_member['group_nickname']


#获取全部好友信息
    def get_all_info(self):
        self.get_friend_list()
        self.get_group_list()

#处理不同好友信息
    def process_group_info(self):
        groups = []
        if not self.info_list['group']:
            self.logger.error('No group info , Check your config file')

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

        for friend in self.info_list['friend']:
            nickname = friend['nickname']
            remark = friend['remark']
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

    def process_group_members_info(self):
        group_member = []
        for group_member in self.info_list['group_member']:
            self.info_dict['group_member'][group_member['wxid']]['group_nickname'] = group_member['group_nickname']
            self.info_dict['group_member'][group_member['wxid']]['nickname'] = group_member['nickname']

#获取好友
    def get_friend_list(self):
        friend_list = self.bot.GetFriendList()
        self.info_list['friend'] = friend_list.get('data', None)

    def get_group_list(self):
        group_list = self.bot.GetGroupList()
        self.info_list['group'] = group_list.get('data', None)

    def get_group_members_list(self , group_wxid):
        group_member_list = self.bot.GetGroupMemberList(group_wxid = group_wxid)
        return group_member_list.get('data', None)

    def get_group_member_info(self , member_wxid ):
        group_member_info = self.bot.GetGroupMemberInfo( member_wxid = member_wxid)
        return group_member_info.get('data', None)

    def get_friend_info(self, item: str, wxid: int) -> Union[None, str]:
        if not self.info_dict.get('friend', None):
            self.update_friend_info()
        if not self.info_dict['friend'].get(wxid, None):
            return None
        return self.info_dict['friend'][wxid].get(item, None)    
