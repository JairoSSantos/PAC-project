import numpy as np
import pandas as pd
import tensorflow as tf
from skimage.io import imread, imsave
from skimage.transform import resize
from scipy.ndimage import center_of_mass
from warnings import warn
from .config import Paths, Default
from .measure import find_scale, find_slope

def _with_suffix(pattern, suffix):
    '''
    Modifica a extensão dos arquivos em `pattern`.

    Parameters
    ----------
    pattern : iterable
        Arquivos que serão mapeados.
    suffix : str
        Extenção que será adicionada aos arquivos.
    
    Returns
    -------
    iterable
        Arquivos `pattern` com a extensão `suffix`.
    '''
    return map(lambda filepath: filepath.with_suffix(suffix), pattern)

def add_processed_data(replace=False):
    '''
    Adiciona as amomstras de `Paths.processed` ao conjunto de treinamento `Paths.dataset`.

    Parameters
    ----------
    replace : bool, default=False
        Se verdadeiro, arquivos existentes poderão ser sobrescritos.
    
    Returns
    -------
    None
    '''
    for jpg_path in Paths.processd.glob('*.jpg'):
        new_jpg_path = Paths.dataset/jpg_path.name

        png_path = jpg_path.with_suffix('.png')
        new_png_path = Paths.dataset/png_path.name

        if not replace and new_jpg_path.exists():
            warn(f'Uma amostra nomeada "{jpg_path.stem}" já foi adicionada ao dataset!')
        else:
            jpg_path.rename(new_jpg_path)
            png_path.rename(new_png_path)

def check_data_integrity(directory):
    '''
    Verifica integridade dos dados no diretório `directory` 
    conferindo se para cada arquivo `.jpg` (imagem) existe um `.png` (máscara) correspondente.

    Parameters
    ----------
    directory : pathlib.PurePath
        Diretório que será verificado.
    
    Returns
    -------
    None
    '''
    jpg_files = list(directory.glob('**/*.jpg'))
    png_files = list(directory.glob('**/*.png'))
    
    print(f'Verificando integridade dos dados em {directory}')

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

def flipping_augmentation(collection):
    '''
    Aumento os dados via espelhamento das imagens. As imagens serão espelhadas nos eixos `height` e `width`.

    Parameters
    ----------
    collection: tensor-like
        Tensor contendo a coleção de imagens que serão espelhadas,
        `collection.shape`: `[n_batch, height, width, chanels]` ou `[n_batch, height, width]`.
    
    Returns
    -------
    tf.Tensor
        Coleção aumentada em 4 vezes, `shape = [4*n_batch, ...]`.
    '''
    return tf.concat((
            collection,
            collection[:, ::-1],
            collection[:, :, ::-1],
            collection[:, ::-1, ::-1]
    ), axis=0)

def load_by_area(area, **kwargs):
    '''
    Coleta as amostras do conjunto de treinamentos através da área.

    Parameters
    ----------
    area : str
        `string`, `float` ou `int` contendo o valor da área (no padrão internacional) a ser usado para procurar as amostras.
    **kwargs
        Extra arguments to `load_collection`: refer to each metric documentation for a
        list of all possible arguments.

    Returns
    -------
    tuple
        (jpg_files, png_files)
    '''
    jpg_files = list(Paths.dataset.glob(f'**/{area}.jpg'))
    png_files = map(lambda filename: filename.with_suffix('.png'), jpg_files)
    return (load_collection(jpg_files, **kwargs), 
            load_collection(png_files, **kwargs))

def load_collection(pattern, grayscale=True, as_tensor=True, norm=True):
    '''
    Carrega uma coleção de imagens.

    Parameters
    ----------
    pattern: iterable
        Iterável contendo os caminhos para as imagens.
    grayscale : bool, default=True
        Se `True` as imagens serão convertidas em tons de cinza.
    as_tensor : bool, default=True
        Se `True` as imagens serão retornadas em forma de `tf.Tensor`; se `False` retornará `np.ndarray`.
    norm: bool, default=True
        Se `True` as imagens serão normalizadas para valores entre 0 e 1, ao longo dos eixos 1 e 2 (`height` e `width`, respectivamente).
    
    Returns
    ------- 
    tensor-like
        Coleção de imagens `shape = [n_batch, height, width, chanels]` ou `shape = [n_batch, height, width]`, se `as_tensor = False`.
    '''
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

