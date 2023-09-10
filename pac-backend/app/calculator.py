import numpy as np
from skimage.color import rgb2gray
from skimage.transform import resize
from skimage import morphology
from skimage.segmentation import mark_boundaries
from scipy import ndimage
from scipy.stats import mode
from tensorflow.keras.saving import load_model
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image

HERE = Path(__file__).parent
MODEL = load_model(HERE/'unet-0.41.h5', compile=False)
IMG_SIZE = (256, 256)

def FFT(x):
    return np.abs(np.fft.fft(x))

def Cxx(x):
    return np.correlate(x, x, mode='same')

def PSD(x):
    return FFT(Cxx(x))

def find_scale(img, sigma=2):
    Iy, Ix = np.gradient(img)
    fs= []
    for dI in (Ix, Iy.T):
        freqs = np.fft.fftfreq(dI.shape[1], 1)
        pos = freqs > 0
        dI_gauss = ndimage.gaussian_filter(dI, sigma)
        D = np.apply_along_axis(lambda y: freqs[pos][np.argmax(PSD(y)[pos])], 1, dI_gauss)
        fs.append(mode(D, keepdims=True).mode[0])
    
    fx, fy = fs
    return fx*fy

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

def determinate(image, post_process):
    gray_image = rgb2gray(resize(np.array(image), IMG_SIZE))
    scale = find_scale(gray_image)
    pred = MODEL.predict(gray_image[np.newaxis, ..., np.newaxis], verbose=False)[0, ..., 0]
    pred = pred > 0.5

    for func, config in post_process.items():
        pred = getattr(globals()[config['source']], func)(pred, **config['params'])

    segmentation = resize(pred, image.size)

    return {
        'scale': scale,
        'area': scale*pred.sum(),
        'segmentation': build_overlay(segmentation, image)
    }