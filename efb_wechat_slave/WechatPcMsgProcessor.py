import base64
import tempfile
from urllib.request import urlopen

from efb_wechat_slave.MsgDecorator import efb_text_simple_wrapper, efb_image_wrapper


class MsgProcessor:
    @staticmethod
    def text_msg(msg: dict):
        return efb_text_simple_wrapper(msg['content'])

    @staticmethod
    def image_msg(msg: dict):
        if 'imageFile' in msg and 'base64Content' in msg['imageFile']:
            try:
                file = tempfile.NamedTemporaryFile()
                with urlopen(msg['imageFile']['base64Content']) as response:
                    data = response.read()
                    file.write(data)
                return efb_image_wrapper(file)
            except Exception as e:
                print(e)
        return efb_text_simple_wrapper("Image received. Please check it on your phone.")