def load_all(pattern='**/*', area=False, **kwargs):
    '''
    Carrega todas as amostras do conjunto de treinamento encontradas através do `pattern` fornecido.

    Parameters
    ----------
    patter : str, default='**/*'
        Caminho das amostras relativo a `Paths.dataset`.
    area : bool, default=False
        Se `True` as áreas são retornadas.
    **kwargs
        Extra arguments to `load_collection`: refer to each metric documentation for a
        list of all possible arguments.
    
    Returns
    -------
    list
        (jpg_files, png_files), ou (jpg_files, png_files, areas) se `area = True`.
    '''
    jpg_files = list(Paths.dataset.glob(f'{pattern}.jpg'))
    png_files = map(lambda filename: filename.with_suffix('.png'), jpg_files)
    output = [
        load_collection(jpg_files, **kwargs),
        load_collection(png_files, **kwargs)
    ]
    if area: 
        output.append(list(map(lambda filename: float(filename.stem.split('_')[0]), jpg_files)))
    return output

def load_dataset(augmentation, **kwargs):
    '''
    Carrega o conjunto de dados para treinamento.

    Parameters
    ----------
    augmentation : bool
        Se `True` o conjunto de dados será aumentado utilizando `flipping_augmentation`.
    **kwargs
        Extra arguments to `load_collection`: refer to each metric documentation for a
        list of all possible arguments.
    
    Returns
    -------
    tuple
        (x_train, y_train), (x_test, y_test): Conjunto de treinamento.
    '''
    train_jpg_files = list(Paths.train.glob('*.jpg'))
    test_jpg_files = list(Paths.test.glob('*.jpg'))
    x_train = load_collection(train_jpg_files, **kwargs)
    y_train = load_collection(_with_suffix(train_jpg_files, '.png'), **kwargs)
    x_test = load_collection(test_jpg_files, **kwargs)
    y_test = load_collection(_with_suffix(test_jpg_files, '.png'), **kwargs)

    if augmentation: # shape = [4*N, H, W, D]
        x_train = flipping_augmentation(x_train)
        y_train = flipping_augmentation(y_train)
        x_test = flipping_augmentation(x_test)
        y_test = flipping_augmentation(y_test)

    return (x_train, y_train), (x_test, y_test)

def load_random(n=1, seed=None, get_area=False, **kwargs):
    '''
    Carrega amostras aleatórias do conjunto de dados de treinamento.

    Parameters
    ----------
    n : int, default=1
        Quantidade de amostras que devem ser coletadas.
    seed : Any, default=None
        Gerador de números pseodo-aleatórios.
    get_area : bool
        Se `True` a área das amostras serão retornada.
    **kwargs
        Extra arguments to `load_collection`: refer to each metric documentation for a
        list of all possible arguments.
    
    Returns
    -------
    list
        `[images, labels]`, ou `[images, labels, areas]` se `get_area = True`.
    '''
    jpg_files = list(Paths.dataset.glob('**/*.jpg'))
    chosens = np.random.default_rng(seed).choice(jpg_files, size=n, replace=False)
    images = load_collection(chosens, **kwargs)
    labels = load_collection([jpg_file.with_suffix('.png') for jpg_file in chosens], **kwargs)
    out = [images, labels]
    if get_area: out.append([float(jpg_file.stem) for jpg_file in chosens])
    return out

