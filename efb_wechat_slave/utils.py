import logging
import tempfile
import threading
import requests as requests
import re
import json
import emoji as Emoji

def download_file(url: str, retry: int = 3) -> tempfile:
    """
    A function that downloads files from given URL
    Remember to close the file once you are done with the file!
    :param retry: The max retries before giving up
    :param url: The URL that points to the file
    """
    count = 1
    while True:
        try:
            file = tempfile.NamedTemporaryFile()
            r = requests.get(url, stream=True, timeout=10)
            r.raise_for_status()  # Replace this with better error handling.

            for chunk in r.iter_content(1024):
                file.write(chunk)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error occurred when downloading {url}. {e}")
            if count >= retry:
                logging.getLogger(__name__).warning(f"Maximum retry reached. Giving up.")
                raise e
            count += 1
        else:
            break
    return file

def emoji_telegram2wechat(msg):
    text = msg
    emojiList = Emoji.get_emoji_regexp().findall(text)
    for emoji in emojiList:
        text = text.replace(emoji, '[@emoji=' + json.dumps(emoji).strip("\"") + ']')
    return text

def emoji_wechat2telegram(msg):
    text = msg
    emojiList = re.findall(r'(?<=\[@emoji=)[\\0-9A-Za-z]*(?=\])', text)
    for emoji in emojiList:
        # 将 "\\ud83d\\ude4b" 转为 Unicode 表情
        text = text.replace(f"[@emoji={emoji}]", emoji.encode('utf-8').decode("unicode-escape").encode('utf-16', 'surrogatepass').decode('utf-16'))
    return text

