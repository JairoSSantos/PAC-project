import numpy as np
from preprocess import *
from scipy.ndimage import binary_opening, binary_dilation
from sklearn.cluster import KMeans
from dataclasses import dataclass

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
            image = align(image) # rotação automática com transformação de Hough
    
        (fx, std_fx), (fy, std_fy) = pixel_scale(image) # Encontrar a proporção pixel-milímetro
        fx = 0.025 if fx < 0.025 else fx
        fy = 0.025 if fy < 0.025 else fy
        
        filtered = gabor_filter(image, fx, fy)

        mask = filtered < threshold_kmeans(filtered, nclusters=self.nclusters, nbins=self.nbins) # segmentação
        mask = binary_opening(mask, iterations=self.opening) # abertura
        mask = binary_dilation(mask, iterations=self.dilation) # dilatação
        Ap = np.sum(mask) # cálculo da área
        Ap_error = np.sum(mask*filtered) + np.sum(np.logical_not(mask)*filtered) # * 255**2

        return Ap*fx*fy, propagation_of_error(Ap, fx, fy, Ap_error, std_fx, std_fy)