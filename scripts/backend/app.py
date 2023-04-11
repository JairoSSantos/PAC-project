import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

from flask import Flask, request, jsonify
import numpy as np
from skimage.io import imread
from src.measure import find_scale
from tensorflow.keras.saving import load_model
import base64
from io import BytesIO
from PIL import Image
import random
import string
from pathlib import Path
from dataclasses import dataclass
import threading
import json

model = load_model('unet-0.45.h5', compile=False)
app = Flask(__name__)
temp = Path('temp/')

@dataclass
class ImageProcessor:
    key:str = None
    path:str = None
    results_path:str = None
    image:np.ndarray = None
    gray_image:np.ndarray = None
    pred:np.ndarray = None
    segmentation:str = None
    scale:float = None
    scale_error:float = None
    area:float = None

    def _random_key(self):
        return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))

    def generate_key(self):
        self.key = self._random_key()
        self.build_path()
        while self.path.exists():
            self.key = self._random_key()
            self.build_path()
        return self.key
    
    def build_path(self):
        global temp
        self.path = temp/(self.key + '.jpg')
        self.results_path = temp/(self.key + '.json')
    
    def get_image(self):
        self.image = imread(self.path)/255
        self.gray_image = imread(self.path, as_gray=True)
    
    def get_scale(self):
        while self.gray_image is None: continue
        self.scale, self.scale_error = find_scale(self.gray_image)
        self.update_results()
    
    def get_segmentation(self):
        while self.gray_image is None: continue
        global model
        self.pred = model.predict(self.gray_image[np.newaxis, ..., np.newaxis])[0, ..., 0]
        threading.Thread(target=self.build_seg_image).start()
        while self.scale is None: continue
        self.area = self.pred.sum()*self.scale
        self.update_results()
    
    def build_seg_image(self):
        DX, DY = np.gradient((self.pred > 0.5).astype(int))
        contour = DX.astype(bool) | DY.astype(bool)
        over = np.where(np.repeat(self.pred[..., np.newaxis], 3, axis=-1) > 0.5, self.image, self.image/2)
        final = np.where(np.repeat(contour[..., np.newaxis], 3, axis=-1), 1, over)
        buffered = BytesIO()
        Image.fromarray((final * 255).astype(np.uint8)).save(buffered, format='JPEG')
        self.segmentation = base64.b64encode(buffered.getvalue()).decode()
        self.update_results()
    
    def update_results(self):
        with open(self.results_path, 'w') as file:
            json.dump({
                'scale':self.scale,
                'scale_error':self.scale_error,
                'area':self.area,
                'segmentation':self.segmentation
            }, file)
    
    def load_result(self, name):
        value = None
        try:
            with open(self.results_path, 'r') as file:
                value = json.load(file)[name]
        except Exception as FileNotFoundError: pass
        return value

    def fromkey(key):
        processor = ImageProcessor(key=key)
        processor.build_path()
        return processor
    
    def await_for(self, value_name):
        value = self.load_result(value_name)
        while value is None: 
            value = self.load_result(value_name)
        return value
    
    def run(self):
        self.get_image()
        threading.Thread(target=self.get_scale).start()
        threading.Thread(target=self.get_segmentation).start()

@app.route('/', methods=['POST'])
def upload():
    processor = ImageProcessor()
    key = processor.generate_key()
    request.files['image'].save(processor.path)
    processor.run()

    return jsonify({'key': key})

@app.route('/<value_name>/<key>', methods=['GET'])
def get(value_name, key):
    if value_name == 'finish':
        for item in temp.glob(f'{key}*'):
            item.unlink()
        return 'OK'
    else:
        return jsonify({value_name: ImageProcessor.fromkey(key).await_for(value_name)})

if __name__ == '__main__':
    app.run(port=5000, debug=True, threaded=True)