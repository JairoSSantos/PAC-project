from os import path, listdir
import numpy as np
from pandas import read_csv
from numpy.random import choice
from PIL.Image import open as image_open

PATH = path.join(*path.split(__file__)[:-1], 'dataset')

def get(filename, gabor=False, apply=None):
    img = np.array(image_open(path.join(get_images_path(gabor), filename)))
    if apply: img = apply(img)
    return img

def get_dataset():
    return read_csv(path.join(PATH, 'dataset.csv'))

def get_images_path(gabor):
    return path.join(PATH, 'gabor' if gabor else 'images')

def by_id(index, filename=False):
    name = f'{index}.jpg'
    img = get(name)
    return img, name if filename else img

def random_images(k=1, names=False, gabor=False):
    fnames = choice(listdir(get_images_path(gabor)), k, replace=False)
    images = tuple(map(get, fnames))
    return zip(images, fnames) if names else images