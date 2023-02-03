import os
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model
from tensorflow.keras import Input, Model, layers, callbacks, losses
from IPython.display import clear_output, HTML, display
from skimage.color import label2rgb
from warnings import warn
from typing import Any

SAVE_PATH = os.path.join(*os.path.split(__file__)[:-1], 'saves')

def _check_unet_name(name:str):
    '''
    Verifica se já existe uma U-Net salva com este nome nos modelos salvos.
    Se existir um modelo salvo com este nome, um numero inteiro será adicionado após este (ex: 'U-Net', 'U-Net0', 'U-Net1', ...) e um aviso será emitido.

    Args:
        name: Nome da U-Net.
    
    Return:
        Se não houver modelo salvo com este nome, name será retornado. Porém, se houver, um novo nome será retornado.
    '''
    saved_unets = os.listdir(SAVE_PATH)
    changed = False
    while name in saved_unets:
        if name[-1].isnumeric():
            name = name[:-1] + str(int(name[-1]) + 1)
        else: name +='0'
        changed = True
    if changed: warn(f'Nome alterado para {name}, pois uma U-Net com este nome já foi salva.')
    return name

@tf.function
def amape(y_true, y_pred):
    '''
    Erro percentual médio adaptado para comparar as áreas (em píxel) entre a saída do modelo `y_pred` e o valor verdadeiro `y_true`.

    Args:
        y_true: Tensor quadridimensional contendo as máscaras verdadeiras.
                Neste tensor, os valores devem ser restritos a 0 (fora da máscara) e 1 (dentro da máscara).
                Se `y_true.shape[-1] > 1`, será considerado apenas `y_true[:, :, :, 0]`.
        y_pred: Tensor quadridimentional contendo as saídas da rede neural (0 <= `y_pred` <= 1).
    '''
    area_true = tf.reduce_sum(y_true[:, :, :, 0], axis=(-1, -2))
    area_pred = tf.reduce_sum(y_pred, axis=(-1, -2, -3))
    return tf.reduce_mean(tf.abs(area_true - area_pred)/area_true * 10)

def conv_block(x:Any, filters:int):
    '''
    Bloco de convolução (convolução -> batch normalization -> ReLu -> convolução -> batch normalization -> ReLu).

    Args:
        x: Input, camada anterior.
        filters: Número de filtros de saída da convolução.
    
    Return:
        x: Ativação da última camada de convolução.
    '''
    for lay in (layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu'),
                layers.Conv2D(filters, 3, padding='same'),
                layers.BatchNormalization(),
                layers.Activation('relu')):
        x = lay(x)
    return x

def encoder(x:Any, filters:int):
    '''
    Camada de codificação da U-Net.

    Args:
        x: Input, camada anterior.
        filters: Número de filtros de saída do block de convolução.
    
    Return:
        x: Camada de codificação (bloco de convolução + maxpooling).
        jumper: Ativação da última camada do bloco de convolução, utilizada para conectar com a camada de decodificação.
    '''
    x = conv_block(x, filters)
    return layers.MaxPool2D((2, 2))(x), x

def decoder(x:Any, jumper:Any, filters:int):
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

