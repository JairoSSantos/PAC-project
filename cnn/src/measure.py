import numpy as np
import tensorflow as tf
from scipy.stats import mode, circmean, circstd
from scipy.ndimage import gaussian_filter
from tensorflow.keras import Model, Input
from tensorflow.keras.layers import Lambda

def FFT(x):
    return np.abs(np.fft.fft(x))

def FFT2(x):
    return np.abs(np.fft.fftshift(np.fft.fft2(x)))

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
        dI_gauss = gaussian_filter(dI, sigma)
        D = np.apply_along_axis(lambda y: freqs[pos][np.argmax(PSD(y)[pos])], 1, dI_gauss)
        fs.append(mode(D).mode[0])
        delta.append(0.5/dI.shape[1])
    
    (fx, fy), (dx, dy) = fs, delta
    return fx*fy, np.sqrt((dx*fy)**2 + (dy*fx)**2)

def find_slope(img, beta=3e-3):
    fft2d = FFT2(img)
    loc = fft2d > fft2d.max()*beta
    X = np.arange(-img.shape[1]//2, img.shape[1]//2)
    Y = np.arange(-img.shape[0]//2, img.shape[0]//2)
    X, Y = np.meshgrid(X, Y)
    H = 90 - np.degrees(np.arctan2(Y[loc], X[loc]))%90
    return circmean(H, low=0, high=90), circstd(H, low=0, high=90)

def measurer(function, input_shape, dtype, name, *args, **kwargs):
    def appraise(x):
        return function(x, *args, **kwargs)

    @tf.function
    def _appraise(x):
        return tf.stack(tf.numpy_function(appraise, [x], [dtype, dtype]))
    
    @tf.function
    def _mapper(X):
        return tf.map_fn(_appraise, X, fn_output_signature=dtype)

    X = Input(input_shape)
    return Model(
        inputs= X, 
        outputs= Lambda(_mapper)(X),
        name= name
    )

def scale_from_mask(area, mask):
    return area/mask.sum(axis=(-1, -2))