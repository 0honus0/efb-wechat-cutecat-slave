import base64
import tempfile
import logging
from .utils import download_file , wechatimagedecode , load_config
from .MsgDecorator import efb_text_simple_wrapper, efb_text_delete_wrapper, efb_image_wrapper, efb_video_wrapper, efb_share_link_wrapper, efb_location_wrapper, efb_file_wrapper , efb_unsupported_wrapper , efb_voice_wrapper , efb_qqmail_wrapper , efb_miniprogram_wrapper
import re
import pilk
import pydub
import json

from ehforwarderbot import utils as efb_utils

logger :logging.Logger = logging.getLogger(__name__)

channel_id = "honus.CuteCatiHttp"
access_token = load_config(efb_utils.get_config_path(channel_id)).get("access_token" , "")

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
            temp_msg += ' ' + (content.strip())
            msg['msg'] = temp_msg
        
        if at_list:
            return efb_text_simple_wrapper(msg['msg'] , at_list)
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def image_msg(msg: dict):
        url = msg['msg']
        try:
            f = download_file(url , access_token = access_token)
        except Exception as e:
            logger.warning(f"Failed to download the image! {e}")
            return efb_text_simple_wrapper("Image received and download failed. Please check it on your phone.")
        else:
            return efb_image_wrapper(f)

    @staticmethod
    def video_msg(msg : dict):
        url = msg['msg']
        try:
            f = download_file(url , access_token = access_token)
        except Exception as e:
            logger.warning(f"Failed to download the video_msg! {e}")
            return efb_text_simple_wrapper("Video_msg received and download failed. Please check it on your phone.")
        else:
            return efb_video_wrapper(f)

    @staticmethod
    def file_msg(msg : dict):
        url = msg['msg']
        try:
            f = download_file(url , access_token = access_token)
        except Exception as e:
            logger.warning(f"Failed to download the file! {e}")
            return efb_text_simple_wrapper("File received and download failed. Please check it on your phone.")
        else:
            if 'dat' in url:
                f = wechatimagedecode(f)
                return efb_image_wrapper(f)
            return efb_file_wrapper(f , filename= url.split('/')[-1])

    @staticmethod
    def share_link_msg(msg: dict):
        try:
            type = re.search('<type>(\d+)<\/type>' , msg['msg']).group(1)
            if str(type) in ['8'] and msg['event'] == 'EventSendOutMsg':
                return
        except:
            pass
        return efb_share_link_wrapper(msg['msg'])
    
    @staticmethod
    def location_msg(msg: dict):
        return efb_location_wrapper(msg['msg'])
    
    @staticmethod
    def qqmail_msg(msg: dict):
        return efb_qqmail_wrapper(msg['msg'])
    
    @staticmethod
    def miniprogram_msg(msg: dict):
        return efb_miniprogram_wrapper(msg['content'])
    
    @staticmethod
    def other_msg(msg: dict):
        if '<banner>' in msg['msg']:
            msg['msg'] = '??????/?????? ???????????????'
        elif 'notifydata' in msg['msg']:
            return None
        elif '?????????' in msg['msg'] or 'tickled' in msg['msg']:
            return None
        elif 'ClientCheckConsistency' in msg['msg']:
            msg['msg'] = '????????????????????????'
        elif 'mmchatroombarannouncememt' in msg['msg']:
            return None
        elif 'bizlivenotify' in msg['msg']:    #????????????????????????
            msg['msg'] = '??????????????????'
        elif 'roomtoolstips' in msg['msg'] and '??????' in msg['msg']:
            msg['msg'] = '  - - - - - - - - - - - - - - - \n????????????????????????'
        elif 'roomtoolstips' in msg['msg'] and '??????' not in msg['msg']:
            msg['msg'] = '  - - - - - - - - - - - - - - - \n??????/?????? ??????????????????'
        elif 'ShareExtensionSend' in msg['msg']:
            msg['msg'] = '  - - - - - - - - - - - - - - - \n??????????????????'
        elif 'ChatSync' in msg['msg']:
            msg['msg'] = '  - - - - - - - - - - - - - - - \n???????????? : ????????????'
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def unsupported_msg(msg: dict):
        mag_type = {'voip' : '??????/????????????' , 'card' : '???????????????????????????'}
        msg['msg'] = '%s\n  - - - - - - - - - - - - - - - \n????????????????????????, ?????????????????????' % mag_type[msg['type']]
        return efb_unsupported_wrapper(msg['msg'])
    
    @staticmethod
    def revoke_msg(msg: dict):
        pat = "['|\"]msg_type['|\"]: (\d+),"
        try:
            msg_type = re.search(pat , str(msg['msg'])).group(1)
        except:
            msg_type = None
        if msg_type in ['1']:
            msg['msg'] = '??????????????????????????? \n  - - - - - - - - - - - - - - - \n' + msg['msg']['revoked_msg']['content']
        else:
            msg['msg'] = '??????????????????????????? \n  - - - - - - - - - - - - - - - \n????????????????????????'
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def voice_msg( msg : dict , chat):
        try:
            input_file = download_file(msg['msg'] , access_token = access_token)
        except Exception as e:
            logger.warning(f"Failed to download the voice! {e}")
            msg['msg'] = '????????????\n  - - - - - - - - - - - - - - - \n????????????????????????, ?????????????????????'
            return efb_unsupported_wrapper(msg['msg'])
        else:
            f = tempfile.NamedTemporaryFile()
            input_file.seek(0)
            silk_header = input_file.read(10)
            input_file.seek(0)
            if b"#!SILK_V3" in silk_header:
                pilk.decode(input_file.name, f.name)
                input_file.close()
                pydub.AudioSegment.from_raw(file= f , sample_width=2, frame_rate=24000, channels=1) \
                    .export( f , format="ogg", codec="libopus",
                            parameters=['-vbr', 'on'])
                return efb_voice_wrapper(f , filename= f.name + '.ogg')
            input_file.close()
            msg['msg'] = '????????????\n  - - - - - - - - - - - - - - - \n????????????????????????, ?????????????????????'
            return efb_unsupported_wrapper(msg['msg'])
            
    @staticmethod
    def group_announcement_msg( msg : dict ):
        msg['msg'] = '??????????????? \n  - - - - - - - - - - - - - - - \n ' + msg['msg']
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def event_notify_msg( msg : dict ):
        if msg['event'] == 'EventGroupMemberAdd':
            new = msg['msg']['guest']['nickname']
            inviter = msg['msg']['inviter']['nickname']
            msg['msg'] = f'????????????????????? \n  - - - - - - - - - - - - - - - \n{inviter} ?????? {new} ???????????????'
        elif msg['event'] == 'EventGroupMemberDecrease':
            msg['msg'] = '????????????????????? \n  - - - - - - - - - - - - - - - \n "' + msg['msg']['member_nickname'] + '" ???????????????'
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def transfer_msg( msg : dict ):
        msg['msg'] = '???????????? \n  - - - - - - - - - - - - - - - \n ' + str(json.loads(msg['money'])) + ' ???'
        return efb_text_simple_wrapper(msg['msg'])

    @staticmethod
    def scanmoney_msg( msg : dict ):
        msg['msg'] = msg['msg']['scene_desc']
        return efb_text_simple_wrapper(msg['msg'])

