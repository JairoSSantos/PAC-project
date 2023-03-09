import tensorflow as tf
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
def DSC(y_true, y_pred):
    '''
    Dice Similarity Coefficient
    '''
    return 2*tf.reduce_sum(y_true*y_pred, axis=(-1, -2, -3))/(tf.reduce_sum(y_true) + tf.reduce_sum(y_pred))