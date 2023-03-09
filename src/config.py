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

class Paths:
    DATA = Path('data/dataset')
    RAW = Path('data/raw')
    TRAIN = DATA/'train'
    TEST = DATA/'test'
    MODELS = Path('models/')