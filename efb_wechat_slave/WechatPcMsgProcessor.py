import base64
import tempfile
from .utils import download_file
from efb_wechat_slave.MsgDecorator import efb_text_simple_wrapper, efb_image_wrapper, efb_video_wrapper, efb_share_link_wrapper


class MsgProcessor:
    @staticmethod
    def text_msg(msg: dict):
        return efb_text_simple_wrapper(str(msg['msg']))

    @classmethod
    def image_msg(cls , msg: dict , api_root : str):
        url = cls().url_preprocess(msg , api_root)
        try:
            f = download_file(url)
        except Exception as e:
            logger.warning(f"Failed to download the image! {e}")
            return efb_text_simple_wrapper("Image received and download failed. Please check it on your phone.")
        else:
            return efb_image_wrapper(f)

    @classmethod
    def video_msg(cls , msg : dict , api_root : str):
        url = cls().url_preprocess(msg , api_root)
        try:
            f = download_file(url)
        except Exception as e:
            logger.warning(f"Failed to download the video_msg! {e}")
            return efb_text_simple_wrapper("Video_msg received and download failed. Please check it on your phone.")
        else:
            return efb_video_wrapper(f)

    def url_preprocess(self , msg : str , api_root : str):
        path = msg['msg']
        if '\\WeChat' in path:
            path = '/WeChat'+ path.split('\\WeChat')[-1].replace('\\', '/')
        return api_root + path

    
    @classmethod
    def share_link_msg(self , msg: dict , api_root : str):
        return efb_share_link_wrapper(msg['msg'])
    
    @classmethod
    def location_msg(cls , msg: dict , api_root : str):
        pass