def split_validation_data(p, shuffle=True, seed=None, verbose=True):
    '''
    Separa dados de validação e treinamento no diretório `Paths.dataset`.

    Parameters
    ----------
    p : float
        Fração das imagens que serão usadas para validação, `0 <= p <= 1`.
    shuffle : bool, default=True
        Se `True` os arquivos serão escolhidos aleatoriamente.
    seed : Any, default=None
        Gerador de números pseodo-aleatórios (obs: esta informação só será utilizada se `shuffle = True`).
    verbose : bool, default=True
        Se `True`, informações sobre a separação dos dados serão exibidas ao final do procedimento.
    
    Returns
    -------
    None
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
    Regulariza as amostras de `Paths.raw` no padrão de treinamento, e as move para `Paths.processed`.

    Parameters
    ----------
    pattern : iterable or None, default=None
        Iterável contendo as amostras da pasta `Paths.raw` que serão regularizadas. Se `pattern = None` todas as amostras serão regularizadas.
    mode: str, list ou None, modo com o qual as imagens serão ajustadas.
        > `'crop'`: Recorta as imagens no formado padrão `Default.size` 
                    de modo com que o centro do corte corresponda ao centro de massa da máscara.
            Obs.: Este tipo de ajuste é indicado para imagens que possuem dimensões widescreen ou semelhantes (ex.: 9:20 ou 16:9), 
                ou para imagens cuja a região do pellet seja pequena.
        > `'resize'`: Redimensiona a imagem para que atenda os padrões de treinamento `Default.size`.
            Obs.: Este tipo de ajuste é indicado para imagens que já possuem uma boa qualidade, 
                porém com dimensões diferentes daquelas utilizadas nos dados de treinamento
    
    Returns
    -------
    None
    
    Exemples
    --------
    >>> regularize_raw_data(mode='crop')

    Neste exemplo, todas as amostras em `Paths.raw` serão recortadas no formato de treinamento.

    >>> regularize_raw_data(['118.032_mm2', '64.760_mm2'], mode=['crop', 'resize'])

    Já neste caso, apenas as amostras especificadas serão ajustadas, cada uma com seu respectivo método.
    '''
    if pattern is None: 
        pattern = map(lambda filepath: filepath.stem, Paths.raw.glob('*.jpg'))
    for i, sample in enumerate(pattern):
        jpg_raw_file = Paths.raw/(sample + '.jpg')
        png_raw_file = jpg_raw_file.with_suffix('.png')

        jpg_final_file = Paths.processed/(sample + '.jpg')
        png_final_file = jpg_final_file.with_suffix('.png')

        img = imread(jpg_raw_file)
        msk = imread(png_raw_file)

        m = mode[i] if type(mode) is not str else mode

        if m == 'crop':
            y, x = center_of_mass(msk)
            x, y = int(x), int(y)

            dw = Default.image_width//2
            dh = Default.image_height//2

            imsave(jpg_final_file, imread(jpg_raw_file)[y-dh:y+dh, x-dw:x+dw])
            imsave(png_final_file, imread(png_raw_file)[y-dh:y+dh, x-dw:x+dw])
        
        elif m == 'resize':
            w, h = img.shape[:2]
            if w != h:
                d = abs(w - h)
                if w > h: img, msk = img[d:], msk[d:]
                elif h > w: img, msk = img[:, d:], msk[:, d:]

            imsave(jpg_final_file, resize(img, Default.image_size))
            imsave(png_final_file, resize(msk, Default.image_size))

def get_info():
    '''
    Coleta informações sobre as amostras do conjunto de treinamento.

    Returns
    -------
    pd.DataFrame
    '''
    return pd.read_csv(Paths.dataset/'info.csv')

def update_info():
    '''
    Atualizar tabela de informações sobre o dataset.
    '''
    dataframe = []
    for jpg_file in Paths.dataset.glob('**/*.jpg'):
        img = imread(jpg_file, as_gray= True)
        mask = imread(jpg_file.with_suffix('.png'), as_gray=True)
        scale, d_scale = find_scale(img)
        slope, d_slope = find_slope(img)
        dataframe.append({
            'area': float(jpg_file.stem.split('_')[0]),
            'group': jpg_file.parent.stem, 
            'scale': scale,
            'delta_scale': d_scale,
            'slope': slope,
            'delta_slope': d_slope,
            'area_pixel': np.sum((mask - mask.min())/(mask.max() - mask.min()))
        })
    pd.DataFrame(dataframe).sort_values('area').to_csv(Paths.dataset/'info.csv', index=False)
