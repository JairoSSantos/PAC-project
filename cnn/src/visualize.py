from skimage.color import label2rgb
import matplotlib.pyplot as plt

def plot_image(image, **kwargs):
    if len(image.shape) == 4: image = image[0, :, :, 0]
    plt.imshow(image, **kwargs)
    plt.axis('off')

def plot_label(image, label, **kwargs):
    return plot_image(rgb2label(label, image, bg_label=0), **kwargs)