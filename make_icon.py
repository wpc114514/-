"""生成应用图标 icon.ico（蓝色圆角底 + 白色「译」字）"""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
SIZES = [16, 24, 32, 48, 64, 128, 256]
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

BLUE_TOP = (59, 130, 246)
BLUE_BOTTOM = (29, 78, 216)


def _font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def make(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # 竖向渐变背景
    grad = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / max(size - 1, 1)
        color = tuple(int(BLUE_TOP[i] + (BLUE_BOTTOM[i] - BLUE_TOP[i]) * t)
                      for i in range(3)) + (255,)
        gd.line([(0, y), (size, y)], fill=color)
    # 圆角遮罩
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1],
                                           radius=int(size * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)

    # 「译」字
    d = ImageDraw.Draw(img)
    font = _font(int(size * 0.60))
    text = "译"
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), text,
           font=font, fill=(255, 255, 255, 255))
    return img


def main():
    images = [make(s) for s in SIZES]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print("已生成:", OUT)


if __name__ == "__main__":
    main()
