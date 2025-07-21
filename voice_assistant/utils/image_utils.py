from PIL import Image

import base64, mimetypes

def img_to_base64_uri(path):
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"

def resize_for_image_understand(src_path, dim = 672):
    # 980 672 336
    dst_path = src_path.split('.')[0] + f"_resized_{dim}.jpg"
    img = Image.open(src_path).convert('RGB')
    # 先按最短边等比缩放，再居中裁出正方形
    w, h = img.size
    if w < h:
        new_w = dim
        new_h = int(h * dim / w)
    else:
        new_h = dim
        new_w = int(w * dim / h)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # 居中裁成正方形
    left = (new_w - dim) // 2
    top  = (new_h - dim) // 2
    img = img.crop((left, top, left + dim, top + dim))
    img.save(dst_path, quality=95)
    return dst_path