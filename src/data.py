import numpy as np
import pandas as pd
import tensorflow as tf
from skimage.io import imread, imsave
from skimage.transform import resize
from scipy.ndimage import center_of_mass
from typing import Any, Callable
from warnings import warn
from .config import Paths, Default

def add_processed_data(replace=False):
    '''
    Adicionar as amomstras de `processed/` para `dataset/`.
    '''
    for jpg_path in Paths.processd.glob('*.jpg'):
        new_jpg_path = Paths.dataset/jpg_path.name

        png_file = jpg_path.with_suffix('.png')
        new_png_path = Paths.dataset/png_path.name

        if not replace and new_jpg_path.exists():
            warn(f'Uma amostra nomeada {jpg_path.stem} já foi adicionada ao dataset!')
        else:
            jpg_path.rename(new_jpg_path)
            png_path.rename(new_png_path)

def check_data_integrity(directory):
    '''
    Verificar integridade dos dados em um subdiretório de `data/`
    '''
    path = getattr(Paths, directory)
    jpg_files = list(path.glob('**/*.jpg'))
    png_files = list(path.glob('**/*.png'))
    
    print(f'Verificando integridade dos dados em {path}')

    png_missing = []
    for jpg_file in jpg_files:
        png_file = jpg_file.with_suffix('.png')
        if png_file not in png_files:
            png_missing.append(str(png_file))

    jpg_missing = []
    for png_file in png_files:
        jpg_file = png_file.with_suffix('.jpg')
        if jpg_file not in jpg_files:
            jpg_missing.append(str(jpg_file))

    issues = False
    if len(png_missing) > 0:
        issues = True
        print(f'- Máscaras não encontradas:', end='\n\t')
        print('\n\t'.join(png_missing))
    if len(jpg_missing) > 0:
        issues = True
        print(f'- Imagens não encontradas:', end='\n\t')
        print('\n\t'.join(jpg_missing))
    if not issues:
        print('- Não foram encontradas incosistências neste diretório')

def flipping_augmentation(collection, axis=(1, 2), concat_axis=0):
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

def load_by_area(area, **kwargs):
    return (
        load_collection(Paths.dataset.glob(f'**/{area}.jpg'), **kwargs), 
        load_collection(Paths.dataset.glob(f'**/{area}.png'), **kwargs)
    )

def load_collection(pattern, grayscale=True, as_tensor=True, norm=True):
    collection = tf.stack(list(map(lambda path: imread(path, as_gray=grayscale), pattern)))
    
    if not as_tensor:
        collection = np.squeeze(collection) #.numpy()
    elif len(collection.shape) < 4:
        collection = tf.expand_dims(collection, axis=-1)
    
    if norm:
        cmin = np.min(collection, axis=(1, 2))[:, np.newaxis, np.newaxis]
        cmax = np.max(collection, axis=(1, 2))[:, np.newaxis, np.newaxis]
        collection = (collection - cmin)/(cmax - cmin)

    return collection

def load_all(glob='**/*', *args, **kwargs):
    '''
    Carregar todas as amostras encontradas através do `glob` fornecido.
    '''
    jpg_files = list(Paths.dataset.glob(f'{glob}.jpg'))
    png_files = map(lambda filename: filename.with_suffix('.png'), jpg_files)
    return (
        load_collection(jpg_files, *args, **kwargs),
        load_collection(png_files, *args, **kwargs)
    )

def load_dataset(augmentation, **kwargs):
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
    train_jpg_files = list(Paths.train.glob('*.jpg'))
    test_jpg_files = list(Paths.test.glob('*.jpg'))
    x_train = load_collection(train_jpg_files, **kwargs)
    y_train = load_collection((filepath.with_suffix('.png') for filepath in train_jpg_files), **kwargs)
    x_test = load_collection(test_jpg_files, **kwargs)
    y_test = load_collection((filepath.with_suffix('.png') for filepath in test_jpg_files), **kwargs)

    if augmentation: # shape = [4*N, H, W, D]
        x_train = flipping_augmentation(x_train, axis=(1, 2), concat_axis=0)
        y_train = flipping_augmentation(y_train, axis=(1, 2), concat_axis=0)
        x_test = flipping_augmentation(x_test, axis=(1, 2), concat_axis=0)
        y_test = flipping_augmentation(y_test, axis=(1, 2), concat_axis=0)

    return (x_train, y_train), (x_test, y_test)

