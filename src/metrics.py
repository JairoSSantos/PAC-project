import tensorflow as tf
from tensorflow.keras.losses import Loss
from tensorflow.keras.metrics import mape

def gauge(metric):
    def wrapped_metric(y_true, y_pred):
        return metric(y_true, y_pred[:, 0])
    wrapped_metric.__name__ = metric.__name__
    return wrapped_metric

@tf.function
def angular_distance(y_true, y_pred):
    dist = tf.abs(y_true - y_pred)
    return tf.where(dist > 45, 90 - dist, dist)

@tf.function
def angular_mape(y_true, y_pred):
    return angular_distance(y_true, y_pred)/y_true * 100

@tf.function
def area_mape(y_true, y_pred):
    '''
    Erro percentual médio adaptado para comparar as áreas (em píxel) entre a saída do modelo `y_pred` e o valor verdadeiro `y_true`.

    Args:
        y_true: Tensor contendo as máscaras verdadeiras.
        y_pred: Tensor contendo as saídas da rede neural.
    '''
    area_true = tf.reduce_sum(y_true, axis=(-1, -2, -3))
    area_pred = tf.reduce_sum(y_pred, axis=(-1, -2, -3))
    return mape(area_true, area_pred)

@tf.function
def IoU(y_true, y_pred):
    intersection = tf.math.reduce_sum(y_true*y_pred + (1 - y_true)*(1 - y_pred), axis=(1, 2, 3))
    union = tf.math.reduce_sum(y_true*(2 - y_pred) + (1 - y_true)*(1 + y_pred), axis=(1, 2, 3))
    return intersection/union

@tf.function
def DSC(y_true, y_pred):
    return tf.math.reduce_mean(y_true*y_pred + (1 - y_true)*(1 - y_pred), axis=(1, 2, 3))

class Dice(Loss):
    def __init__(self):
        super().__init__()
    
    def call(self, y_true, y_pred):
        return 1 - DSC(y_true, y_pred)

class TopK(Loss):
    def __init__(self, k, image_shape):
        super().__init__()
        assert 0 <= k <= 1
        self.N = tf.cast(tf.reduce_prod(image_shape), tf.float32)
        self.k = tf.cast(self.N*k, tf.int32) # k's threshold
    
    @tf.function
    def top_k(self, x):
        return tf.reduce_sum(tf.math.top_k(tf.reshape(x, [-1]), k=self.k, sorted=False).values)/self.N
    
    @tf.function
    def call(self, y_true, y_pred):
        loss = - y_true*tf.math.log(y_pred) - (1 - y_true)*tf.math.log(1 - y_pred)
        return tf.map_fn(self.top_k, loss, fn_output_signature=tf.float32)

class DiceTopK(Dice, TopK):
    def __init__(self, *args, **kwargs):
        super(Dice, self).__init__(*args, **kwargs)
        super(TopK, self).__init__()
    
    def call(self, y_true, y_pred):
        return Dice.call(self, y_true, y_pred) + TopK.call(self, y_true, y_pred)