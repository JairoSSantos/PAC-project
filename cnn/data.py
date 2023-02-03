import os
import glob
import numpy as np
import pandas as pd
import tensorflow as tf
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
    return pd.read_csv(os.path.join(DATASET_PATH, 'info.csv'))

def get_random(n:int=1, seed:Any=None, grayscale:bool=True, stack:bool=False, as_tensor:bool=False):
    files = glob.glob(os.path.join(DATASET_PATH, '*/*.jpg'), recursive=True)
    images = []
    for jpg_file in np.random.default_rng(seed).choice(files, size=n, replace=False):
        img = imread(jpg_file)/255
        if grayscale: img = rgb2gray(img)
        lbl = (imread(os.path.splitext(jpg_file)[0] + '.png')/255).astype(int)
        images.append((img, lbl))
    if n == 1: return images[0]
    elif stack: return np.stack(images, axis=1)
    elif as_tensor: return tf.expand_dims(tf.stack(images, axis=1), axis=-1)

def calc_weights(lbls, vmax=2, verbose=False):
    assert vmax > 1
    height, width = lbls.shape[1:3]
    X, Y, _ = tf.meshgrid(tf.range(width, dtype=tf.float32), tf.range(height, dtype=tf.float32), tf.zeros(1, dtype=tf.float32))
    edges = tf.reduce_any(tf.image.sobel_edges(lbls) != 0, axis=-1)
    W = []
    T = lbls.shape[0]
    for i, (edge_points, lbl) in enumerate(zip(edges, lbls)):
        Ex = X[edge_points][tf.newaxis, tf.newaxis]
        Ey = Y[edge_points][tf.newaxis, tf.newaxis]
        R = np.sqrt((Ex - X)**2 + (Ey - Y)**2)
        R_min = tf.expand_dims(tf.reduce_min(R, axis=-1), axis=-1)
        W.append(norm(tf.where(lbl == 0, tf.sqrt(R_min), 0), vmin=1, vmax=vmax))
        if verbose: 
            j = (i + 1)/T
            print('\rCalculando pesos:|' + '='*int(20*j) + ' '*int(20*(1 - j)) + f'|{i + 1}/{T} ({j*100:.2f}%)', end='')
    if verbose: print()
    return tf.cast(tf.stack(W), dtype=lbls.dtype)

def flipping_augmentation(collection, axis:tuple=(1, 2), concat_axis:int=0):
    '''
    Aumento os dados espelhando as imagens.

    Args:
        collection: Coleção de imagens.
        axis: Eixos que serão espelhados.
        concat_axis (opcional): Eixo de concatenação.
    
    Return:
        A coleção de imagens espelhadas nas direções definidas em `axis`.
    '''
    assert len(axis) == 2, '`axis` deve conter exatamente 2 valores.'
    return tf.concat((
            collection,
            tf.reverse(collection, axis=axis),
            tf.reverse(collection, axis=axis[:0]),
            tf.reverse(collection, axis=axis[1:2])
    ), axis=concat_axis)

def load_dataset(grayscale:bool=True, augmentation:bool=True, weights:bool=False, vmax:int=2, verbose:bool=False):
    '''
    Carregar conjunto de dados para treinamento.

    Args:
        grayscale (opcional): Se True, as imagens serão retornadas em tons de cinza.
        augmentation (opcional): Se True, os dados serão aumentados em 4 vezes espelhando as imagens horizontalmente e verticalmente.
    
    Return:
        (x_train, y_train), (x_test, y_test): Conjunto de dados.
    '''
    # x.shape = [N, H, W, 3]
    # y.shape = [N, H, W, 1]
    x_train = tf.stack(imread_collection(glob.glob(os.path.join(TRAIN_PATH, '*.jpg'))).concatenate()/255)
    y_train = tf.expand_dims(tf.stack(imread_collection(glob.glob(os.path.join(TRAIN_PATH, '*.png'))).concatenate()/255), axis=-1)
    x_test = tf.stack(imread_collection(glob.glob(os.path.join(TEST_PATH, '*.jpg'))).concatenate()/255)
    y_test = tf.expand_dims(tf.stack(imread_collection(glob.glob(os.path.join(TEST_PATH, '*.png'))).concatenate()/255), axis=-1)

    if grayscale: # x.shape = [N, H, W, 1]
        x_train = tf.image.rgb_to_grayscale(x_train)
        x_test = tf.image.rgb_to_grayscale(x_test)
    
    if weights: # y.shape = [N, H, W, 2]
        y_train = tf.concat((y_train, calc_weights(y_train, vmax=vmax, verbose=verbose)), axis=-1)
        y_test = tf.concat((y_test, calc_weights(y_test, vmax=vmax, verbose=verbose)), axis=-1)
    
    if augmentation: # shape = [4*N, H, W, ...]
        x_train = flipping_augmentation(x_train, axis=(1, 2), concat_axis=0)
        y_train = flipping_augmentation(y_train, axis=(1, 2), concat_axis=0)
        x_test = flipping_augmentation(x_test, axis=(1, 2), concat_axis=0)
        y_test = flipping_augmentation(y_test, axis=(1, 2), concat_axis=0)

    return (x_train, y_train), (x_test, y_test)

def norm(x, vmin:float=0, vmax:float=1):
    '''
    Normalizar valores de um array "x" para determinados limites (vmin, vmax).

    Args:
        x: Array n-dimensional com os valores que serão normalizados.
        vmin (opcional): Limite inferior (default: 0).
        vmax (opcional): Limite superior (default: 1).
    
    Return:
        y: Tensor normalizado.
    '''
    return vmin + (x - tf.reduce_min(x)) * (vmax - vmin)/(tf.reduce_max(x) - tf.reduce_min(x))

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
        lbl_name = area + '.png' # noma da mascara
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