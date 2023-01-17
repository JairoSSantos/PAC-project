import os
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras import Input, Model, layers
from tensorflow.keras.callbacks import Callback
from tensorflow.keras.models import load_model
from IPython.display import clear_output
from skimage.color import label2rgb
from warnings import warn

SAVE_PATH = os.path.join(*os.path.split(__file__)[:-1], 'saves')

def mape(y_pred:np.ndarray, y_true:np.ndarray):
    '''
    Mean absolute percentage error (erro percentual médio).

    Args:
        y_pred: Valor da predição.
        y_true: Valor verdadeiro.
    
    Return:
        erro: mean(|y_true - y_pred|/y_true * 100)
    '''
    return np.mean(np.abs(y_true - y_pred)/y_true * 100)

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

def check_unet_name(name:str):
    '''
    Verifica se já existe uma U-Net salva com este nome nos modelos salvos.
    Se existir um modelo salvo com este nome, um numero inteiro será adicionado apos este (ex: 'U-Net', 'U-Net0', 'U-Net1', ...) e um aviso será emitido.

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

def build_UNet(input_shape:tuple, filters:tuple, name:str, activation:str='sigmoid'):
    '''
    Construir U-Net.

    Args:
        input_shape: Formato dos dados de entrada (3 valores inteiros: [altura, largura, canais]).
        filters: Número de filtros para cada etapa de codificação (a mesma quantidade será utilizada na etapa de decodificação).
        name: Nome da rede, será utilizado para salvar o modelo.
        activation (opcional): Função de ativação da última camada da rede (default: 'sigmoid').
    
    Return:
        unet: U-Net, rede neural convolucional para segmentação semantica.
    '''
    name = check_unet_name(name)
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

def load_unet(name:str):
    '''
    Carregar U-Net.

    Args:
        name: Nome do modelo.
    
    Return:
        U-Net já compilada.
    '''
    return load_model(os.join(SAVE_PATH, name, f'{name}.h5'))

class UNetTrainingPlot(Callback):
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

        Y_rel_area = np.concatenate((self.y_rel_area_train, self.y_rel_area_test))
        ymin, ymax = Y_rel_area.min(), Y_rel_area.max()
        dy = 0.2*(ymax - ymin)
        self.t_min, self.t_max = ymin - dy, ymax + dy
        self.t = np.linspace(self.t_min, self.t_max, 50)

        self.logs = {}
    
    def update_logs(self, logs):
        '''
        Atualizar logs
        '''
        for k, v in logs.items():
            try: self.logs[k].append(v)
            except KeyError: self.logs[k] = [v]

    def plot(self):
        '''
        Plotar métricas.
        '''
        pred_train = (self.unet.predict(self.x_train, verbose=0) > 0.5).astype(int)
        pred_train_rel_area = pred_train.sum(axis=(1, 2))/self.area_total
        pred_test = (self.unet.predict(self.x_test, verbose=0) > 0.5).astype(int)
        pred_test_rel_area = pred_test.sum(axis=(1, 2))/self.area_total

        clear_output(wait=True)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4))

        ax1.plot(self.logs['loss'], label='loss')
        ax1.plot(self.logs['val_loss'], label='val_loss')
        ax1.semilogy()
        ax1.legend()
        ax1.set_ylim(bottom=0)

        i = np.random.randint(0, self.x_test.shape[0]-1)
        ax2.imshow(label2rgb(pred_test[i, :, :, 0], self.x_test[i, :, :, 0], bg_label=0))

        ax3.plot(self.y_rel_area_train, pred_train_rel_area, 'bo', alpha=0.5, 
            label=r'MAPE(train) = {}%'.format(np.round(mape(self.y_rel_area_train, pred_train_rel_area), 2)))
        ax3.plot(self.y_rel_area_test, pred_test_rel_area, 'ro', alpha=0.5,
            label=r'MAPE(val) = {}%'.format(np.round(mape(self.y_rel_area_test, pred_test_rel_area), 2)))
        ax3.plot(self.t, self.t, 'k--')
        ax3.set_xlim(self.t_min, self.t_max)
        ax3.set_ylim(self.t_min, self.t_max)
        ax3.set_aspect('equal')
        ax3.legend()
        plt.show()
    
    def on_epoch_end(self, epoch, logs={}):
        self.update_logs(logs)
        if epoch % self.period == 0: self.plot()
    
    def on_train_end(self, logs={}):
        self.update_logs(logs)
        self.plot()

class UNetCheckpoint(Callback):
    '''
    Callback para salvar evolução do treinamento.
    '''
    def __init__(self, unet):
        super(Callback, self).__init__()

        self.unet = unet
        self.path = os.path.join(SAVE_PATH, unet.name)
        self.model_path = os.join(self.path, f'{self.unet.name}.h5')
        self.weights_path = os.path.join(self.path, 'weights')
        self.logs_path = os.join(self.path, 'logs.csv')
        self.logs = {'epoch':[], 'loss':[], 'val_loss':[]}
    
    def on_train_begin(logs):
        os.mkdir(self.path)
        os.mkdir(self.weights_path)
        try: self.initial_epoch = pd.read_csv(self.logs_path).epoch.max()
        except FileNotFoundError: self.initial_epoch = 0

    def on_epoch_end(self, epoch, logs={}):
        epoch += self.initial_epoch

        for k, v in logs.items():
            try: self.logs[k].append(v)
            except KeyError: self.logs[k] = [v]
        self.logs['epoch'].append(epoch)
        
        if logs['val_loss'] <= min(self.logs['val_loss']):
            filename = 'epoch-{} val_loss-{}.h5'.format(epoch, np.round(logs['val_loss'], 2))
            self.unet.save_weights(os.path.join(self.weights_path, filename))
            self.unet.save(self.model_path)
        
        pd.DataFrame(self.logs).to_csv(self.logs_path, index=False)