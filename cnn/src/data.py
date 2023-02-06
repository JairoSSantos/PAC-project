import numpy as np
import pandas as pd
import tensorflow as tf
from skimage.io import imread
from typing import Any, Callable
from .config import Paths

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

def load_collection(pattern, grayscale=False, normalize=True, as_tensor=True):
    collection = tf.stack(mapper(imread, stack=False)(pattern, as_gray=grayscale), axis=0)
    if normalize:
        collection = norm(collection, axis=(1, 2))
    if as_tensor and len(collection.shape) < 4:
        collection = tf.expand_dims(collection, axis=-1)
    else:
        collection = tf.squeeze(collection).numpy()
    return collection

def load_dataset(**kwargs):
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
    x_train = load_collection(Paths.TRAIN.glob('*.jpg'), **kwargs)
    y_train = load_collection(Paths.TRAIN.glob('*.png'), **kwargs)
    x_test = load_collection(Paths.TEST.glob('*.jpg'), **kwargs)
    y_test = load_collection(Paths.TEST.glob('*.png'), **kwargs)

    if augmentation: # shape = [4*N, H, W, D]
        x_train = flipping_augmentation(x_train, axis=(1, 2), concat_axis=0)
        y_train = flipping_augmentation(y_train, axis=(1, 2), concat_axis=0)
        x_test = flipping_augmentation(x_test, axis=(1, 2), concat_axis=0)
        y_test = flipping_augmentation(y_test, axis=(1, 2), concat_axis=0)

    return (x_train, y_train), (x_test, y_test)

def load_random(n:int=1, seed:Any=None, **kwargs):
    jpg_files = list(Paths.DATA.glob('**/*.jpg'))
    chosens = np.random.default_rng(seed).choice(jpg_files, size=n, replace=False)
    images = load_collection(chosens, **kwargs)
    labels = load_collection([jpg_file.with_suffix('.png') for jpg_file in chosens], **kwargs)
    return (images, labels)

def norm(x, vmin:float=0, vmax:float=1, axis=None):
    '''
    Normalizar valores de um array "x" para determinados limites (vmin, vmax).

    Args:
        x: Array n-dimensional com os valores que serão normalizados.
        vmin (opcional): Limite inferior (default: 0).
        vmax (opcional): Limite superior (default: 1).
    
    Return:
        y: Tensor normalizado.
    '''
    return vmin + (x - tf.reduce_min(x, axis=axis)) * (vmax - vmin)/(tf.reduce_max(x, axis=axis) - tf.reduce_min(x, axis=axis))

def split_validation_data(p:float, shuffle:bool=True, seed:Any=None, verbose:bool=True):
    '''
    Separar dados de validação: No diretório config.DATASET, os arquivos

    Args:
        p: Fração das imagens que serão usadas para validação, 0 <= p <= 1.
        shuffle (opcional): Se True, os arquivos serão escolhidos aleatoriamente.
        seed (opcional): Seed usada para embaralhar os arquivos (obs: esta informação só será utilizada caso shuffle=True).
        verbose (opcional): Se True, informações sobre a separação dos dados serão exibidas ao final do procedimento.
    '''
    all_jpg_paths = list(Paths.DATA.glob('**\*.jpg'))
    n_files = len(files)
    split_threshold = int(p*n_files)

    if shuffle: 
        np.random.default_rng(seed).shuffle(files) # embaralhe as amostras, se shuffle for verdadeiro

    for i, jpg_file in enumerate(all_jpg_paths): # enumere as informações das amostras
        new_dir = Paths.TEST if i < split_threshold else Paths.TRAIN
        png_file = jpg_file.with_suffix('.png')

        jpg_file.rename(new_dir/jpg_file.name)
        png_file.rename(new_dir/png_file.name)

    if verbose:
        tr = n_files - split_threshold
        print('\n'.join([
            f'Foram encontradas {n_files} amostras, totalizando {2*n_files} arquivos.'
            f'Dados para treinamento: {tr} amostras ({tr/n_files*100:.2f}%).'
            f'Dados para validação: {split_threshold} amostras ({split_threshold/n_files*100:.2f}%).'
        ]))
