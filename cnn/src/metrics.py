from scipy.stats import mode
from scipy.signal import find_peaks
from skimage.feature import canny
from skimage.filters import farid_v, farid_h
from skimage.transform import rotate, hough_line, hough_line_peaks

def _get_sample_info(filepath:str):
    '''
    Coletar informações sobre a amostra indicada pelo caminho filepath.
    '''
    root, filename = os.path.split(filepath)
    area, _ = os.path.splitext(filename)
    train = os.path.split(root)[-1]
    im = rgb2gray(imread(filepath))
    f, slope = find_scale(im), find_slope(im)
    rel_area = np.sum(imread(os.path.join(root, area + '.png'))/255)/np.multiply(*im.shape)
    return float(area), train, f, slope, rel_area

def align(image:np.ndarray):
    '''
    Alinhar imagem pela transformação de Hough.
    '''
    return rotate(image, find_slope(image), mode='reflect')

def autocorr(x:np.ndarray, mode:str='full'):
    '''
    Autocorrelação de um sinal.

    Args:
        x: Sinal no qual será feita a autocorrelação.
        mode (opcional): Tipo de autocorrelação (default: 'full').
    
    Return:
        C_xx: Autocorrelação do sinal x.
    '''
    C_xx = np.correlate(x, x, mode=mode)
    return C_xx

def find_scale(img:np.ndarray):
    '''
    Encontrar escala píxel-milimetro.

    Args:
        img: Imagem em escala de cinza no formato de um array bidimentional.
    
    Return:
        f: Quantidade de milímetros por píxel
    '''
    freq = np.fft.fftfreq(len(img), 1)
    loc = (freq > 0)
    auto_fft = lambda x: norm(np.abs(np.fft.fft(autocorr(x, 'same')))[loc], vmin=0, vmax=1).numpy()
    far = np.concatenate([farid_v(img), farid_h(img).T])
    Y = np.apply_along_axis(auto_fft, 0, far.T).mean(axis=1)
    P = find_peaks(Y, height=0.5)[0]
    f = freq[loc][P].min()
    return f

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
    angle = mode(slopes)[0][0] # angulo com maior ocorrência
    return angle

def get_info():
    '''
    Pegar informações sobre as amostras do dataset.
    '''
    return pd.read_csv(os.path.join(config.DATASET, 'info.csv'))

def update_info():
    '''
    Atualizar tabela de informações sobre o dataset.
    '''
    pd.DataFrame(
        _get_sample_info(glob.glob(os.path.join(config.TRAIN, '*.jpg'))) +
        _get_sample_info(glob.glob(os.path.join(config.TEST, '*.jpg'))),
        columns=['area', 'train', 'freq', 'slope', 'label_pixel_area']
    ).sort_values('area').to_csv(os.path.join(config.DATASET, 'info.csv'), index=False)