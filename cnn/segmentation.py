import numpy as np
import scipy.ndimage as nd
from scipy.signal import find_peaks
from skimage.color import rgb2gray
from skimage.filters import farid
from sklearn.cluster import KMeans
from dataclasses import dataclass

def variance(image:np.array, size:list[int, int]|int):
    return nd.uniform_filter(image**2, size) - nd.uniform_filter(image, size)**2

def fft2d(image:np.array):
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image)))

def peaks_filter(x:np.array, y:np.array, peaks:np.array, k:int=1):
    ypeaks = y[peaks]
    max_peak = peaks[ypeaks == ypeaks.max()]
    for _ in range(k-1):
        max_peak = peaks[ypeaks == ypeaks[np.isin(ypeaks, y[x < x[max_peak][0]])].max()]
    return max_peak

def pixel_scale_1d(signal:np.array):
    fft = np.abs(np.fft.fftshift(np.fft.fft(np.fft.ifftshift(signal))))
    freqs = np.fft.ifftshift(np.fft.fftfreq(len(fft), 1))
    return np.abs(freqs[peaks_filter(freqs, fft, find_peaks(fft)[0], 2)][0])

def pixel_scale(image:np.array):
    '''fft = np.abs(fft2d(image))
    xfreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[0], 1))
    yfreqs = np.fft.ifftshift(np.fft.fftfreq(fft.shape[1], 1))
    
    ymean = np.mean(fft, axis=1)
    xmean = np.mean(fft, axis=0)
    
    (ypeaks, _), (xpeaks, _) = find_peaks(ymean), find_peaks(xmean)
    Py = peaks_filter(yfreqs, ymean, ypeaks, 2)
    Px = peaks_filter(xfreqs, xmean, xpeaks, 2)
    
    return np.abs(xfreqs[Px][0]), np.abs(xfreqs[Py][0])'''
    FX = np.apply_along_axis(pixel_scale_1d, 0, image)
    FY = np.apply_along_axis(pixel_scale_1d, 1, image)
    fxhist, fxbins = np.histogram(FX, bins=25)
    fyhist, fybins = np.histogram(FX, bins=25)
    return (fxbins[:-1][fxhist == fxhist.max()][0], FX.std()), (fybins[:-1][fyhist == fyhist.max()][0], FY.std())

def threshold_kmeans(image:np.array):
    img_flat = image.flatten()
    clusters = KMeans(3).fit_predict(img_flat.reshape(-1, 1))
    _min = None
    for label in np.unique(clusters):
        subset = img_flat[clusters == label]
        _, bins = np.histogram(subset, bins=50)
        if _min == None or bins.max() < _min: 
            _min = subset.max()
    return image < _min

def morphological_processing(image:np.array, opening_iter:int=1, closing_iter:int=1, dilation_iter:int=1):
    image = nd.binary_opening(image, iterations=opening_iter)
    image = nd.binary_closing(image, iterations=closing_iter)
    image = nd.binary_dilation(image, iterations=dilation_iter)
    return image

@dataclass
class Model:
    variance_size:int
    minimum_size:int
    opening_iter:int
    closing_iter:int
    dilation_iter:int

    def predict(self, image:np.array):
        if len(image.shape) > 2: 
            image = rgb2gray(image)
        var = nd.minimum_filter(variance(farid(image), self.variance_size), self.minimum_size)
        mask = morphological_processing(
            threshold_kmeans(var),
            self.opening_iter,
            self.closing_iter,
            self.dilation_iter
        )
        self.mask = mask.copy()
        (fx, fx_std), (fy, fy_std) = pixel_scale(image)
        return np.sum(mask)*fx*fy, np.sum(mask)*np.sqrt((fy*fx_std)**2 + (fx*fy_std)**2)

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from DScontrol import *
    import time

    #plt.ion()

    model = Model(15, 5, 15, 1, 5)

    fig, axs = plt.subplots(2, 5, figsize=(18, 8))
    n = 10
    for i, (img, name) in enumerate(random_images(n, names=True)):
        ax = axs[i%2, i%5]
        ax.imshow(img)
        area, std = model.predict(img)
        ax.contour(model.mask, cmap='plasma')
        ax.text(5, 270, f'{float(DS.loc[DS.filename == name].area):.2f}; {area:.2f}({std:.2f})')
        ax.axis('off')
        ax.set_title(name)
    #plt.show(block=False)
    
    '''predict, process_time = [], []
    total = len(DS)
    start = None
    for i, filename in enumerate(DS.filename):
        start = time.time()

        predict.append(model.predict(get(filename)))
        process_time.append(time.localtime(time.time() - start).tm_sec)

        tpi = np.mean(process_time)
        print(f'{i+1}/{total}|{(i/total*100):.2f}%|PI: {tpi:.1f}sec|ET: {tpi*(total-i-1)/60:.1f}min'+' '*10, end='\r')

    DS['predict'] = predict
    DS['process_time'] = process_time
    DS['disp'] = DS.area - DS.predict
    DS['error_abs'] = np.abs(DS.disp)
    DS['error_rel'] = DS.error_abs/DS.area*100

    dss = DS.sort_values('area')
    plt.figure()
    plt.plot(dss.area.values, '+', alpha=0.8, label='Valor Real')
    plt.plot(dss.predict.values, '+', alpha=0.8, label='Valor Encontrado')
    plt.bar(range(len(dss)), dss.error_abs, color='tab:red', alpha=0.4, label='Erro absoluto')
    plt.legend()'''
    
    plt.show()