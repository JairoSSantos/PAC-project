import tensorflow as tf
from tensorflow.keras import Input, Model, layers
from tensorflow.keras.callbacks import Callback
from IPython.display import clear_output
import matplotlib.pyplot as plt
from skimage.color import label2rgb
from random import randint
import os

def conv_block(x, filters):
    for lay in (layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu'),
                layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu')):
        x = lay(x)
    return x

def encoder(x, filters):
    x = conv_block(x, filters)
    return layers.MaxPool2D((2, 2))(x), x

def decoder(x, jumper, filters):
    x = layers.Conv2DTranspose(filters, (2, 2), strides=2, padding='same')(x)
    x = layers.Concatenate()([jumper, x])
    x = conv_block(x, filters)
    return x

def build_unet(input_shape:tuple, filters:tuple, name:str, activation:str='sigmoid'):
    inputs = x = layers.Input(input_shape)
    jumpers = []
    for f in filters[:-1]:
        x, jumper = encoder(x, f)
        jumpers.append(jumper)
    
    x = conv_block(x, filters[-1])
    
    for f, jumper in zip(filters[::-1][1:], jumpers[::-1]):
        x = decoder(x, jumper, f)
    
    outputs = layers.Conv2D(1, 1, padding='same', activation=activation)(x)
    return Model(inputs=inputs, outputs=outputs, name=name)

class UnetTrainingPlot(Callback):
    def __init__(self, unet, x_test, y_test, period:int=3):
        super(Callback, self).__init__()

        self.unet = unet
        self.x_test = x_test
        self.y_test = y_test
        self.period = period

        self.area_total = tf.multiply(*self.y_test.shape[1:-1]).numpy()
        self.y_rel_area = tf.reduce_sum(self.y_test, (1, 2))/self.area_total

        ymin, ymax = tf.reduce_min(self.y_rel_area), tf.reduce_max(self.y_rel_area)
        dy = 0.2*(ymax - ymin)
        self.t_min, self.t_max = ymin - dy, ymax + dy
        self.t = tf.linspace(self.t_min, self.t_max, 50)

        self.logs = {}
    
    def on_epoch_end(self, epoch, logs={}):
        for k, v in logs.items():
            try: self.logs[k].append(v)
            except KeyError: self.logs[k] = [v]
        
        if not epoch % self.period:
            pred = tf.where(self.unet.predict(self.x_test, verbose=0) > 0.5, 1, 0)
            pred_rel_area = tf.reduce_sum(pred, axis=(1, 2))/self.area_total

            clear_output(wait=True)
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 4))

            for k, v in self.logs:
                ax1.plot(v, label=k)
            ax1.legend()
            ax1.set_ylim(bottom=0)

            i = randint(0, self.x_test.shape[0]-1)
            ax2.imshow(label2rgb(pred[i, :, :, 0], self.x_test[i, :, :, 0], bg_label=0))

            ax3.plot(self.pred_rel_area, rel_area, 'ro', alpha=0.5)
            ax3.plot(self.t, self.t, 'k--')
            ax3.set_ylim(self.t_min(), self.t_max())
            ax3.set_aspect('equal')
            plt.show()