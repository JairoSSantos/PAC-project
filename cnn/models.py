import numpy as np
import scipy.ndimage as nd
from scipy.signal import find_peaks
from skimage.color import rgb2gray
from skimage.filters import farid, gabor_kernel, threshold_minimum
from sklearn.cluster import KMeans
from dataclasses import dataclass
from abc import ABC, abstractmethod

def variance(image:np.ndarray, size:list[int, int]|int) -> np.ndarray:
    return nd.uniform_filter(image**2, size) - nd.uniform_filter(image, size)**2

def fft2d(image:np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image)))

def peaks_filter(x:np.ndarray, y:np.ndarray, peaks:np.ndarray, k:int=1) -> np.ndarray:
    ypeaks = y[peaks]
    max_peak = peaks[ypeaks == ypeaks.max()]
    for _ in range(k-1):
        max_peak = peaks[ypeaks == ypeaks[np.isin(ypeaks, y[x < x[max_peak][0]])].max()]
    return max_peak

def pixel_scale(image:np.ndarray):
    fft = np.abs(fft2d(image))
    xfreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[0], 1))
    yfreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[1], 1))
    
    ymean = np.mean(fft, axis=1)
    xmean = np.mean(fft, axis=0)
    
    (ypeaks, _), (xpeaks, _) = find_peaks(ymean), find_peaks(xmean)
    Py = peaks_filter(yfreqs, ymean, ypeaks, 2)
    Px = peaks_filter(xfreqs, xmean, xpeaks, 2)
    
    return np.abs(xfreqs[Px][0]), np.abs(xfreqs[Py][0])

def threshold_kmeans(image:np.ndarray):
    img_flat = image.flatten()
    clusters = KMeans(3).fit_predict(img_flat.reshape(-1, 1))
    _min = None
    for label in np.unique(clusters):
        subset = img_flat[clusters == label]
        _, bins = np.histogram(subset, bins=50)
        if _min == None or bins.max() < _min: 
            _min = subset.max()
    return image < _min

def power(image, kernel):
    image = (image - image.mean())/image.std() #normalization
    return np.sqrt(nd.convolve(image, np.real(kernel), mode='wrap')**2 + 
                   nd.convolve(image, np.imag(kernel), mode='wrap')**2)

@dataclass
class Model(ABC):
    opening_iter:int
    closing_iter:int
    dilation_iter:int

    @abstractmethod
    def predict(self):
        pass

    def morphological_processing(self, image:np.ndarray) -> np.ndarray:
        image = nd.binary_opening(image, iterations=self.opening_iter)
        image = nd.binary_closing(image, iterations=self.closing_iter)
        image = nd.binary_dilation(image, iterations=self.dilation_iter)
        return image

@dataclass
class EdgeBlur(Model):
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
            threshold_kmeans(
                nd.minimum_filter(var, self.minimum_size)
            )
        )
        self.mask = mask.copy()
        fx, fy = pixel_scale(image)
        return np.sum(mask)*fx*fy

@dataclass
class FourierGabor(Model):
    def predict(self, image:np.ndarray) -> float:
        if len(image.shape) > 2: 
            img = rgb2gray(image)
    
        fx, fy = pixel_scale(img)
        filtered = power(img, gabor_kernel(fx, theta=0)) + power(img, gabor_kernel(fy, theta=np.pi/2))
        mask = self.morphological_processing(filtered < threshold_minimum(filtered))
        self.mask = mask.copy()
        return np.sum(mask)*fx*fy