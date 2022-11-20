from os import path, listdir
import numpy as np
from pandas import read_csv
from numpy.random import choice
from PIL.Image import open as image_open

PATH = path.join(*path.split(__file__)[:-1], 'dataset')

def get(filename, filtered=False, function=None):
    img = np.array(image_open(path.join(get_images_path(filtered), filename)))
    if function: img = function(img)
    return img

def get_dataset(images=False, filtered=False):
    return read_csv(path.join(PATH, 'dataset.csv'))

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