import numpy as np
import matplotlib.pyplot as plt
from skimage.color import label2rgb

def plot_image(image, **kwargs):
    plt.imshow(np.squeeze(image), **kwargs)
    plt.axis('off')

def plot_label(image, label, **kwargs):
    return plot_image(label2rgb(np.squeeze(label), np.squeeze(image), bg_label=0), **kwargs)

class Plot:
    def __init__(self, log_name):

class TrainingBoard:
    def __init__(self, objects):
        pass