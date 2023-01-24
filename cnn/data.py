import os
import glob
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.stats import mode
from skimage.color import rgb2gray
from skimage.filters import farid_v, farid_h
from skimage.transform import rotate, hough_line, hough_line_peaks
from skimage.feature import canny
from skimage.io import imread, imread_collection
from typing import Any, Callable

DATASET_PATH = os.path.join(*os.path.split(__file__)[:-1], 'dataset')
TRAIN_PATH = os.path.join(DATASET_PATH, 'train')
TEST_PATH = os.path.join(DATASET_PATH, 'test')

def mapper(func:Callable, stack:bool=True):
    '''
    Decorator para aplicar funções em iteráveis utilizando a função nativa map (obs: todos os valores None serão filtrados).

    Args:
        stack (opcional): Se True, a saída será um array; se False, a saída será uma lista 
                (utilize stack=False para o caso em que o formato (shape) de saída varie para diferentes itens).
    
    Return:
        Função func aplicada a cada item do íterável x.
    '''
    NoneType = type(None)
    def wrapper(x, *args, **kwargs):
        try: y = list(filter(lambda x: type(x) != NoneType, map(lambda x: func(x, *args, **kwargs), x)))
        except TypeError: return func(x, *args, **kwargs)
        else: return np.stack(y) if stack else y
    return wrapper

@mapper
def _extract_from_filepath(filepath:str, get_root:bool=True, get_area:bool=True):
    '''
    Extrair diretório e area do caminho de uma imagem (.jpg) no dataset.
    '''
    root, filename = os.path.split(filepath)
    area, ext = os.path.splitext(filename)
    out = []
    if get_root: out.append(root)
    if get_area: out.append(area)
    return out if ext == '.jpg' else None # filtrar extensões diferentes de .jpg

@mapper
def _get_sample_info(filepath:str):
    '''
    Coletar informações sobre a amostra indicada pelo caminho filepath.
    '''
    root, filename = os.path.split(filepath)
    area, _ = os.path.splitext(filename)
    train = os.path.split(root)[-1]
    im = rgb2gray(imread(filepath))
    f, slope = find_scale(im), find_slope(im)
    rel_area = np.sum(imread(os.path.join(root, area + '.tif'))/255)/np.multiply(*im.shape)
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
    auto_fft = lambda x: norm(np.abs(np.fft.fft(autocorr(x, 'same')))[loc], vmin=0, vmax=1)
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
    return pd.read_csv(os.path.join(DATASET_PATH, 'info.csv'))

def load_random(n:int=1, seed:Any=None, grayscale:bool=True):
    files = _extract_from_filepath(glob.glob(os.path.join(DATASET_PATH, '**'), recursive=True))
    images = []
    for i in np.random.default_rng(seed).integers(0, len(files), n):
        root, area = files[i]
        img = imread(os.path.join(root, area + '.jpg'))
        if grayscale: img = rgb2gray(img)
        lbl = (imread(os.path.join(root, area + '.tif'))/255).astype(int)
        images.append((img, lbl))
    return images

def flipping_augmentation(collection:np.ndarray):
    '''
    Aumento os dados espelhando as imagens.

    Args:
        collection: Coleção de imagens.
    
    Return:
        A coleção de imagens espelhada em quatro direções (esquerda-direita, cima-baixo).
    '''
    return np.concatenate((
            collection,
            collection[:, ::-1],
            collection[:, :, ::-1],
            collection[:, ::-1, ::-1]
    ))

