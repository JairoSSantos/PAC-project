import os
import numpy as np
import pandas as pd
from numpy.random import choice
from PIL import Image

PATH = 'cnn\dataset'
IMAGES_PATH = os.path.join(PATH, 'images')
DS = pd.read_csv(os.path.join(PATH, 'dataset.csv'))

def get(filename):
    return np.array(Image.open(os.path.join(IMAGES_PATH, filename)))

def random_images(k=1, names=False):
    fnames = choice(os.listdir(IMAGES_PATH), k)
    images = tuple(map(get, fnames))
    if names: 
        return images, fnames
    else: 
        return images