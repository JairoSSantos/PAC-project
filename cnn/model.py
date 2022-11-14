import numpy as np
import scipy.ndimage as nd
from scipy.signal import find_peaks
from scipy.stats import mode
from skimage.color import rgb2gray
from skimage.filters import gabor, sobel
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny
from sklearn.cluster import KMeans
from dataclasses import dataclass

def fft1d(y:np.ndarray):
    '''
    Aplica a transformada de fourier em um sinal unidimensional.

    Args
        y: array unidimensional com os valores do sinal.
    
    Returns
        fft: transformada de fourier do sinal.
        freqs: frequências associadas à transformada do sinal.
    '''
    fft = np.abs(np.fft.fft(np.fft.ifftshift(y)))
    freqs = np.fft.fftfreq(len(fft), 1)
    return fft, freqs

def peaks_filter(x:np.ndarray, y:np.ndarray, peaks:np.ndarray, k:int=1):
    '''
    Filtrar picos pela altura do sinal.

    Args
        x, y: valores x e y do sinal.
        preaks: posição dos picos.
        k: o k-ésimo pico mais intenso será retornado.
    
    Return
        P: posição do k-ésimo pico mais intenso.
    '''
    ypeaks = y[peaks]
    max_peak = peaks[ypeaks == ypeaks.max()]
    for _ in range(k-1):
        max_peak = peaks[ypeaks == ypeaks[np.isin(ypeaks, y[x < x[max_peak][0]])].max()]
    return max_peak

def higher_frequency(signal_1d:np.array):
    '''
    Encontrar a frequêcia, diferente de zero, associada à maior amplitude de um sinal unidimensional.

    Args
        signal_1d: array contendo os valores do sinal.
    
    Return
        f: módulo da frequência encontrada.
    '''
    fft, freqs = fft1d(signal_1d) # transformada de fourier do sinal
    fft = np.abs(fft) # eliminar termo complexo da transformada de fourier
    
    peaks, _ = find_peaks(fft) # encontrar os picos de frequência
    f = np.abs(freqs[
        peaks_filter(freqs, fft, peaks, 2) # pegar o segundo pico mais intenso
    ][0]) # frequência associada ao pico mais intenso diferente de y(x = 0)
    return f

def pixel_scale(image:np.ndarray):
    '''
    Encontrar a escala milímetro/pixel utilizando transformada de fourier da image.

    Args
        image: imagem no formado de um array bidimensional (em escalas de cinza).
    
    Return
        (fx, std_fx), (fy, std_fy): escalas encontradas para x e y em seus respectivos desvios.
    '''
    Fx = np.apply_along_axis(higher_frequency, 0, image)
    Fy = np.apply_along_axis(higher_frequency, 1, image)
    
    fx = np.median(Fx[Fx > 0.025])
    fy = np.median(Fy[Fy > 0.025])
    
    return (fx, (Fx.max() - Fx.min())/40), (fy, (Fy.max() - Fy.min())/40)

def fft_peak(y, freq):
    fft = np.abs(np.fft.fft(y))
    loc = freq > 0.015
    fft = fft[loc]
    freq = freq[loc]
    return freq[fft == fft.max()][0]

def pixel_scale_edge(img):
    arr = sobel(img)
    height, width = arr.shape
    
    xfreqs = np.fft.fftfreq(width, 1)
    yfreqs = np.fft.fftfreq(height, 1)
    
    Fx = np.apply_along_axis(fft_peak, 1, arr, xfreqs).flat
    Fy = np.apply_along_axis(fft_peak, 0, arr, yfreqs).flat
    
    return mode(Fx).mode[0], mode(Fy).mode[0]

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

def align(image):
    return rotate(image, find_slope(image), mode='reflect')

def gabor_filter(image, fx, fy):
    realx, imagx = gabor(image, fx, 0, n_stds=3) # filtros de Gabor na horizontal
    realy, imagy = gabor(image, fy, np.pi/2, n_stds=3) # filtros de Gabor na vertical
    real45, imag45 = gabor(image, np.sqrt(fx**2 + fy**2), np.pi/4, n_stds=3) # filtros de Gabor em 45 graus
    real135, imag135 = gabor(image, np.sqrt(fx**2 + fy**2), np.pi/4 + np.pi/2, n_stds=3) # filtros de Gabor em 135 graus
    return (
        np.sqrt(realx**2 + imagx**2) + 
        np.sqrt(realy**2 + imagy**2) +
        np.sqrt(real45**2 + imag45**2) +
        np.sqrt(real135**2 + imag135**2)
    )

def threshold_kmeans(img, nclusters, nbins):
    data = img.flatten()
    km = KMeans(nclusters)
    cluster_id = km.fit_predict(data.reshape(-1, 1))
    min_bin = None
    for ii in np.unique(cluster_id):
        subset = data[cluster_id == ii]
        hist, bins = np.histogram(subset, bins=nbins)
        if min_bin == None or bins.max() < min_bin:
            min_bin = np.max(subset)
    return min_bin

def propagation_of_error(Ap, fx, fy, error_Ap, error_fx, error_fy) -> float:
    return np.sqrt(
        (fx*fy*error_Ap)**2 +
        (Ap*fy*error_fx)**2 +
        (Ap*fx*error_fy)**2
    )

@dataclass
class FourierGabor:
    nclusters:int = 3 # quantidade de núclos de cinza para segmentação
    nbins:int = 50 # quantidade de bins do histograma de cinza
    opening:int = 6 # número de iterações na abertra
    dilation:int = 2 # número de iterações na dilatação

    def predict(self, image:np.ndarray, auto_rotate:bool=False):
        if len(image.shape) > 2: 
            image = rgb2gray(image) # transformar imagem para escala de cinza
        if auto_rotate:
            image = rotate(image, find_slope(image), mode='reflect') # rotação automática com transformação de Hough
    
        (fx, std_fx), (fy, std_fy) = pixel_scale(image) # Encontrar a proporção pixel-milímetro
        fx = 0.025 if fx < 0.025 else fx
        fy = 0.025 if fy < 0.025 else fy
        
        filtered = gabor_filter(image, fx, fy)

        mask = filtered < threshold_kmeans(filtered, nclusters=self.nclusters, nbins=self.nbins) # segmentação
        mask = nd.binary_opening(mask, iterations=self.opening) # abertura
        mask = nd.binary_dilation(mask, iterations=self.dilation) # dilatação
        Ap = np.sum(mask) # cálculo da área
        Ap_error = np.sum(mask*filtered) + np.sum(np.logical_not(mask)*filtered) # * 255**2

        return Ap*fx*fy, propagation_of_error(Ap, fx, fy, Ap_error, std_fx, std_fy)