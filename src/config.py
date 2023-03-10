from pathlib import Path
from warnings import warn

def add_dir_id(path, verbose=True):
    file_id = 0
    while path.with_name(path.name + str(file_id)).exists():
        file_id += 1
    new_path = path.with_name(path.name + str(file_id))
    if verbose:
        warn(f'Caminho alterado de {str(path)} para {str(new_path)} devido a choque com diretórios existentes.')
    return new_path

class Default:
    image_width = 256
    image_height = 256
    image_size = (image_width, image_height)

class Paths:
    data = Path('data/')
    models = Path('models/')
    dataset = data/'dataset'
    train = dataset/'train'
    test = dataset/'test'
    raw = data/'raw'
    processed = data/'processed'