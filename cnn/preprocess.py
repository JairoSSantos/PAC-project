import numpy as np
from scipy.signal import find_peaks
from scipy.stats import mode
from skimage.color import rgb2gray
from skimage.filters import gabor, sobel
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny

def align(image):
    '''
    Alinhar imagem pela transformação de Hough.
    '''
    return rotate(image, find_slope(image), mode='reflect')

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
    '''
    Encontrar a escala milímetro/pixel utilizando transformada de fourier das bordas da imagem.

    Args
        image: imagem no formado de um array bidimensional (em escalas de cinza).
    
    Return
        fx, fy: escalas encontradas para x e y.
    '''
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