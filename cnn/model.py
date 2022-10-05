import numpy as np
import scipy.ndimage as nd
from scipy.signal import find_peaks
from skimage.color import rgb2gray
from skimage.filters import gabor
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny
from sklearn.cluster import KMeans
from dataclasses import dataclass

def fft1d(y:np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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

def fft2d(image:np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    '''
    Aplica a transformada de fourier em uma imagem bidimensional.

    Args
        image: imagem na forma de um array bidimensional (escala de cinza).
    
    Returns
        fft: a imagem no domínio das frequências.
        ifreqs, jfreqs: frequências associadas à transformada do sinal em cada dimensão.
    '''
    fft = np.fft.fft2(np.fft.ifftshift(image))
    yfreqs = np.fft.fftfreq(fft.shape[0], 1)
    xfreqs = np.fft.fftfreq(fft.shape[1], 1)
    return fft, xfreqs, yfreqs

def peaks_filter(x:np.ndarray, y:np.ndarray, peaks:np.ndarray, k:int=1) -> np.ndarray:
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

def higher_frequency(signal_1d:np.array) -> float:
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

def pixel_scale(image:np.ndarray) -> tuple[tuple[float, float], tuple[float, float]]:
    '''
    Encontrar a escala milímetro/pixel utilizando transformada de fourier da image.

    Args
        image: imagem no formado de um array bidimensional (em escalas de cinza).
    
    Return
        (fx, std_fx), (fy, std_fy): escalas encontradas para x e y em seus respectivos desvios.
    '''
    Fx = np.apply_along_axis(higher_frequency, 0, image)
    Fy = np.apply_along_axis(higher_frequency, 1, image)
    Fx, Fy = Fx[Fx > 0.025], Fy[Fy > 0.025] # aplicando um limite para baixas frequências
    return (np.median(Fx), np.std(Fx)), (np.median(Fy), np.std(Fy))

def find_slope(image:np.ndarray, n_angles=500) -> float:
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
    slopes = np.degrees(angles + np.pi/2) # inclinação em relação ao eixo x
    slope_values = np.unique(slopes)
    probs = np.array([np.sum(slopes == val) for val in slope_values])
    angle = slope_values[probs == probs.max()][0] # angulo com maior probabilidade
    return angle

def threshold_kmeans(img, nclusters, nbins) -> float:
    data = img.flatten()
    km = KMeans(nclusters)
    cluster_id = km.fit_predict(data.reshape(-1, 1))
    min_bin = None
    for ii in np.unique(cluster_id):
        subset = data[cluster_id == ii]
        hist, bins = np.histogram(subset, bins=nbins)
        if min_bin == None or bins.max() < min_bin:
            min_bin = np.max(subset) #bins[:-1][hist == hist.min()][0]
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

    def predict(self, image:np.ndarray, auto_rotate:bool=False) -> tuple[float, float]:
        if len(image.shape) > 2: 
            image = rgb2gray(image) # transformar imagem para escala de cinza
        if auto_rotate:
            image = rotate(image, -find_slope(image), mode='reflect') # rotação automática com transformação de Hough
    
        (fx, std_fx), (fy, std_fy) = pixel_scale(image) # Encontrar a proporção pixel-milímetro

        xreal, ximag = gabor(image, fx, 0, n_stds=3) # filtros de Gabor no eixo x
        yreal, yimag = gabor(image, fy, np.pi/2, n_stds=3) # filtros de Gabor no eixo y
        filtered = np.sqrt(xreal**2 + ximag**2) + np.sqrt(yreal**2 + yimag**2) # imagem filtrada

        mask = filtered < threshold_kmeans(filtered, nclusters=self.nclusters, nbins=self.nbins) # segmentação
        mask = nd.binary_opening(mask, iterations=self.opening) # abertura
        mask = nd.binary_dilation(mask, iterations=self.dilation) # dilatação
        Ap = np.sum(mask) # cálculo da área

        return Ap*fx*fy, propagation_of_error(Ap, fx, fy, 0, std_fx, std_fy)