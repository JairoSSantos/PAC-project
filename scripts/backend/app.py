import sys
sys.path.append('../src/')

from flask import Flask, request, jsonify
from skimage.io import imread
from measure import find_scale

app = Flask(__name__)

def norm(x):
    return (x - x.min())/x.ptp()

@app.route('/', methods=['POST'])
def upload():
    request.files['image'].save('image.jpg')
    img = norm(imread('image.jpg', as_gray=True))
    s, ds = find_scale(img)
    return jsonify({
        'scale': str(s),
        'delta_scale': str(ds),
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)