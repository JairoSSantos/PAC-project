from os import path, listdir
import numpy as np
import pandas as pd
from numpy.random import choice
from PIL import Image

PATH = path.join(*path.split(__file__)[:-1], 'dataset')

def get(filename, filtered=False):
    return np.array(Image.open(path.join(get_images_path(filtered), filename)))

def get_datainfo(*args, **kwargs):
    return pd.read_csv(path.join(PATH, 'dataset.csv'), *args, **kwargs)

def get_images_path(filtered):
    return path.join(PATH, 'filtered' if filtered else 'images')

def by_id(index, name=False):
    filename = f'{index}.jpg'
    if name:
        return get(filename), filename
    else:
        return get(f'{index}.jpg')

def random_images(k=1, names=False, filtered=False):
    fnames = choice(listdir(get_images_path(filtered)), k, replace=False)
    images = tuple(map(get, fnames))
    if names: 
        return zip(images, fnames)
    else: 
        return images
