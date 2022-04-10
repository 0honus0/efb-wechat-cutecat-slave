from typing import Mapping, Tuple, Union, IO
import magic
from lxml import etree
from traceback import print_exc

from ehforwarderbot import MsgType, Chat
from ehforwarderbot.chat import ChatMember
from ehforwarderbot.message import Substitutions, Message, LinkAttribute, LocationAttribute


def efb_text_simple_wrapper(text: str, ats: Union[Mapping[Tuple[int, int], Union[Chat, ChatMember]], None] = None) -> Message:
    """
    A simple EFB message wrapper for plain text. Emojis are presented as is (plain text).
    :param text: The content of the message
    :param ats: The substitutions of at messages, must follow the Substitution format when not None
                [[begin_index, end_index], {Chat or ChatMember}]
    :return: EFB Message
    """
    efb_msg = Message(
        type=MsgType.Text,
        text=text
    )
    if ats:
        efb_msg.substitutions = Substitutions(ats)
    return efb_msg


def efb_image_wrapper(file: IO, filename: str = None, text: str = None) -> Message:
    """
    A EFB message wrapper for images.
    :param file: The file handle
    :param filename: The actual filename
    :param text: The attached text
    :return: EFB Message
    """
    efb_msg = Message()
    efb_msg.file = file
    mime = magic.from_file(file.name, mime=True)
    if isinstance(mime, bytes):
        mime = mime.decode()

    if "gif" in mime:
        efb_msg.type = MsgType.Animation
    else:
        efb_msg.type = MsgType.Image

    if filename:
        efb_msg.filename = filename
    else:
        efb_msg.filename = file.name
        efb_msg.filename += '.' + str(mime).split('/')[1]  # Add extension suffix

    if text:
        efb_msg.text = text

    efb_msg.path = efb_msg.file.name
    efb_msg.mime = mime
    return efb_msg

def efb_video_wrapper(file: IO, filename: str = None, text: str = None) -> Message:
    """
    A EFB message wrapper for voices.
    :param file: The file handle
    :param filename: The actual filename
    :param text: The attached text
    :return: EFB Message
    """
    efb_msg = Message()
    efb_msg.type = MsgType.Video
    efb_msg.file = file
    mime = magic.from_file(file.name, mime=True)
    if isinstance(mime, bytes):
        mime = mime.decode()
    if filename:
        efb_msg.filename = filename
    else:
        efb_msg.filename = file.name
        efb_msg.filename += '.' + str(mime).split('/')[1]  # Add extension suffix
    efb_msg.path = efb_msg.file.name
    efb_msg.mime = mime
    if text:
        efb_msg.text = text
    return efb_msg

def efb_file_wrapper(file: IO, filename: str = None, text: str = None) -> Message:
    """
    A EFB message wrapper for voices.
    :param file: The file handle
    :param filename: The actual filename
    :param text: The attached text
    :return: EFB Message
    """
    efb_msg = Message()
    efb_msg.type = MsgType.File
    efb_msg.file = file
    mime = magic.from_file(file.name, mime=True)
    if isinstance(mime, bytes):
        mime = mime.decode()
    if filename:
        efb_msg.filename = filename
    else:
        efb_msg.filename = file.name
        efb_msg.filename += '.' + str(mime).split('/')[1]  # Add extension suffix
    efb_msg.path = efb_msg.file.name
    efb_msg.mime = mime
    if text:
        efb_msg.text = text
    return efb_msg


