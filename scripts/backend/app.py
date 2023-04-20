import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

from flask import Flask, request, jsonify

import base64
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
import json
from textwrap import wrap

import numpy as np
from skimage.color import rgb2gray
from skimage.transform import resize
from skimage.filters import sobel
from skimage import morphology
from scipy import ndimage
from src.measure import find_scale
from tensorflow.keras.saving import load_model

MODEL = load_model('unet-0.45.h5', compile=False)
IMG_SIZE = (256, 256)
PAD_BY_WIDTH = 1/20 # proporção margem por largura da imagem
TEXT_LIM = 40 # limite de caracteres por linha de texto

APP = Flask(__name__)

def get_image(image_file):
    buffered = BytesIO()
    image_file.save(buffered)
    return Image.open(buffered)

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format='JPEG', quality=95)
    return base64.b64encode(buffered.getvalue()).decode()

def build_overlay(mask, image):
    contour = Image.fromarray(morphology.skeletonize(sobel(mask).astype(bool)))
    label = Image.fromarray(mask.astype(bool)).convert('RGB')
    overlay = Image.composite(Image.new('RGB', image.size, (255, 255, 255)), Image.blend(image, label, 0.3), contour)
    return image_to_base64(overlay)

@APP.route('/', methods=['POST'])
def upload():
    image = get_image(request.files['image'])
    post_process = json.loads(request.values.get('post_process'))

    gray_image = rgb2gray(resize(np.array(image), IMG_SIZE))
    scale = find_scale(gray_image)[0]
    pred = MODEL.predict(gray_image[np.newaxis, ..., np.newaxis])[0, ..., 0]
    pred = pred > 0.5

    for func, config in post_process.items():
        pred = getattr(globals()[config['source']], func)(pred, **config['params'])

    segmentation = resize(pred, image.size)

    return jsonify({
        'scale': scale,
        'area': scale*pred.sum(),
        'segmentation': build_overlay(segmentation, image)
    })

@APP.route('/result', methods=['POST'])
def result_as_image():
    image = get_image(request.files['image'])
    info = json.loads(request.values.get('informations'))

    w, h = image.size
    pad = int(PAD_BY_WIDTH * w)
    font = ImageFont.truetype('arial.ttf', pad)

    items = []
    for k, v in info.items():
        text = f'{k}: {v}'
        if len(text) > TEXT_LIM:
            items += wrap(text, width=TEXT_LIM)
        else: items.append(text)

    size = (w + 2*pad, h + (2 + 2*len(items))*pad)
    result = Image.new('RGB', size, (255, 255, 255))
    draw = ImageDraw.Draw(result)
    result.paste(image, (pad, pad))

    y = y0 = 2*pad + h
    for item in items:
        draw.text((int(1.5*pad), y), item, (0, 0, 0), font=font)
        y += 2*pad

    return jsonify({
        'result': image_to_base64(result)
    })

if __name__ == '__main__':
    APP.run(port=5000, debug=True, threaded=True)