WC_EMOTICON_CONVERSION = {
    '[微笑]': '😃', '[Smile]': '😃',
    '[撇嘴]': '😖', '[Grimace]': '😖',
    '[色]': '😍', '[Drool]': '😍',
    '[发呆]': '😳', '[Scowl]': '😳',
    '[得意]': '😎', '[Chill]': '😎',
    '[流泪]': '😭', '[Sob]': '😭',
    '[害羞]': '☺️', '[Shy]': '☺️',
    '[闭嘴]': '🤐', '[Shutup]': '🤐',
    '[睡]': '😴', '[Sleep]': '😴',
    '[大哭]': '😣', '[Cry]': '😣',
    '[尴尬]': '😰', '[Awkward]': '😰',
    '[发怒]': '😡', '[Pout]': '😡',
    '[调皮]': '😜', '[Wink]': '😜',
    '[呲牙]': '😁', '[Grin]': '😁',
    '[惊讶]': '😱', '[Surprised]': '😱',
    '[难过]': '🙁', '[Frown]': '🙁',
    '[囧]': '☺️', '[Tension]': '☺️',
    '[抓狂]': '😫', '[Scream]': '😫',
    '[吐]': '🤢', '[Puke]': '🤢',
    '[偷笑]': '🙈', '[Chuckle]': '🙈',
    '[愉快]': '☺️', '[Joyful]': '☺️',
    '[白眼]': '🙄', '[Slight]': '🙄',
    '[傲慢]': '😕', '[Smug]': '😕',
    '[困]': '😪', '[Drowsy]': '😪',
    '[惊恐]': '😱', '[Panic]': '😱',
    '[流汗]': '😓', '[Sweat]': '😓',
    '[憨笑]': '😄', '[Laugh]': '😄',
    '[悠闲]': '😏', '[Loafer]': '😏',
    '[奋斗]': '💪', '[Strive]': '💪',
    '[咒骂]': '😤', '[Scold]': '😤',
    '[疑问]': '❓', '[Doubt]': '❓',
    '[嘘]': '🤐', '[Shhh]': '🤐',
    '[晕]': '😲', '[Dizzy]': '😲',
    '[衰]': '😳', '[BadLuck]': '😳',
    '[骷髅]': '💀', '[Skull]': '💀',
    '[敲打]': '👊', '[Hammer]': '👊',
    '[再见]': '🙋\u200d♂', '[Bye]': '🙋\u200d♂',
    '[擦汗]': '😥', '[Relief]': '😥',
    '[抠鼻]': '🤷\u200d♂', '[DigNose]': '🤷\u200d♂',
    '[鼓掌]': '👏', '[Clap]': '👏',
    '[坏笑]': '👻', '[Trick]': '👻',
    '[左哼哼]': '😾', '[Bah！L]': '😾',
    '[右哼哼]': '😾', '[Bah！R]': '😾',
    '[哈欠]': '😪', '[Yawn]': '😪',
    '[鄙视]': '😒', '[Lookdown]': '😒',
    '[委屈]': '😣', '[Wronged]': '😣',
    '[快哭了]': '😔', '[Puling]': '😔',
    '[阴险]': '😈', '[Sly]': '😈',
    '[亲亲]': '😘', '[Kiss]': '😘',
    '[可怜]': '😻', '[Whimper]': '😻',
    '[菜刀]': '🔪', '[Cleaver]': '🔪',
    '[西瓜]': '🍉', '[Melon]': '🍉',
    '[啤酒]': '🍺', '[Beer]': '🍺',
    '[咖啡]': '☕', '[Coffee]': '☕',
    '[猪头]': '🐷', '[Pig]': '🐷',
    '[玫瑰]': '🌹', '[Rose]': '🌹',
    '[凋谢]': '🥀', '[Wilt]': '🥀',
    '[嘴唇]': '💋', '[Lip]': '💋',
    '[爱心]': '❤️', '[Heart]': '❤️',
    '[心碎]': '💔', '[BrokenHeart]': '💔',
    '[蛋糕]': '🎂', '[Cake]': '🎂',
    '[炸弹]': '💣', '[Bomb]': '💣',
    '[便便]': '💩', '[Poop]': '💩',
    '[月亮]': '🌃', '[Moon]': '🌃',
    '[太阳]': '🌞', '[Sun]': '🌞',
    '[拥抱]': '🤗', '[Hug]': '🤗',
    '[强]': '👍', '[Strong]': '👍',
    '[弱]': '👎', '[Weak]': '👎',
    '[握手]': '🤝', '[Shake]': '🤝',
    '[胜利]': '✌️', '[Victory]': '✌️',
    '[抱拳]': '🙏', '[Salute]': '🙏',
    '[勾引]': '💁\u200d♂', '[Beckon]': '💁\u200d♂',
    '[拳头]': '👊', '[Fist]': '👊',
    '[OK]': '👌',
    '[跳跳]': '💃', '[Waddle]': '💃',
    '[发抖]': '🙇', '[Tremble]': '🙇',
    '[怄火]': '😡', '[Aaagh!]': '😡',
    '[转圈]': '🕺', '[Twirl]': '🕺',
    '[嘿哈]': '🤣', '[Hey]': '🤣',
    '[捂脸]': '🤦\u200d♂', '[Facepalm]': '🤦\u200d♂',
    '[奸笑]': '😜', '[Smirk]': '😜',
    '[机智]': '🤓', '[Smart]': '🤓',
    '[皱眉]': '😟', '[Concerned]': '😟',
    '[耶]': '✌️', '[Yeah!]': '✌️',
    '[红包]': '🧧', '[Packet]': '🧧',
    '[鸡]': '🐥', '[Chick]': '🐥',
    '[蜡烛]': '🕯️', '[Candle]': '🕯️',
    '[糗大了]': '😥',
    '[Thumbs Up]': '👍', '[Pleased]': '😊',
    '[Rich]': '🀅',
    '[Pup]': '🐶',
    '[吃瓜]': '🙄\u200d🍉',
    '[加油]': '💪\u200d😁',
    '[加油加油]': '💪\u200d😷',
    '[汗]': '😓',
    '[天啊]': '😱',
    '[Emm]': '🤔',
    '[社会社会]': '😏',
    '[旺柴]': '🐶\u200d😏',
    '[好的]': '😏\u200d👌',
    '[哇]': '🤩',
    '[打脸]': '😟\u200d🤚',
    '[破涕为笑]': '😂', '[破涕為笑]': '😂',
    '[苦涩]': '😭',
    '[翻白眼]': '🙄',
    '[裂开]': '🫠'
}