def efb_share_link_wrapper(text: str) -> Tuple[Message]:
    """
    处理msgType49消息 - 复合xml, xml 中 //appmsg/type 指示具体消息类型.
    /msg/appmsg/type
    已知：
    //appmsg/type = 5 : 链接（公众号文章）
    //appmsg/type = 17 : 实时位置共享
    //appmsg/type = 19 : 合并转发的聊天记录
    //appmsg/type = 21 : 微信运动
    //appmsg/type = 74 : 文件 (收到文件的第一个提示)
    //appmsg/type = 6 : 文件 （收到文件的第二个提示【文件下载完成】)，也有可能 msgType = 10000 【【提示文件有风险】没有任何有用标识，无法判断是否与前面哪条消息有关联】
    //appmsg/type = 57 : 【感谢 @honus 提供样本 xml】引用(回复)消息，未细致研究哪个参数是被引用的消息 id 
    :param text: The content of the message
    :return: EFB Message
    """

    xml = etree.fromstring(text)
    efb_msgs = []
    result_text = ""
    try: 
        type = int(xml.xpath('/msg/appmsg/type/text()')[0])

        if type == 5: # xml链接
            showtype = int(xml.xpath('/msg/appmsg/showtype/text()')[0])
            if showtype == 0: # 消息对话中的(测试的是从公众号转发给好友, 不排除其他情况)
                title = url = des = thumburl = None # 初始化
                try:
                    title = xml.xpath('/msg/appmsg/title/text()')[0]
                    url = xml.xpath('/msg/appmsg/url/text()')[0]
                    if len(xml.xpath('/msg/appmsg/des/text()'))!=0:
                        des = xml.xpath('/msg/appmsg/des/text()')[0]
                    if len(xml.xpath('/msg/appmsg/thumburl/text()'))!=0:
                        thumburl = xml.xpath('/msg/appmsg/thumburl/text()')[0]

                    sourceusername = xml.xpath('/msg/appmsg/sourceusername/text()')[0]
                    sourcedisplayname = xml.xpath('/msg/appmsg/sourcedisplayname/text()')[0]
                    result_text += f"\n转发自公众号【{sourcedisplayname}(id: {sourceusername})】\n\n"
                except Exception as e:
                    print_exc()
                if title is not None and url is not None:
                    attribute = LinkAttribute(
                        title=title,
                        description=des,
                        url=url,
                        image=thumburl
                    )
                    efb_msg = Message(
                        attributes=attribute,
                        type=MsgType.Link,
                        text=result_text,
                        vendor_specific={ "is_mp": True }
                    )
                    efb_msgs.append(efb_msg)
            elif showtype == 1: # 公众号发的推送
                items = xml.xpath('//item')
                for item in items:
                    title = url = digest = cover = None # 初始化
                    try:
                        title = item.find("title").text
                        url = item.find("url").text
                        digest = item.find("digest").text
                        cover = item.find("cover").text
                    except Exception as e:
                        print_exc()
                    if title is not None and url is not None:
                        attribute = LinkAttribute(
                            title=title,
                            description=digest,
                            url=url,
                            image=cover
                        )
                        efb_msg = Message(
                            attributes=attribute,
                            type=MsgType.Link,
                            text=result_text,
                            vendor_specific={ "is_mp": True }
                        )
                        efb_msgs.append(efb_msg)
        elif type == 19: # 合并转发的聊天记录
            msg_title = xml.xpath('/msg/appmsg/title/text()')[0]
            forward_content = xml.xpath('/msg/appmsg/des/text()')[0]
            result_text += f"{forward_content}\n\n{msg_title}"
            efb_msg = Message(
                type=MsgType.Text,
                text=result_text,
                vendor_specific={ "is_forwarded": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 21: # 微信运动
            msg_title = xml.xpath('/msg/appmsg/title/text()')[0].strip("<![CDATA[夺得").strip("冠军]]>")
            rank = xml.xpath('/msg/appmsg/hardwareinfo/messagenodeinfo/rankinfo/rank/rankdisplay/text()')[0].strip("<![CDATA[").strip("]]>")
            steps = xml.xpath('/msg/appmsg/hardwareinfo/messagenodeinfo/rankinfo/score/scoredisplay/text()')[0].strip("<![CDATA[").strip("]]>")
            result_text += f"{msg_title}\n\n排名：{rank}\n步数：{steps}"
            efb_msg = Message(
                type=MsgType.Text,
                text=result_text,
                vendor_specific={ "is_wechatsport": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 57: # 引用（回复）消息
            msg = xml.xpath('/msg/appmsg/title/text()')[0]
            refer_msgType = int(xml.xpath('/msg/appmsg/refermsg/type/text()')[0]) # 被引用消息类型
            # refer_fromusr = xml.xpath('/msg/appmsg/refermsg/fromusr/text()')[0] # 被引用消息所在房间
            # refer_fromusr = xml.xpath('/msg/appmsg/refermsg/chatusr/text()')[0] # 被引用消息发送人微信号
            refer_displayname = xml.xpath('/msg/appmsg/refermsg/displayname/text()')[0] # 被引用消息发送人微信名称
            refer_content = xml.xpath('/msg/appmsg/refermsg/content/text()')[0] # 被引用消息内容
            if refer_msgType == 1: # 被引用的消息是文本
                result_text += f"「{refer_displayname}:\n{refer_content}」\n\n{msg}"
            else: # 被引用的消息非文本，提示不支持
                result_text += f"「{refer_displayname}:\n系统消息：被引用的消息不是文本，暂不支持展示」\n\n{msg}"
            efb_msg = Message(
                type=MsgType.Text,
                text=result_text,
                vendor_specific={ "is_refer": True }
            )
            efb_msgs.append(efb_msg)
    except Exception as e:
        print_exc()

    if efb_msgs == []:
        efb_msg = Message(
            type=MsgType.Text,
            text=text
        )
        efb_msgs.append(efb_msg)

    return tuple(efb_msgs)



def efb_location_wrapper(self, msg: str) -> Message:
    efb_msg = Message()
    '''msg = ast.literal_eval(text)'''
    efb_msg.text = msg['desc']
    efb_msg.attributes = LocationAttribute(latitude=float(msg['x']),
                                           longitude=float(msg['y']))
    efb_msg.type = MsgType.Location
    return efb_msg
