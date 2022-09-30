import numpy as np
import scipy.ndimage as nd
from scipy.signal import find_peaks
from skimage.color import rgb2gray
from skimage.filters import farid, gabor, threshold_triangle, threshold_isodata
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny
from skimage.morphology import disk
from sklearn.cluster import KMeans
from dataclasses import dataclass
from abc import ABC, abstractmethod

def variance(image:np.ndarray, size:list[int, int]|int) -> np.ndarray:
    '''
    Variância de uma imagem.

    Args
        image: imagem na forma de um array bidimensional (escala de cinza).
        size: tamanho do núcleo de convolução.
    
    Returns
        var: variância no formato de um array com as mesmas dimensões da imagem de entrada.
    '''
    var = nd.uniform_filter(image**2, size) - nd.uniform_filter(image, size)**2
    return var

def fft1d(y:np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    '''
    Aplica a transformada de fourier em um sinal unidimensional.

    Args
        y: array unidimensional com os valores do sinal.
    
    Returns
        fft: transformada de fourier do sinal.
        freqs: frequências associadas à transformada do sinal.
    '''
    fft = np.abs(np.fft.fftshift(np.fft.fft(np.fft.ifftshift(y))))
    freqs = np.fft.ifftshift(np.fft.fftfreq(len(fft), 1))
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
    fft = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image)))
    ifreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[0], 1))
    jfreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[1], 1))
    return fft, ifreqs, jfreqs

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

def propagation_of_error(Ap, fx, fy, error_Ap, error_fx, error_fy):
    return np.sqrt(
        (fx*fy*error_Ap)**2 +
        (Ap*fy*error_fx)**2 +
        (Ap*fx*error_fy)**2
    )

@dataclass
class Segmentation(ABC):
    opening:int
    closing:int
    dilation:int

    @abstractmethod
    def predict(self):
        pass

    def morphological_processing(self, image:np.ndarray) -> np.ndarray:
        if self.opening > 0: image = nd.binary_opening(image, iterations=self.opening)
        if self.closing > 0: image = nd.binary_closing(image, iterations=self.closing)
        if self.dilation > 0: image = nd.binary_dilation(image, iterations=self.dilation)
        return image

@dataclass
class EdgeBlur(Segmentation):
    variance_size:int
    minimum_size:int

    def predict(self, image:np.ndarray) -> float:
        if len(image.shape) > 2: 
            image = rgb2gray(image)
        var = variance( #blur
                farid(image), #edge
                self.variance_size
            )
        mask = self.morphological_processing(
            threshold_triangle(
                nd.minimum_filter(var, self.minimum_size),
                nbins=50
            )
        )
        (fx, stdfx), (fy, stdfy) = pixel_scale(image)
        area = np.sum(mask)*fx*fy
        return area, area*np.sqrt((fy*stdfx)**2 + (fx*stdfy)**2)

@dataclass
class FourierGabor(Segmentation):
    minimum:int=5
    maximum:int=5
    median:int=5
    nbins:int=50

    def predict(self, image:np.ndarray, auto_rotate:bool=False) -> float:
        if len(image.shape) > 2: 
            image = rgb2gray(image)
        if auto_rotate:
            image = rotate(image, find_slope(image), mode='reflect')
    
        (fx, std_fx), (fy, std_fy) = pixel_scale(image)

        xreal, ximag = gabor(image, fx, 0, n_stds=3)
        yreal, yimag = gabor(image, fy, np.pi/2, n_stds=3)
        filtered = np.sqrt(xreal**2 + ximag**2) + np.sqrt(yreal**2 + yimag**2)

        if self.minimum: filtered = nd.minimum_filter(filtered, footprint=disk(self.minimum))
        if self.maximum: filtered = nd.maximum_filter(filtered, footprint=disk(self.maximum))
        if self.median: filtered = nd.median_filter(filtered, footprint=disk(self.median))

        mask = filtered < threshold_isodata(filtered, nbins=self.nbins)
        mask = self.morphological_processing(mask)
        Ap = np.sum(mask)

        return Ap*fx*fy, propagation_of_error(Ap, fx, fy, 0, std_fx, std_fy)