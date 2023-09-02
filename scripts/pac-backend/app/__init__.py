from flask import Flask, request, jsonify

import base64
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
import json
from textwrap import wrap

import numpy as np
from skimage.color import rgb2gray, label2rgb
from skimage.transform import resize
from skimage.filters import roberts
from skimage import morphology
from skimage.segmentation import mark_boundaries
from scipy import ndimage
from scipy.stats import mode
from tensorflow.keras.saving import load_model

MODEL = load_model('app/unet-0.41.h5', compile=False)
IMG_SIZE = (256, 256)
PAD_BY_WIDTH = 1/30 # proporção margem por largura da imagem
TEXT_LIM = 50 # limite de caracteres por linha de texto
SAVING_SIZE = (1000, 1000)

APP = Flask(__name__)

def FFT(x):
    return np.abs(np.fft.fft(x))

def Cxx(x):
    return np.correlate(x, x, mode='same')

def PSD(x):
    return FFT(Cxx(x))

def find_scale(img, sigma=2):
    Iy, Ix = np.gradient(img)
    fs, delta = [], []
    for dI in (Ix, Iy.T):
        freqs = np.fft.fftfreq(dI.shape[1], 1)
        pos = freqs > 0
        dI_gauss = ndimage.gaussian_filter(dI, sigma)
        D = np.apply_along_axis(lambda y: freqs[pos][np.argmax(PSD(y)[pos])], 1, dI_gauss)
        fs.append(mode(D, keepdims=True).mode[0])
        delta.append(0.5/dI.shape[1])
    
    (fx, fy), (dx, dy) = fs, delta
    return fx*fy, np.sqrt((dx*fy)**2 + (dy*fx)**2)

def get_image(image_file):
    buffered = BytesIO()
    image_file.save(buffered)
    return Image.open(buffered)

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format='JPEG', quality=95)
    return base64.b64encode(buffered.getvalue()).decode()

def build_overlay(mask, image):
    label = Image.fromarray((120*mask).astype(np.uint8)).convert('L')
    overlay = Image.composite(Image.new('RGB', image.size, (50, 200, 255)), image, label)
    return image_to_base64(Image.fromarray((mark_boundaries(np.array(overlay), mask, (1, 1, 0))*255).astype(np.uint8)))

@APP.route('/', methods=['POST'])
def upload():
    image = get_image(request.files['image'])
    post_process = json.loads(request.values.get('post_process'))

    gray_image = rgb2gray(resize(np.array(image), IMG_SIZE))
    scale = find_scale(gray_image)[0]
    pred = MODEL.predict(gray_image[np.newaxis, ..., np.newaxis], verbose=False)[0, ..., 0]
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
    image = get_image(request.files['image']).resize(SAVING_SIZE)
    info = json.loads(request.values.get('informations'))

    w, h = image.size
    pad = int(PAD_BY_WIDTH * w)
    font = ImageFont.truetype('app/arial.ttf', pad)

    items = []
    for k, v in info.items():
        text = f'{k}{v}' if (k == '' or v == '') else f'{k}: {v}'
        if len(text) > TEXT_LIM:
            items += wrap(text, width=TEXT_LIM)
        else: items.append(text)

    size = (w + 2*pad, h + (2 + 2*len(items))*pad)
    result = Image.new('RGB', size, (255, 255, 255))
    draw = ImageDraw.Draw(result)
    result.paste(image, (pad, pad))

    y = 2*pad + h
    for item in items:
        draw.text((int(1.5*pad), y), item, (0, 0, 0), font=font)
        y += 2*pad

    return jsonify({
        'result': image_to_base64(result)
    })