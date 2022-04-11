import base64
import tempfile
import logging
from .utils import download_file
from efb_wechat_slave.MsgDecorator import efb_text_simple_wrapper, efb_image_wrapper, efb_video_wrapper, efb_share_link_wrapper, efb_location_wrapper, efb_file_wrapper
import re

logger :logging.Logger = logging.getLogger(__name__)

class MsgProcessor:

    @staticmethod
    def text_msg(msg: dict , chat):
        msg['msg'] = str(msg['msg'])
        at_list = {}
        if "[@at," in msg['msg']:
            text = msg['msg']
            at = re.findall(r"\[@at,(.+?)\]",text)
            content = re.sub(r'\[@at,nickname=(.+?)\]','',text)
            temp_msg = ""
            for each_people in list(set(at)):
                nickname = re.findall("^nickname=(.+),wxid",each_people)
                wxid = re.findall("wxid=(.+)$",each_people)
                if len(nickname)!=0:
                    for i in nickname:
                        temp_msg += "@"+ i
                if len(wxid)!=0:
                    for i in wxid:
                        if i == msg['robot_wxid']:
                            begin_index = len(temp_msg)
                            temp_msg += ' @me'
                            end_index = len(temp_msg)
                            at_list[(begin_index, end_index)] = chat.self
            temp_msg+='\n'+content
            msg['msg'] = temp_msg
        
        if at_list:
            return efb_text_simple_wrapper(msg['msg'] , at_list)
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def image_msg(msg: dict):
        url = msg['msg']
        try:
            f = download_file(url)
        except Exception as e:
            logger.warning(f"Failed to download the image! {e}")
            return efb_text_simple_wrapper("Image received and download failed. Please check it on your phone.")
        else:
            return efb_image_wrapper(f)

    @staticmethod
    def video_msg(msg : dict):
        url = msg['msg']
        try:
            f = download_file(url)
        except Exception as e:
            logger.warning(f"Failed to download the video_msg! {e}")
            return efb_text_simple_wrapper("Video_msg received and download failed. Please check it on your phone.")
        else:
            return efb_video_wrapper(f)

    @staticmethod
    def file_msg(msg : dict):
        url = msg['msg']
        try:
            f = download_file(url)
        except Exception as e:
            logger.warning(f"Failed to download the file! {e}")
            return efb_text_simple_wrapper("File received and download failed. Please check it on your phone.")
        else:
            return efb_file_wrapper(f , filename= url.split('/')[-1])

    @staticmethod
    def share_link_msg(msg: dict):
        return efb_share_link_wrapper(msg['msg'])
    
    @staticmethod
    def location_msg(msg: dict):
        return efb_location_wrapper(self, msg['msg'])
    
    @staticmethod
    def other_msg(msg: dict):
        if '<banner>' in msg['msg']:
            msg['msg'] = '收到/取消 群语音邀请'
        elif '<notifydata>' in msg['msg']:
            return None
        elif '拍了拍' in msg['msg']:
            return None
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def unsupported_msg(msg: dict):
        mag_type = {'miniprogram' : '小程序' , 'voip' : '语音聊天' , 'voip' : '语音/视频聊天'}
        msg['msg'] = '不支持 %s 消息类型, 请在微信端查看' % mag_type[msg['type']]
        return efb_text_simple_wrapper(msg['msg'])
    
    @staticmethod
    def revoke_msg(msg: dict):
        pat = "['|\"]msg_type['|\"]: (\d+),"
        try:
            msg_type = re.search(pat , str(msg['msg'])).group(1)
        except:
            msg_type = None
        if msg_type in ['1']:
            msg['msg'] = ' 「撤回了一条消息」 \n - - - - - - - - - - - - - - - \n ' + msg['msg']['revoked_msg']['content']
        else:
            msg['msg'] = ' 「撤回了一条消息」 \n - - - - - - - - - - - - - - - \n 不支持的消息类型'
        return efb_text_simple_wrapper(msg['msg'])