def load_dataset(grayscale:bool=True, as_tensor:bool=False, augmentation:bool=True):
    '''
    Carregar conjunto de dados para treinamento.

    Args:
        grayscale (opcional): Se True, as imagens serão retornadas em tons de cinza.
        as_tensor (opcional): Se True, os dados serão retornados no formato de arrays com 4 dimensões. Se False, os dados serão retornados na forma de arrays com 3 dimensões
        augmentation (opcional): Se True, os dados serão aumentados em 4 vezes espelhando as imagens horizontalmente e verticalmente.
    
    Return:
        (x_train, y_train), (x_test, y_test): Conjunto de dados.
    '''
    x_train = imread_collection(glob.glob(os.path.join(TRAIN_PATH, '*.jpg'))).concatenate()
    y_train = (imread_collection(glob.glob(os.path.join(TRAIN_PATH, '*.tif'))).concatenate()/255).astype(int)
    x_test = imread_collection(glob.glob(os.path.join(TEST_PATH, '*.jpg'))).concatenate()
    y_test = (imread_collection(glob.glob(os.path.join(TEST_PATH, '*.tif'))).concatenate()/255).astype(int)
    if grayscale:
        to_gray = mapper(rgb2gray)
        x_train, x_test = to_gray(x_train), to_gray(x_test)
    if augmentation:
        x_train = flipping_augmentation(x_train)
        x_test = flipping_augmentation(x_test)
        y_train = flipping_augmentation(y_train)
        y_test = flipping_augmentation(y_test)
    if as_tensor:
        return ((x_train[:, :, :, np.newaxis],
                 y_train[:, :, :, np.newaxis]),
                (x_test[:, :, :, np.newaxis],
                 y_test[:, :, :, np.newaxis]))
    else:
        return (x_train, y_train), (x_test, y_test)

def norm(x:np.ndarray, vmin:float=0, vmax:float=1):
    '''
    Normalizar valores de um array "x" para determinados limites (vmin, vmax).

    Args:
        x: Array n-dimensional com os valores que serão normalizados.
        vmin (opcional): Limite inferior (default: 0).
        vmax (opcional): Limite superior (default: 1).
    
    Return:
        y: Array normalizado.
    '''
    y = vmin + (x - x.min())/x.ptp() * (vmax - vmin)
    return y

def split_validation_data(p:float, shuffle:bool=True, seed:Any=None, verbose:bool=True):
    '''
    Separar dados de validação: No diretório DATASET_PATH, os arquivos

    Args:
        p: Fração das imagens que serão usadas para validação, 0 <= p <= 1.
        shuffle (opcional): Se True, os arquivos serão escolhidos aleatoriamente.
        seed (opcional): Seed usada para embaralhar os arquivos (obs: esta informação só será utilizada caso shuffle=True).
        verbose (opcional): Se True, informações sobre a separação dos dados serão exibidas ao final do procedimento.
    '''
    all_files = glob.glob(os.path.join(DATASET_PATH, '**'), recursive=True) # coletar o caminho até todos os arquivos no dataset
    files = _extract_from_filepath(all_files) # separar os diretórios (root) das amostras (imagem e mascara) nomeadas com as respactivas areas
    n_files = len(files) # quantidade de amostras
    split_threshold = int(p*n_files) # quantidade de amostras que serão destinados à validação

    if shuffle: np.random.default_rng(seed).shuffle(files) # embaralhe as amostras, se shuffle for verdadeiro

    for i, (root, area) in enumerate(files): # enumere as informações das amostras
        img_name = area + '.jpg' # nome da imagem
        lbl_name = area + '.tif' # noma da mascara
        dst = TEST_PATH if i < split_threshold else TRAIN_PATH # novo destino dos arquivos
        try: os.rename(os.path.join(root, lbl_name), os.path.join(dst, lbl_name)) # para a mascara: caminho antigo -> novo caminho
        except FileNotFoundError: raise FileNotFoundError(f'A máscara {lbl_name} não foi encontrada, certifique-se que a imagem e sua máscara encontram-se no mesmo diretório.')
        else: os.rename(os.path.join(root, img_name), os.path.join(dst, img_name)) # para a imagem: caminho antigo -> novo caminho

    if verbose:
        tr = n_files - split_threshold
        print('\n'.join((
            f'Foram encontradas {n_files} amostras, totalizando {2*n_files} arquivos. '
            f'Dados para treinamento: {tr} amostras ({tr/n_files*100:.2f}%). '
            f'Dados para validação: {split_threshold} amostras ({split_threshold/n_files*100:.2f}%).'
        )))

def update_info():
    '''
    Atualizar tabela de informações sobre o dataset.
    '''
    pd.DataFrame(
        _get_sample_info(glob.glob(os.path.join(TRAIN_PATH, '*.jpg'))) +
        _get_sample_info(glob.glob(os.path.join(TEST_PATH, '*.jpg'))),
        columns=['area', 'train', 'freq', 'slope', 'label_pixel_area']
    ).sort_values('area').to_csv(os.path.join(DATASET_PATH, 'info.csv'), index=False)

if __name__ == '__main__':
    #split_validation_data(0.26, seed=123)
    update_info()