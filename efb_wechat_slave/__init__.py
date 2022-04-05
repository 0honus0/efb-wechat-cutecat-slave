import logging
import queue
import threading
import uuid
from traceback import print_exc

import yaml
import hashlib
from ehforwarderbot.chat import PrivateChat
from pyqrcode import QRCode
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
    'text' : MsgProcessor.text_msg,
    'image' : MsgProcessor.image_msg,
    'video' : MsgProcessor.video_msg,
    'share' : MsgProcessor.share_link_msg,
    'location' : MsgProcessor.location_msg
}

import sys

class CuteCatChannel(SlaveChannel):
    channel_name: str = "Wechat Pc Slave"
    channel_emoji: str = "📱"
    channel_id = "honus.CuteCatiHttp"

    config: Dict[str, Any] = {}

    # info_list = TTLCache(maxsize=2, ttl=600)
    # info_dict = TTLCache(maxsize=2, ttl=600)
    # info_list = TTLCache(maxsize=2, ttl=600)
    # info_dict = TTLCache(maxsize=2, ttl=600)

    info_list = {}
    info_dict = {}

    info_list['chat'] = []
    info_dict['chat'] = {}
    info_dict['friend'] = {}

    update_friend_event = threading.Event()
    update_friend_lock = threading.Lock()

    __version__ = version.__version__

    logger: logging.Logger = logging.getLogger("plugins.%s.CuteCatiHttp" % channel_id)

    logger.setLevel(logging.DEBUG)

    supported_message_types = {MsgType.Text, MsgType.Sticker, MsgType.Image,
                                MsgType.Link, MsgType.Voice, MsgType.Animation}

    def __init__(self, instance_id: InstanceID = None):
        super().__init__(instance_id)

        self.load_config()
        if 'api_root' not in self.config:
            raise EFBException("api_root not found in config")
        if 'robot_wxid' not in self.config:
            raise EFBException("robot_wxid not found in config")
        self.api_root = self.config['api_root']
        robot_wxid = self.config['robot_wxid']
        access_token = self.config.get('access_token',None)

        self.bot = CuteCat(api_root = self.api_root, robot_wxid = robot_wxid, access_token = access_token)

        ChatMgr.slave_channel = self

        @self.bot.on('EventGroupMsg')
        def on_group_msg(msg: Dict[str, Any]):
            print(msg)

            group_wxid = msg['from_wxid']
            group_name = msg['from_name']

            username = msg['final_from_name']
            userwxid = msg['final_from_wxid']
            chat = None
            author = None
            chat = ChatMgr.build_efb_chat_as_group(EFBGroupChat(
                    uid= group_wxid,
                    name=group_name or group_wxid
            ))

            remark = self.get_friend_info('remark', userwxid)
            author = ChatMgr.build_efb_chat_as_member(chat, EFBGroupMember(
                    name=remark or username or userwxid,
                    alias= username, 
                    uid=userwxid
            ))

            if msg['type'] in TYPE_HANDLERS:
                if msg['type'] in ['video', 'image', 'share', 'location']:
                    efb_msg = TYPE_HANDLERS[msg['type']](msg , self.api_root)
                else:
                    efb_msg = TYPE_HANDLERS['text'](msg)
            else:
                 efb_msg = TYPE_HANDLERS['text'](msg)
            efb_msg.author = author
            efb_msg.chat = chat
            efb_msg.deliver_to = coordinator.master
            coordinator.send_message(efb_msg)
        
        @self.bot.on('EventFriendMsg')
        def on_friend_msg(msg: Dict[str, Any]):
            print(msg)

            name = msg['final_from_name']
            wxid = msg['final_from_wxid']
            chat = None
            auther = None
            chat = ChatMgr.build_efb_chat_as_private(EFBPrivateChat(
                    uid=wxid,
                    name= name or wxid,
            ))
            author = chat.other

            # if 'type' in msg and msg['msgType'] in TYPE_HANDLERS:
            #     efb_msg = TYPE_HANDLERS[msg['msgType']](msg)

            if msg['type'] in TYPE_HANDLERS:
                if msg['type'] in ['video', 'image', 'share', 'location']:
                    efb_msg = TYPE_HANDLERS[msg['type']](msg , self.api_root)
                else:
                    efb_msg = TYPE_HANDLERS['text'](msg)
            else:
                 efb_msg = TYPE_HANDLERS['text'](msg)
            efb_msg.author = author
            efb_msg.chat = chat
            efb_msg.deliver_to = coordinator.master
            coordinator.send_message(efb_msg)

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
        if 'chat' not in self.info_list or not self.info_list['chat']:
            self.logger.debug("Chat list is empty. Fetching...")
            self.update_friend_info()
        return self.info_list['chat']

#获取联系人
    def get_chat(self, chat_uid: ChatID) -> 'Chat':
        if 'chat' not in self.info_list or not self.info_list['chat']:
            self.logger.debug("Chat list is empty. Fetching...")
            self.update_friend_info()
        for chat in self.info_list['chat']:
            if chat_uid == chat.uid:
                return chat
        return None

#发送消息
    def send_message(self, msg : Message) -> Message:
        chat_uid = msg.chat.uid

        if msg.edit:
            pass  # todo

        if msg.type in [MsgType.Text]:
            self.bot.SendTextMsg(to_wxid=chat_uid,msg=msg.text)

        return msg

#to do
    def get_chat_picture(self, chat: 'Chat') -> BinaryIO:
        pass

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
        with self.update_friend_lock:
            if 'friend' in self.info_list and self.info_list['friend']:
                return
            self.logger.info('Fetching friend list...')
            self.get_all_info()
            self.process_friend_info()
            self.process_group_info()

#获取全部好友信息
    def get_all_info(self):
        self.get_friend_list()
        self.get_group_list()

#处理不同好友信息
    def process_group_info(self):
        group = []
        for group in self.info_list['group']:
            nickname = group['nickname']
            group_wxid = group['wxid']
            self.info_dict['friend'][group_wxid] = {}
            self.info_dict['friend'][group_wxid]['nickname'] = nickname
            new_entity = EFBGroupChat(
                    uid=group_wxid,
                    name=nickname
            )
            self.info_list['chat'].append(ChatMgr.build_efb_chat_as_group(new_entity))
            self.info_dict['chat'][group_wxid] = new_entity

    def process_friend_info(self):
        friend = []
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
            self.info_list['chat'].append(ChatMgr.build_efb_chat_as_private(new_entity))
            self.info_dict['chat'][wxid] = new_entity

    def process_group_members_info(self):
        group_member = []
        for group_member in self.info_list['group_member']:
            self.info_dict['group_member'][group_member['wxid']]['group_nickname'] = group_member['group_nickname']
            self.info_dict['group_member'][group_member['wxid']]['nickname'] = group_member['nickname']

#获取好友
    def get_friend_list(self):
        friend_list = self.bot.GetFriendList()
        if friend_list:
            self.info_list['friend'] = friend_list.get('data',None)

    def get_group_list(self):
        group_list = self.bot.GetGroupList()
        if group_list:
            self.info_list['group'] = group_list.get('data',None)

    def get_group_members_list(self , group_wxid):
        group_member_list = self.bot.GetGroupMemberList(group_wxid = group_wxid)
        (self.info_list['group_members']).extend(group_member_list.get('data',[None]))

    def get_friend_info(self, item: str, wxid: int) -> Union[None, str]:
        if not self.info_dict.get('friend', None) or wxid not in self.info_dict['friend']:
            return None
        return self.info_dict['friend'][wxid].get(item, None)    
