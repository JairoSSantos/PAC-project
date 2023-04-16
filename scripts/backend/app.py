import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

from flask import Flask, request, jsonify

import base64
from io import BytesIO
from PIL import Image
import json

import numpy as np
from skimage.color import rgb2gray
from skimage.transform import resize
from skimage.filters import sobel
from skimage import morphology
from src.measure import find_scale
from tensorflow.keras.saving import load_model

MODEL = load_model('unet-0.45.h5', compile=False)
IMG_SIZE = (256, 256)

APP = Flask(__name__)

def get_image(image_file):
    buffered = BytesIO()
    image_file.save(buffered)
    return Image.open(buffered)

def build_overlay(mask, image):
    contour = Image.fromarray(morphology.skeletonize(sobel(mask).astype(bool)))

    buffered = BytesIO()
    label = Image.fromarray(mask.astype(bool)).convert('RGB')
    overlay = Image.composite(Image.new('RGB', image.size, (255, 255, 255)), Image.blend(image, label, 0.3), contour)
    overlay.save(buffered, format='JPEG', quality=95)
    return base64.b64encode(buffered.getvalue()).decode()

@APP.route('/', methods=['POST'])
def upload():
    image = get_image(request.files['image'])
    post_process = json.loads(request.values.get('post_process'))

    gray_image = rgb2gray(resize(np.array(image), IMG_SIZE))
    scale = find_scale(gray_image)[0]
    pred = MODEL.predict(gray_image[np.newaxis, ..., np.newaxis])[0, ..., 0]

    for func, config in post_process.items():
        pred = getattr(globals()[config['source']], func)(pred, **config['params'])

    area = scale*pred.sum()
    segmentation = build_overlay(resize(pred > 0.5, image.size), image)

    return jsonify({
        'scale': scale,
        'area': area,
        'segmentation': segmentation
    })

if __name__ == '__main__':
    APP.run(port=5000, debug=True, threaded=True)