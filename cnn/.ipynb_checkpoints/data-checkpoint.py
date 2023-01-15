import os
import numpy as np
from pandas import read_csv
from numpy.random import choice
from PIL.Image import open as open_image
from skimage.color import rgb2gray

PATH = os.path.join(*os.path.split(__file__)[:-1], 'dataset')

def read_image(area_value, root='images', gray=True):
    filename = '.'.join([str(area_value), 'jpg' if root == 'images' else 'tif'])
    img = np.array(open_image(os.path.join(PATH, root, filename)))
    if gray and len(img.shape) > 2: img = rgb2gray(img)
    return img

def get_info():
    return read_csv(os.path.join(PATH, 'info.csv'))

def get_files(root):
    return map(lambda fname: path.join(PATH, 'images', fname))

def by_id(index, filename=False):
    name = f'{index}.jpg'
    img = get(name)
    return img, name if filename else img

def random_images(k=1, names=False):
    fnames = choice(listdir(get_images_path()), k, replace=False)
    images = tuple(map(get, fnames))
    return zip(images, fnames) if names else images

def area2image(value):
    return get('.'.join([str(value), 'jpg']), 'images')

def area2label(value):
    return get('.'.join([str(value), 'tif']), 'labels')

def get_dataset():
    info = get_info()
    x_train = info[info.train].area.map(area2image).map(get).to_numpy()[:, :, :, np.newaxis]
    y_train = info[info.train].area.map(area2label).map(get).to_numpy()[:, :, :, np.newaxis]
    x_test = info[~info.train].area.map(area2image).map(get).to_numpy()[:, :, :, np.newaxis]
    y_test = info[~info.train].area.map(area2label).map(get).to_numpy()[:, :, :, np.newaxis]
    