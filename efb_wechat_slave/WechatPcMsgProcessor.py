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
            temp_msg+=' '+content
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
    def multivoip_msg(msg: dict):
        pass

