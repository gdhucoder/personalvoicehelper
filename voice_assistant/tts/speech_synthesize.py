from dashscope.audio.tts_v2 import *
import dashscope
import re
import hashlib
import os

def speechsynthesize(text):
    result_file = ""
    # 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
    # dashscope.api_key = "apiKey"

    file_name = generate_hash_file_name(text)
    result_file = f'/home/hugd/privateprojects/voicehelperdemo/speechsynthesizeresult/{file_name}.mp3'
    # 检查文件是否存在
    if os.path.exists(result_file):
        print(f"文件已存在")
    else:
        print(f"文件不存在，正在生成: {result_file}")
        model = "cosyvoice-v1"
        voice = "longxiaochun"
        synthesizer = SpeechSynthesizer(model=model, voice=voice)
        audio = synthesizer.call(text)
        print(synthesizer.get_last_request_id())
        with open(result_file, 'wb') as f:
            f.write(audio)
    return result_file


def generate_hash_file_name(text):
    # 使用正则表达式去除标点符号
    cleaned_text = re.sub(r'[*=，。！？“”‘’（）【】、；：]', '', text)  # 移除常见的标点符号
    # 截取文本的前10个字符并计算哈希值
    # text_part = cleaned_text[:10]  # 截取文本的前10个字符
    hash_part = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()[:6]  # 计算哈希并截取前6位
    # file_name = f"{text_part}_{hash_part}.mp3"  # 结合文本和哈希值生成文件名
    file_name = f"{hash_part}"
    return file_name