def build_unet(input_shape:tuple, filters:tuple, name:str='unet', activation:str='sigmoid'):
    '''
    Construir U-Net.

    Args:
        input_shape: Formato de entrada da rede.
        filters: Número de filtros para cada etapa de codificação (a mesma quantidade será utilizada na etapa de decodificação).
        name (opcional): Nome que será atribuído ao modelo.
        activation (opcional): Função de ativação da última camada da rede (default: 'sigmoid').
    
    Return:
        unet: U-Net, rede neural convolucional para segmentação semantica.
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

@tf.function
def weighted_binary_crossentropy(y_true, weight, y_pred):
    return -tf.reduce_mean(weight*tf.where(y_true == 1, tf.math.log(y_pred), tf.math.log(1 - y_pred)), axis=(-1, -2, -3))

class UNet:
    '''
    Modelo de U-Net para segmentação de imagens.

    Args:
        name: Nome do modelo, será usado para salvá-lo ou importá-lo, se já houver sido salvo.
        dataset: Tupla ou lista contendo as imagens de treino e validação no formato [(x_train, y_train), (x_test, y_test)].
    
    Attr:
        x_train, y_train: Dados de treinamento.
        x_test, y_test: Dados de validação.
        *Qualquer outro atributo ou método pretencente à classe tf.keras.Model.
    '''
    def __init__(self, name:str, dataset:tuple):
        self.name = name
        (self.x_train, self.y_train), (self.x_test, self.y_test) = dataset
        self._path = os.path.join(SAVE_PATH, self.name)
        self._logs_path = os.path.join(self._path, 'logs.csv')
    
    def __getattr__(self, name):
        '''
        Pegar atributo pertencente ao modelo (tf.keras .Model).
        '''
        return getattr(self.model, name)

    def _on_epoch_end(self, epoch:int, logs:dict):
        '''
        Função a ser chamada durante o treinamento ao final de cada época.
        '''
        if not epoch%self._period: self.plot(epoch)
        
    def _on_train_begin(self, logs:dict):
        '''
        Função a ser chamada ao início do treinamento.
        '''
        try: os.mkdir(os.path.join(self._path))
        except FileExistsError: pass
        self.save()
    
    def _on_train_end(self, logs:dict):
        '''
        Função a ser chamada no final do treinamento.
        '''
        self.plot()
    
    def build(self, filters:tuple, activation:str='sigmoid'):
        '''
        Construir U-Net.

        Args:
            filters: Número de filtros para cada etapa de codificação (a mesma quantidade será utilizada na etapa de decodificação).
            activation (opcional): Função de ativação da última camada da rede (default: 'sigmoid').
        
        Return:
            unet: Objeto da classe aimodel.UNet.
        
        Warnings:
            Se name atribuido à U-Net já estiver sendo usado para salvar outro modelo, a variável será alterada e um aviso será emitido informando a alteração.
        '''
        self.name = _check_unet_name(self.name) # verificar se o nome já está em uso
        self._path = os.path.join(SAVE_PATH, self.name)
        self._logs_path = os.path.join(self._path, 'logs.csv')

        self.model = build_unet(input_shape=self.x_train.shape[1:], filters=filters, name=self.name, activation=activation)
        return self
    
    def fit(self, epochs:int, batch_size:int, period:int=5):
        '''
        Treinamento da rede.

        Args:
            epochs: Número de épocas de treimento.
            batch_size: Número de imagens por pacote.
            period (opcional): Período de atualização dos gráficos sobre o treinamento do modelo.
        '''
        try: initial_epoch = pd.read_csv(self._logs_path).epoch.max()
        except FileNotFoundError: initial_epoch = 0
        self._period = period
        return self.model.fit(
            self.x_train,
            self.y_train,
            validation_data= (self.x_test, self.y_test),
            batch_size= batch_size,
            epochs= epochs,
            initial_epoch= initial_epoch,
            verbose=1,
            callbacks= (
                callbacks.CSVLogger(self._logs_path, append=True),
                callbacks.ModelCheckpoint(os.path.join(self._path, 'weights.{epoch:04d}.h5'), verbose=0, save_weights_only=True),
                callbacks.ModelCheckpoint(os.path.join(self._path, f'{self.name}.h5'), verbose=0, save_weights_only=False),
                callbacks.LambdaCallback(
                    on_epoch_end=self._on_epoch_end,
                    on_train_begin=self._on_train_begin,
                    on_train_end=self._on_train_end
                )
            )
        )

    def load(self, epoch=None):
        '''
        Carregar U-Net.
        
        Return:
            U-Net, já compilada.
        '''
        self.model = load_model(os.path.join(self._path, f'weights.{epoch}.h5' if epoch != None else f'{self.name}.h5'))
        return self
    
    def plot(self, epoch=None):
        '''
        Plotar métricas.
        '''
        clear_output(wait=True)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 4))

        logs = pd.read_csv(self._logs_path)
        x_max = len(logs)
        ax1.hlines(logs.val_loss.min(), 0, x_max, linestyles='dashdot', color='k')
        ax1.plot(logs.loss, label='loss')
        ax1.plot(logs.val_loss, label='val_loss')
        ax1.set_xlim(0, x_max)
        ax1.set_xlabel('Época')
        ax1.set_ylabel('Loss')
        ax1.semilogy()
        ax1.legend()

        if epoch != None: 
            ax2.set_title('Época: %s'%epoch)

        t_min, t_max = float('inf'), -float('inf') # -infinito < qualquer valor < infinito
        for tag in ('train', 'test'):
            x = getattr(self, 'x_%s'%tag)
            y = getattr(self, 'y_%s'%tag) # y.shape = [N, H, W, D]
            pred = self.model.predict(x, verbose=0)
            true_rel_area = tf.reduce_mean(y, axis=(1, 2))[:, 0] # tf.reduce_mean(y, axis=(1, 2)).shape = [N, D]
            pred_rel_area = tf.reduce_mean(pred, axis=(1, 2))[:, 0]
            ax2.plot(true_rel_area, pred_rel_area, 'o', 
                    alpha=0.5, label='{} (AMAPE = {}%)'.format(tag, np.round(logs[('val_' if tag == 'test' else '') + 'amape'].values[-1], 5)))
            t_min = min(t_min, tf.reduce_min(true_rel_area))
            t_max = max(t_max, tf.reduce_max(true_rel_area))
        
        dt = (t_max - t_min)*0.2
        t = np.linspace(t_min - dt, t_max + dt, 10)
        ax2.plot(t, t, 'k--', label=r'$x=y$')
        ax2.set_xlim(t_min - dt, t_max + dt)
        ax2.set_ylim(t_min - dt, t_max + dt)
        ax2.set_xlabel('Método convencional (mm$^2$)')
        ax2.set_ylabel('U-Net (mm$^2$)')
        ax2.set_aspect('equal')
        ax2.legend()

        x = self.x_test[np.random.randint(len(self.x_test))][tf.newaxis].numpy()
        pred = self.model.predict(x, verbose=0)[0, :, :, 0]
        ax3.imshow(label2rgb(pred > 0.5, x[0, :, :, 0], bg_label=0))
        ax3.contour(pred, cmap='plasma')
        ax3.grid(False)
        ax3.axis('off')

        plt.show()

        display(HTML(logs[
            (logs.val_loss == logs.val_loss.min())|
            (logs.val_amape == logs.val_amape.min())
        ].to_html()))
        
    def save(self):
        '''
        Salvar modelo.
        '''
        return self.model.save(os.path.join(self._path, f'{self.name}.h5'))

class CustomLoss(losses.Loss):
    def __init__(self, mrae:bool=False):
        super().__init__()
        self._mrae = mrae
    
    def call(self, y_true, y_pred):
        L = weighted_binary_crossentropy(*tf.split(y_true, num_or_size_splits=2, axis=-1), y_pred)
        if self._mrae: L /= tf.reduce_mean(y_pred, axis=(-1, -2, -3))
        return L
    
    def get_config(self):
        config = super(CustomLoss, self).get_config()
        config.update({'mrae': self._mrae})
        return config