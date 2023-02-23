import tensorflow as tf

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
    return tf.reduce_mean(tf.abs(area_true - area_pred)/area_true * 100)