def load_random(n:int=1, seed:Any=None, get_area:bool=False, **kwargs):
    jpg_files = list(Paths.dataset.glob('**/*.jpg'))
    chosens = np.random.default_rng(seed).choice(jpg_files, size=n, replace=False)
    images = load_collection(chosens, **kwargs)
    labels = load_collection([jpg_file.with_suffix('.png') for jpg_file in chosens], **kwargs)
    out = [images, labels]
    if get_area: out.append([float(jpg_file.stem) for jpg_file in chosens])
    return out

def split_validation_data(p:float, shuffle:bool=True, seed:Any=None, verbose:bool=True):
    '''
    Separar dados de validação: No diretório config.DATASET, os arquivos

    Args:
        p: Fração das imagens que serão usadas para validação, 0 <= p <= 1.
        shuffle (opcional): Se True, os arquivos serão escolhidos aleatoriamente.
        seed (opcional): Seed usada para embaralhar os arquivos (obs: esta informação só será utilizada caso shuffle=True).
        verbose (opcional): Se True, informações sobre a separação dos dados serão exibidas ao final do procedimento.
    '''
    all_jpg_files = list(Paths.dataset.glob('**/*.jpg'))
    n_files = len(all_jpg_files)
    split_threshold = int(p*n_files)

    if shuffle: 
        np.random.default_rng(seed).shuffle(all_jpg_files) # embaralhe as amostras, se shuffle for verdadeiro

    for i, jpg_file in enumerate(all_jpg_files): # enumere as informações das amostras
        new_dir = Paths.test if i < split_threshold else Paths.train
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

def regularize_raw_data(pattern=None, mode='crop'):
    '''
    Regularizar imagens para o padrão de treinamento.

    Args:
        pattern: Lista das amostras que serão regularizadas. Ex.: ['118.032_mm2', '64.760_mm2', ...]
        mode: Modo com o qual as imagens raw serão ajustadas.
            |-> 'crop': Recorta as imagens no formado padrão (256, 256) de modo com que o centro do corte corresponda ao centro de massa da máscara.
                * Este tipo de ajuste é indicado para imagens que possuem dimensões widescreen ou semelhantes (ex.: 9:20 ou 16:9), 
                  ou para imagens cuja a região do pellet seja pequena.

            - 'resize': Redimensiona a imagem para que atenda os padrões de treinamento.
                * Este tipo de ajuste é indicado para imagens que já possuem uma boa qualidade, 
                  porém com dimensões diferentes daquelas utilizadas nos dados de treinamento
    '''
    if pattern is None: 
        pattern = map(lambda filepath: filepath.stem, Paths.raw.glob('*.jpg'))
    for sample in pattern:
        jpg_raw_file = Paths.raw/(sample + '.jpg')
        png_raw_file = jpg_raw_file.with_suffix('.png')

        jpg_final_file = Paths.processed/(sample + '.jpg')
        png_final_file = jpg_final_file.with_suffix('.png')

        img = imread(jpg_raw_file)
        msk = imread(png_raw_file)

        if mode == 'crop':
            y, x = center_of_mass(msk)
            x, y = int(x), int(y)

            dw = Default.image_width//2
            dh = Default.image_height//2

            imsave(jpg_final_file, imread(jpg_raw_file)[y-dh:y+dh, x-dw:x+dw])
            imsave(png_final_file, imread(png_raw_file)[y-dh:y+dh, x-dw:x+dw])
        
        elif mode == 'resize':
            w, h = img.shape[:2]
            if w != h:
                d = abs(w - h)
                if w > h: img, msk = img[d:], msk[d:]
                elif h > w: img, msk = img[:, d:], msk[:, d:]

            imsave(jpg_final_file, resize(img, Default.image_size))
            imsave(png_final_file, resize(msk, Default.image_size))

def get_info():
    '''
    Pegar informações sobre as amostras do dataset.
    '''
    return pd.read_csv(Paths.dataset/'info.csv')

def update_info():
    '''
    Atualizar tabela de informações sobre o dataset.
    '''
    pd.DataFrame(
        [],
        columns=['area', 'train', 'freq', 'slope', 'label_pixel_area']
    ).sort_values('area').to_csv(os.path.join(config.DATASET, 'info.csv'), index=False)