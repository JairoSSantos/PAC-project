import numpy as np
from scipy.signal import find_peaks
from skimage.color import rgb2gray
from skimage.filters import farid_v, farid_h
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny

def norm(arr, vmin=0, vmax=1):
    return vmin + (arr - arr.min())*(vmax - vmin)/(arr.max() - arr.min())

def rotation_augmentation(image):
    yflip = image[::-1]
    xflip = image[:, ::-1]
    aug = []
    for angle in np.arange(0, 360, 90):
        aug.append(rotate(yflip, angle))
        aug.append(rotate(xflip, angle))
    return aug

def align(image):
    '''
    Alinhar imagem pela transformação de Hough.
    '''
    return rotate(image, find_slope(image), mode='reflect')

def find_slope(image:np.ndarray, n_angles=500):
    '''
    Encontrar inclinação da imagem utilizando transformação de Hough.

    Args
        image: imagem no formado de um array bidimensional (em escalas de cinza).
    
    Return
        angle: inclinação da imagem (em graus).
    '''
    _, angles, _ = hough_line_peaks(*hough_line(
        canny(image), # bordas da imagem
        np.linspace(-np.pi/2, np.pi/2, n_angles) # angulos
    ))
    slopes = np.degrees(angles) + 90 # inclinação em relação ao eixo x
    return mode(slopes)[0][0] # angulo com maior ocorrência

def autocorr(x, mode='full'):
    return np.correlate(x, x, mode=mode)

def find_scale(img):
    freq = np.fft.fftfreq(len(img), 1)
    loc = (freq > 0)
    auto_fft = lambda x: norm(np.abs(np.fft.fft(autocorr(x, 'same')))[loc])
    far = np.concatenate([farid_v(img), farid_h(img).T])
    Y = np.apply_along_axis(auto_fft, 0, far.T).mean(axis=1)
    P = find_peaks(Y, height=0.5)[0]
    return freq[loc][P].min()