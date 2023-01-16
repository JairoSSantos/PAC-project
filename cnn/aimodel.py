import os
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras import Input, Model, layers
from tensorflow.keras.metrics import mean_absolute_percentage_error as mape
from tensorflow.keras.callbacks import Callback
from IPython.display import clear_output
from skimage.color import label2rgb

def conv_block(x, filters:int):
    '''
    Bloco de convolução (convolução -> batch normalization -> ReLu -> convolução -> batch normalization -> ReLu).

    Args:
        x: Input, camada anterior.
        filters: Número de filtros de saída da convolução.
    '''
    for lay in (layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu'),
                layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu')):
        x = lay(x)
    return x

def encoder(x, filters:int):
    '''
    Camada de codificação da U-Net.

    Args:
        x: Input, camada anterior.
        filters: Número de filtros de saída do block de convolução.
    
    Return:
        x: Camada de codificação (bloco de convolução + maxpooling).
        jumper: Saída do bloco de convolução, utilizada para conectar com a camada de decodificação.
    '''
    x = conv_block(x, filters)
    return layers.MaxPool2D((2, 2))(x), x

def decoder(x, jumper, filters:int):
    '''
    Camada de decodificação da U-Net (deconvolução + jumper -> bloco de convolução).

    Args:
        x: Input, camada anterior.
        jumper: Conexão com camada de "descida".
        filters: Número de filtros de saída do block de convolução.
    
    Return:
        x: Camada de decodificação.
    '''
    x = layers.Conv2DTranspose(filters, (2, 2), strides=2, padding='same')(x)
    x = layers.Concatenate()([jumper, x])
    x = conv_block(x, filters)
    return x

def build_unet(input_shape:tuple, filters:tuple, name:str, activation:str='sigmoid'):
    '''
    Construir U-Net.

    Args:
        input_shape: Formato dos dados de entrada (3 valores inteiros: [altura, largura, canais]).
        filters: Número de filtros para cada etapa de codificação (a mesma quantidade será utilizada na etapa de decodificação).
        name: Nome da rede, será utilizado para salvar o modelo.
        activation (opcional): Função de ativação da última camada da rede (default: 'sigmoid').
    '''
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
    '''
    Callback para plotar a evolução da rede neural no treinamento.
    '''
    def __init__(self, unet, dataset, period:int=3):
        super(Callback, self).__init__()

        self.unet = unet
        (self.x_train, self.y_train), (self.x_test, self.y_test) = dataset
        self.period = period

        self.area_total = np.multiply(*self.y_test.shape[1:-1])
        self.y_rel_area_train = self.y_train.sum(axis=(1, 2))/self.area_total
        self.y_rel_area_test = self.y_test.sum(axis=(1, 2))/self.area_total

        ymin, ymax = np.concatenate((self.y_rel_area_test, self.y_rel_area_test)).min()
        dy = 0.2*(ymax - ymin)
        self.t_min, self.t_max = ymin - dy, ymax + dy
        self.t = np.linspace(self.t_min, self.t_max, 50)

        self.logs = {}
    
    def on_epoch_end(self, epoch, logs={}):
        for k, v in logs.items():
            try: self.logs[k].append(v)
            except KeyError: self.logs[k] = [v]
        
        if epoch % self.period == 0:
            pred_train = (self.unet.predict(self.x_train, verbose=0) > 0.5).astype(int)
            pred_train_rel_area = pred.sum(axis=(1, 2))/self.area_total
            pred_test = (self.unet.predict(self.x_test, verbose=0) > 0.5).astype(int)
            pred_test_rel_area = pred.sum(axis=(1, 2))/self.area_total

            clear_output(wait=True)
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 4))

            for k, v in self.logs.items():
                ax1.plot(v, label=k)
            ax1.legend()
            ax1.set_ylim(bottom=0)

            i = np.random.randint(0, self.x_test.shape[0]-1)
            ax2.imshow(label2rgb(pred_test[i, :, :, 0], self.x_test[i, :, :, 0], bg_label=0))

            ax3.plot(self.y_rel_area_train, pred_train_rel_area, 'bo', alpha=0.5, 
                label=r'train $\Delta$% = {.:2f}'.format(np.round(mape(self.y_rel_area_train, pred_train_rel_area), 2)))
            ax3.plot(self.y_rel_area_test, pred_test_rel_area, 'ro', alpha=0.5,
                label=r'val $\Delta$% = {.:2f}'.format(np.round(mape(self.y_rel_area_test, pred_test_rel_area), 2)))
            ax3.plot(self.t, self.t, 'k--')
            ax3.set_ylim(self.t_min(), self.t_max())
            ax3.set_aspect('equal')
            plt.show()