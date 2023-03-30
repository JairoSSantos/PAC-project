import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

from flask import Flask, request, jsonify
import numpy as np
from skimage.io import imread
from skimage.color import rgb2gray, label2rgb
from src.measure import find_scale, find_slope
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from tensorflow.keras.saving import load_model
import base64
from io import BytesIO

app = Flask(__name__)
model = load_model('unet-0.45.h5', compile=False)

def norm(x):
    return (x - x.min())/x.ptp()

@app.route('/', methods=['POST'])
def upload():
    request.files['image'].save('image.jpg')

    img = imread('image.jpg')

    gray_img = norm(rgb2gray(img))
    s, ds = find_scale(gray_img)
    slope, d_slope = find_slope(gray_img)
    pred = model.predict(gray_img[np.newaxis, ..., np.newaxis])[0, ..., 0]

    #mask_pred = label2rgb(pred, img, colors=['blue'])
    fig = Figure(dpi=1000, tight_layout=True)
    ax = fig.add_subplot(111)
    ax.imshow(img)
    ax.contour(pred, cmap='bone', linewidths=0.8)
    fig.patch.set_visible(False)
    ax.axis('off')
    buffered = BytesIO()
    FigureCanvasAgg(fig).print_jpg(buffered)

    return jsonify({
        'scale': str(s),
        'delta_scale': str(ds),
        'segmentation': base64.b64encode(buffered.getvalue()).decode(),
        'area': str(np.sum(pred) * s)
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)