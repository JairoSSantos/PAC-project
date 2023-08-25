import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model
from tensorflow.keras import Input, Model, layers, callbacks
from .config import Paths, add_dir_id
from .visualize import TrainingBoard

def conv_block(x, filters:int):
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

def encoder(x, filters:int):
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
    def __init__(self, name, dataset=None):
        self.name = name
        if dataset is None: dataset = [[None]*2]*2
        (self.x_train, self.y_train), (self.x_test, self.y_test) = dataset
        self._dir = Paths.models/self.name
        self._logs_path = self._dir/'logs.csv'
    
    def __getattr__(self, name):
        '''
        Pegar atributo pertencente ao modelo (tf.keras.Model).
        '''
        return getattr(self.model, name)
    
    def _check_dataset(self):
        if None in (self.x_train, self.y_train, self.x_test, self.y_test):
            raise Exception('O dataset não está definido, utilize set_dataset para defini-lo.')
    
    def build(self, filters:tuple, activation:str='sigmoid'):
        '''
        Construir U-Net.

        Args:
            filters: Número de filtros para cada etapa de codificação (a mesma quantidade será utilizada na etapa de decodificação).
            activation (opcional): Função de ativação da última camada da rede (default: 'sigmoid').
        
        Return:
            unet: Objeto segmentation.UNet.
        
        Warnings:
            Se name atribuido à U-Net já estiver sendo usado para salvar outro modelo, a variável será alterada e um aviso será emitido informando a alteração.
        '''
        self._check_dataset()

        if self._dir.exists():
            self._dir = add_dir_id(self._dir)
            self.name = str(self._dir.stem)
            self._logs_path = self._dir/'logs.csv'

        self.model = build_unet(input_shape=self.x_train.shape[1:], filters=filters, name=self.name, activation=activation)
        return self

    def evaluate(self, **kwargs):
        return self.model.evaluate(self.x_test, self.y_test, **kwargs)
    
    def delete(self):
        for filepath in self._dir.glob('*'):
            filepath.unlink()
        self._dir.rmdir()
    
    def fit(self, epochs:int, batch_size:int, plot:bool, period:int=10, ranking:bool=False):
        '''
        Treinamento da rede.

        Args:
            epochs: Número de épocas de treimento.
            batch_size: Número de imagens por pacote.
            period (opcional): Período de atualização dos gráficos sobre o treinamento do modelo.
        '''
        self._check_dataset()

        try: initial_epoch = pd.read_csv(self._logs_path).epoch.max()
        except FileNotFoundError: initial_epoch = 0

        self._dir.mkdir(exist_ok=True)
        self.save()

        default_callbacks = [
            callbacks.CSVLogger(self._logs_path, append=True),
            callbacks.ModelCheckpoint(self._dir/'weights.{epoch:04d}.h5', verbose=0, save_weights_only=True),
            callbacks.ModelCheckpoint(self._dir/f'{self.name}.h5', verbose=0, save_weights_only=False),
        ]
        if plot: default_callbacks.append(TrainingBoard(self, period, ranking))

        return self.model.fit(
            self.x_train,
            self.y_train,
            validation_data= (self.x_test, self.y_test),
            batch_size= batch_size,
            epochs= epochs + initial_epoch,
            initial_epoch= initial_epoch,
            verbose= 1,
            callbacks= default_callbacks
        )

    def load(self, **kwargs):
        '''
        Carregar U-Net.
        
        Return:
            U-Net.
        '''
        self.model = load_model(self._dir/f'{self.name}.h5', **kwargs)
        return self
    
    def load_weights(self, epoch):
        if type(epoch) is int: 
            epoch = str(epoch)
            while len(epoch) < 4: epoch = '0' + epoch
        self.model.load_weights(self._dir/f'weights.{epoch}.h5')
    
    def get_dataset(self):
        return ((self.x_train, self.y_train),
                (self.x_test, self.y_test))
    
    def get_logs(self):
        return pd.read_csv(self._logs_path)
    
    def set_dataset(self, dataset):
        self.dataset = dataset
        
    def save(self):
        '''
        Salvar modelo.
        '''
        return self.model.save(self._dir/f'{self.name}.h5')