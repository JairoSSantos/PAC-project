from tensorflow.keras import Input, Model
from tensorflow.keras.layers import Layer, Conv2D, Conv2DTranspose, Activation, BatchNormalization, Concatenate, MaxPool2D
from tensorflow.math import maximum, sign, reduce_sum
from tensorflow import custom_gradient
from tensorflow.keras.callbacks import Callback
from IPython.display import clear_output
import matplotlib.pyplot as plt

@custom_gradient
def heaviside(x):
    return 1 - maximum(-sign(x), 0), lambda div: div

def conv_block(x, num_filters):
    for _ in range(2):
        x = Conv2D(num_filters, 3, padding='same')(x)
        x = BatchNormalization()(x)
        x = Activation('relu')(x)
    return x

def encoder_block(x, num_filters):
    x = conv_block(x, num_filters)
    p = MaxPool2D((2, 2))(x)
    return x, p

def decoder_block(x, skip_features, num_filters):
    x = Conv2DTranspose(num_filters, (2, 2), strides=2, padding='same')(x)
    x = Concatenate()([x, skip_features])
    x = conv_block(x, num_filters)
    return x

def build_unet(input_shape, u_shape, name='U-Net'):
    inputs = Input(input_shape)
    skips = []
    x = inputs
    for f in u_shape[:-1]:
        skip, x = encoder_block(x, f)
        skips.append(skip)
        
    x = conv_block(x, u_shape[-1])
    
    for f, s in zip(u_shape[:-1][::-1], skips[::-1]):
        x = decoder_block(x, s, f)

    outputs = Conv2D(1, 1, padding='same', activation=heaviside)(x)

    model = Model(inputs, reduce_sum(outputs, axis=[1, 2]), name=name)
    return model

class ConvBlock(Layer):
    def __init__(self, filters):
        super(ConvBlock, self).__init__()
        self.convs = [
            Conv2D(filters, 3, padding='same'),
            BatchNormalization(),
            Activation('relu'),
            Conv2D(filters, 3, padding='same'),
            BatchNormalization(),
            Activation('relu')
        ]
    
    def call(self, x):
        for layer in self.convs:
            x = layer(x)
        return x

class Encoder(Layer):
    def __init__(self, filters):
        super(Encoder, self).__init__()
        self.conv_block = ConvBlock(filters)
        self.maxpool = MaxPool2D((2, 2))
        self.skip = None
    
    def call(self, x):
        self.skip = self.conv_block(x)
        return self.maxpool(self.skip)

class Decoder(Layer):
    def __init__(self, filters, encoder):
        super(Decoder, self).__init__()
        self.encoder = encoder
        self.conv_transpose = Conv2DTranspose(filters, (2, 2), strides=2, padding='same')
        self.concat = Concatenate()
        self.conv_block = ConvBlock(filters)
    
    def call(self, x):
        return self.conv_block(self.concat([self.encoder.skip, self.conv_transpose(x)]))

class UNetAreaDetection(Model):
    def __init__(self, filters, activation=heaviside, **kwargs):
        super(UNetAreaDetection, self).__init__(**kwargs)
        self.filters = filters
        self.activation = activation

        contracting = []
        expanding = []
        for f in self.filters[:-1]:
            contracting.append(Encoder(f))
            expanding.insert(0, Decoder(f, contracting[-1]))
        
        self.net_layers = (
            #[Input(input_shape)] +
            contracting + # contração
            [ConvBlock(self.filters[-1])] + # conexão
            expanding + # expansão
            [Conv2D(1, 1, padding='same', activation=self.activation)] # ativação
        )
    
    def call(self, x, training):
        for layer in self.net_layers:
            x = layer(x)
        return reduce_sum(x, axis=[1, 2]) if training else x

class TrainingPlot(Callback):
    def __init__(self, update):
        super(Callback, self).__init__()
        self.update = update
        self.logs = {}
    
    def on_epoch_end(self, epoch, logs={}):
        for k, v in logs.items():
            try: self.logs[k].append(v)
            except KeyError: self.logs[k] = [v]
        clear_output(wait=True)
        self.update(self.logs, self.model)
        plt.show()