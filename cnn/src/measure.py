import numpy as np
import tensorflow as tf
from abc import ABC, abstractmethod
from scipy.stats import mode, circmean, circstd
from scipy.ndimage import gaussian_filter
from tensorflow.keras import Sequential, Input
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

def scale_from_mask(area, mask):
    return area/mask.sum(axis=(-1, -2))

class Measurer(ABC, Sequential):
    '''
    Measurer é uma classe abstrata criada para facilitar a implementação de um modelo tensorflow com base em uma função numpy que extrai medidas da imagem.
    '''
    def __init__(self, input_shape, mtype):
        assert len(input_shape) == 2
        self.mtype = mtype

        measure_layer = Lambda(lambda images: tf.map_fn(self._appraise, images, fn_output_signature=self.mtype))

        Sequential.__init__(self, 
        layers=[
            Input(input_shape),
            measure_layer,
        ])
    
    @tf.function
    def _appraise(self, img):
        return tf.stack(tf.numpy_function(self.appraise, [img], [self.mtype, self.mtype]))

    @abstractmethod
    def appraise(self): pass

class ScaleMeasurer(Measurer):
    '''
    Modelo tensorflow para medir a escala das imagens.
    '''
    def __init__(self, input_shape, sigma):
        Measurer.__init__(self, input_shape, mtype=tf.float64)
        self.sigma = sigma

    def appraise(self, img):
        return find_scale(img, sigma=self.sigma)

class SlopeMeasurer(Measurer):
    '''
    Modelo tensorflow para medir a inclinação das imagens com relação ao papel milimetrado.
    '''
    def __init__(self, input_shape, beta):
        Measurer.__init__(self, input_shape, mtype=tf.float64)
        self.beta = beta

    def appraise(self, img):
        return find_slope(img, beta=self.beta)