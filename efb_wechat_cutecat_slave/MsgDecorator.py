from typing import Mapping, Tuple, Union, IO
import magic
from lxml import etree
from traceback import print_exc
import re

from ehforwarderbot import MsgType, Chat
from ehforwarderbot.chat import ChatMember
from ehforwarderbot.message import Substitutions, Message, LinkAttribute, LocationAttribute

from .utils import emoji_wechat2telegram

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

def efb_text_delete_wrapper(text: str, ats: Union[Mapping[Tuple[int, int], Union[Chat, ChatMember]], None] = None) -> Message:
    """
    A simple EFB message wrapper for plain text. Emojis are presented as is (plain text).
    :param text: The content of the message
    :param ats: The substitutions of at messages, must follow the Substitution format when not None
                [[begin_index, end_index], {Chat or ChatMember}]
    :return: EFB Message
    """
    efb_msg = Message(
        type=MsgType.Text,
        text=text,
        attributes={'parse_mode': 'Markdown'}
    )
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
    ??????msgType49?????? - ??????xml, xml ??? //appmsg/type ????????????????????????.
    /msg/appmsg/type
    ?????????
    //appmsg/type = 1 : ??????????????????????????????
    //appmsg/type = 2 : ????????????
    //appmsg/type = 3 : ????????????
    //appmsg/type = 4 : ???????????????????????????
    //appmsg/type = 5 : ???????????????????????????
    //appmsg/type = 6 : ?????? ?????????????????????????????????????????????????????????)??????????????? msgType = 10000 ????????????????????????????????????????????????????????????????????????????????????????????????????????????
    //appmsg/type = 8 : ?????????????????????
    //appmsg/type = 17 : ??????????????????
    //appmsg/type = 19 : ???????????????????????????
    //appmsg/type = 21 : ????????????
    //appmsg/type = 24 : ???????????????????????????
    //appmsg/type = 35 : ????????????
    //appmsg/type = 36 : ????????????
    //appmsg/type = 51 : ?????????????????????????????????
    //appmsg/type = 53 : ????????????????????????
    //appmsg/type = 57 : ????????? @honus ???????????? xml?????????(??????)????????????????????????????????????????????????????????? id 
    //appmsg/type = 63 : ?????????????????????????????????
    //appmsg/type = 74 : ?????? (??????????????????????????????)
    :param text: The content of the message
    :return: EFB Message
    """

    xml = etree.fromstring(text)
    efb_msgs = []
    result_text = ""
    try: 
        type = int(xml.xpath('/msg/appmsg/type/text()')[0])
        if type in [ 1 , 2 ]:
            title = xml.xpath('/msg/appmsg/title/text()')[0]
            des = xml.xpath('/msg/appmsg/des/text()')[0]
            efb_msg = Message(
                type = MsgType.Text,
                text = title if title==des else title+" :\n"+des,
            )
            efb_msgs.append(efb_msg)
        elif type == 3: #????????????
            try:
                music_name = xml.xpath('/msg/appmsg/title/text()')[0]
                music_singer = xml.xpath('/msg/appmsg/des/text()')[0]
            except:
                efb_msg = Message(
                    type = MsgType.Text,
                    text = "- - - - - - - - - - - - - - - \n?????????????????????",
                )
            try:
                thumb_url = xml.xpath('/msg/appmsg/url/text()')[0]
                attribute = LinkAttribute(
                    title = music_name + ' / ' + music_singer,
                    description = None,
                    url = thumb_url ,
                    image = None
                )
                efb_msg = Message(
                    attributes=attribute,
                    type=MsgType.Link,
                    text= None,
                    vendor_specific={ "is_mp": True }
                )
            except:
                pass
            efb_msgs.append(efb_msg)
        elif type in [ 4 , 36 ]: # ??????????????????????????? , ????????????
            title = xml.xpath('/msg/appmsg/title/text()')[0]
            des = xml.xpath('/msg/appmsg/des/text()')[0]
            url = xml.xpath('/msg/appmsg/url/text()')[0]
            app = xml.xpath('/msg/appinfo/appname/text()')[0]
            description = f"{des}\n---- from {app}"
            attribute = LinkAttribute(
                title = title,
                description = description,
                url = url ,
                image = None
            )
            efb_msg = Message(
                attributes=attribute,
                type=MsgType.Link,
                text= None,
                vendor_specific={ "is_mp": False }
            )
            efb_msgs.append(efb_msg)
        elif type == 5: # xml??????
            showtype = int(xml.xpath('/msg/appmsg/showtype/text()')[0])
            if showtype == 0: # ??????????????????(???????????????????????????????????????, ?????????????????????)
                title = url = des = thumburl = None # ?????????
                try:
                    title = xml.xpath('/msg/appmsg/title/text()')[0]
                    print(title)
                    if '<' in title and '>' in title:
                        subs = re.findall('<[\s\S]+?>', title)
                        print(subs)
                        for sub in subs:
                            title = title.replace(sub, '')
                    url = xml.xpath('/msg/appmsg/url/text()')[0]
                    if len(xml.xpath('/msg/appmsg/des/text()'))!=0:
                        des = xml.xpath('/msg/appmsg/des/text()')[0]
                    if len(xml.xpath('/msg/appmsg/thumburl/text()'))!=0:
                        thumburl = xml.xpath('/msg/appmsg/thumburl/text()')[0]
                    if len(xml.xpath('/msg/appinfo/appname/text()'))!=0:
                        app = xml.xpath('/msg/appinfo/appname/text()')[0]
                        des = f"{des}\n---- from {app}"

                    if len(xml.xpath('/msg/appmsg/sourceusername/text()'))!=0:
                        sourceusername = xml.xpath('/msg/appmsg/sourceusername/text()')[0]
                        sourcedisplayname = xml.xpath('/msg/appmsg/sourcedisplayname/text()')[0]
                        result_text += f"\n?????????????????????{sourcedisplayname}(id: {sourceusername})???\n\n"
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
            elif showtype == 1: # ?????????????????????
                items = xml.xpath('//item')
                for item in items:
                    title = url = digest = cover = None # ?????????
                    try:
                        title = item.find("title").text
                        url = item.find("url").text
                        digest = item.find("digest").text
                        cover = item.find("cover").text
                    except Exception as e:
                        print_exc()
                    
                    if '@app' in text:
                        name = xml.xpath('//publisher/nickname/text()')[0]
                        digest += f"\n- - - - from {name}"
                    if title and url:
                        attribute = LinkAttribute(
                            title=title,
                            description=digest,
                            url=url,
                            image= cover,
                        )
                        efb_msg = Message(
                            attributes=attribute,
                            type=MsgType.Link,
                            text=result_text,
                            vendor_specific={ "is_mp": True }
                        )
                    else: # ???????????????????????????url??????
                        result_text += f"{title}\n  - - - - - - - - - - - - - - - \n{digest}"
                        efb_msg = Message(
                            type=MsgType.Text,
                            text=result_text
                        )
                    efb_msgs.append(efb_msg)
        elif type == 8:
            efb_msg = Message(
                type=MsgType.Unsupported,
                text='????????????????????? ????????????????????????',
            )
            efb_msgs.append(efb_msg)
        elif type == 19: # ???????????????????????????
            msg_title = xml.xpath('/msg/appmsg/title/text()')[0]
            forward_content = xml.xpath('/msg/appmsg/des/text()')[0]
            result_text += f"{msg_title}\n\n{forward_content}"
            efb_msg = Message(
                type=MsgType.Text,
                text= emoji_wechat2telegram(result_text),
                vendor_specific={ "is_forwarded": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 21: # ????????????
            msg_title = xml.xpath('/msg/appmsg/title/text()')[0].strip("<![CDATA[??????").strip("??????]]>")
            if '??????' not in msg_title:
                msg_title = msg_title.strip()
                efb_msg = Message(
                    type=MsgType.Text,
                    text= msg_title ,
                )
                efb_msgs.append(efb_msg)
            else:
                rank = xml.xpath('/msg/appmsg/hardwareinfo/messagenodeinfo/rankinfo/rank/rankdisplay/text()')[0].strip("<![CDATA[").strip("]]>")
                steps = xml.xpath('/msg/appmsg/hardwareinfo/messagenodeinfo/rankinfo/score/scoredisplay/text()')[0].strip("<![CDATA[").strip("]]>")
                result_text += f"{msg_title}\n\n??????: {rank}\n??????: {steps}"
                efb_msg = Message(
                    type=MsgType.Text,
                    text=result_text,
                    vendor_specific={ "is_wechatsport": True }
                )
                efb_msgs.append(efb_msg)
        elif type == 24:
            desc = xml.xpath('/msg/appmsg/des/text()')[0]
            recorditem = xml.xpath('/msg/appmsg/recorditem/text()')[0]
            xml = etree.fromstring(recorditem)
            datadesc = xml.xpath('/recordinfo/datalist/dataitem/datadesc/text()')[0]
            efb_msg = Message(
                type=MsgType.Text,
                text= '???????????? :\n  - - - - - - - - - - - - - - - \n' +desc + '\n' + datadesc,
                vendor_specific={ "is_mp": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 35:
            efb_msg = Message(
                type=MsgType.Text,
                text= '???????????? : ????????????',
                vendor_specific={ "is_mp": False }
            )
            efb_msgs.append(efb_msg)
        elif type == 40: # ?????????????????????
            title = xml.xpath('/msg/appmsg/title/text()')[0]
            desc = xml.xpath('/msg/appmsg/des/text()')[0]
            efb_msg = Message(
                type=MsgType.Text,
                text= f"{title}\n\n{desc}" ,
                vendor_specific={ "is_forwarded": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 51: # ?????????????????????????????????
            title = xml.xpath('/msg/appmsg/title/text()')[0]
            url = xml.xpath('/msg/appmsg/url/text()')[0]
            if len(xml.xpath('/msg/appmsg/finderFeed/avatar/text()'))!=0:
                imgurl = xml.xpath('/msg/appmsg/finderFeed/avatar/text()')[0].strip("<![CDATA[").strip("]]>")
            else:
                imgurl = None
            if len(xml.xpath('/msg/appmsg/finderFeed/desc/text()'))!=0:
                desc = xml.xpath('/msg/appmsg/finderFeed/desc/text()')[0]
            else:
                desc = None
            result_text += f"?????????????????????\n - - - - - - - - - - - - - - - \n"
            attribute = LinkAttribute(
                title=title,
                description=  '\n' + desc,
                url= url,
                image= imgurl
            )
            efb_msg = Message(
                attributes=attribute,
                type=MsgType.Link,
                text=result_text,
                vendor_specific={ "is_mp": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 57: # ????????????????????????
            msg = xml.xpath('/msg/appmsg/title/text()')[0]
            refer_msgType = int(xml.xpath('/msg/appmsg/refermsg/type/text()')[0]) # ?????????????????????
            # refer_fromusr = xml.xpath('/msg/appmsg/refermsg/fromusr/text()')[0] # ???????????????????????????
            # refer_fromusr = xml.xpath('/msg/appmsg/refermsg/chatusr/text()')[0] # ?????????????????????????????????
            refer_displayname = xml.xpath('/msg/appmsg/refermsg/displayname/text()')[0] # ????????????????????????????????????
            refer_content = xml.xpath('/msg/appmsg/refermsg/content/text()')[0] # ?????????????????????
            if refer_msgType == 1: # ???????????????????????????
                result_text += f"???{refer_displayname}:\n{refer_content}???\n  - - - - - - - - - - - - - - - \n{msg}"
            else: # ?????????????????????????????????????????????
                result_text += f"???{refer_displayname}:\n?????????????????????????????????????????????????????????????????????\n  - - - - - - - - - - - - - - - \n{msg}"
            efb_msg = Message(
                type=MsgType.Text,
                text=result_text,
                vendor_specific={ "is_refer": True }
            )
            efb_msgs.append(efb_msg)
        elif type == 63: # ?????????????????????????????????
            title = xml.xpath('/msg/appmsg/title/text()')[0]
            url = xml.xpath('/msg/appmsg/url/text()')[0]
            imgurl = xml.xpath('/msg/appmsg/finderLive/headUrl/text()')[0].strip("<![CDATA[").strip("]]>")
            desc = xml.xpath('/msg/appmsg/finderLive/desc/text()')[0].strip("<![CDATA[").strip("]]>")
            result_text += f"?????????????????????\n  - - - - - - - - - - - - - - - \n"
            attribute = LinkAttribute(
                title=title,
                description= '\n' + desc ,
                url= url,
                image= imgurl
            )
            efb_msg = Message(
                attributes=attribute,
                type=MsgType.Link,
                text=result_text,
                vendor_specific={ "is_mp": True }
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

def efb_location_wrapper(msg: str) -> Message:
    efb_msg = Message()
    '''msg = ast.literal_eval(text)'''
    efb_msg.text = msg['desc']
    efb_msg.attributes = LocationAttribute(latitude=float(msg['x']),
                                           longitude=float(msg['y']))
    efb_msg.type = MsgType.Location
    return efb_msg

def efb_qqmail_wrapper(text: str) -> Message:
    xml = etree.fromstring(text)
    result_text = ""
    sender = xml.xpath('/msg/pushmail/content/sender/text()')[0].strip("<![CDATA[").strip("]]>")
    subjectwithCDATA = xml.xpath('/msg/pushmail/content/subject/text()')
    if len(subjectwithCDATA) != 0:
        subject = subjectwithCDATA[0].strip("<![CDATA[").strip("]]>")
    digest = xml.xpath('/msg/pushmail/content/digest/text()')[0].strip("<![CDATA[").strip("]]>")
    addr = xml.xpath('/msg/pushmail/content/fromlist/item/addr/text()')[0]
    datereceive = xml.xpath('/msg/pushmail/content/date/text()')[0].strip("<![CDATA[").strip("]]>")
    result_text = f"?????????{subject}\nfrom: {sender}\n????????????: {datereceive}\n??????: {digest}"
    attribute = LinkAttribute(
        title= f'??????: {addr}',
        description= result_text,
        url= f"mailto:{addr}",
        image= None
    )
    efb_msg = Message(
        attributes=attribute,
        type=MsgType.Link,
        text=None,
        vendor_specific={ "is_mp": False }
    )
    return efb_msg



def efb_miniprogram_wrapper(text: str) -> Message:
    xml = etree.fromstring(text)
    result_text = ""
    title = xml.xpath('/msg/appmsg/title/text()')[0]
    programname = xml.xpath('/msg/appmsg/sourcedisplayname/text()')[0]
    imgurl = xml.xpath('/msg/appmsg/weappinfo/weappiconurl/text()')[0].strip("<![CDATA[").strip("]]>")
    url = xml.xpath('/msg/appmsg/url/text()')[0]
    result_text = f"from: {programname}\n  - - - - - - - - - - - - - - - \n?????????????????????"
    attribute = LinkAttribute(
        title= f'{title}',
        description= result_text,
        url= url,
        image= imgurl
    )
    efb_msg = Message(
        attributes=attribute,
        type=MsgType.Link,
        text=None,
        vendor_specific={ "is_mp": False }
    )
    return efb_msg

def efb_unsupported_wrapper( text : str) -> Message:
    """
    A simple EFB message wrapper for unsupported message
    :param text: The content of the message
    :return: EFB Message
    """
    efb_msg = Message(
        type=MsgType.Unsupported,
        text=text
    )
    return efb_msg

def efb_voice_wrapper(file: IO, filename: str = None, text: str = None) -> Message:
    """
    A EFB message wrapper for voices.
    :param file: The file handle
    :param filename: The actual filename
    :param text: The attached text
    :return: EFB Message
    """
    efb_msg = Message()
    efb_msg.type = MsgType.Audio
    efb_msg.file = file
    mime = magic.from_file(efb_msg.file.name, mime=True)
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
