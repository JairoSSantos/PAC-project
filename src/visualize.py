import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.style import use
from tensorflow.keras.callbacks import Callback
from skimage.color import label2rgb
from IPython.display import display, clear_output, HTML

def plot_image(image, ax=None, **kwargs):
    ax = (ax if ax is not None else plt)
    ax.imshow(np.squeeze(image), **kwargs)
    ax.axis('off')

def plot_label(image, label, **kwargs):
    return plot_image(label2rgb(np.squeeze(label), np.squeeze(image), bg_label=0), **kwargs)

def plot_seg_contour(image, label, y_pred, th=0.5, ax=None):
    ax = (ax if ax is not None else plt)
    plot_label(image, y_pred >= th, ax=ax)
    ax.contour(y_pred, levels=(0, 0.25, 0.5, 0.75, 1), cmap='magma')
    ax.contour(label, cmap='bone')

def set_custom_style():
    use({
        'scatter.edgecolors':'black',
        'lines.linewidth':2
    })

def plot_training(unet, clear=False, ranking=False):

    # ==================== Model info ====================
    y_pred_test = unet.model.predict(unet.x_test, verbose=0)
    y_pred_train = unet.model.predict(unet.x_train, verbose=0)
    area_pred_test = np.mean(y_pred_test, axis=(-1, -2, -3))
    area_pred_train = np.mean(y_pred_train, axis=(-1, -2, -3))

    j = np.random.randint(len(y_pred_test))
    img = unet.x_test[j, ..., 0]
    gtruth = unet.y_test[j, ..., 0]
    pred = y_pred_test[j, ..., 0]

    logs = unet.get_logs()
    best_epoch = logs.epoch[np.argmin(logs.val_loss)]
    n_metrics = len(unet.model.metrics) - 1

    # ==================== Figure config ====================
    fig = plt.figure(figsize=(18, 7))
    main_grid = GridSpec(10, 4, figure=fig)
    mh = 4
    metrics_grid = main_grid[-mh:, :].subgridspec(1, n_metrics)

    axs = {
        'seg': fig.add_subplot(main_grid[:-mh, 0]),
        'prec': fig.add_subplot(main_grid[:-mh, -1]),
        'loss': fig.add_subplot(main_grid[:-mh, 1:-1]),
    }

    # ==================== Segmentation ====================
    plot_seg_contour(img, gtruth, pred, 0.5, axs['seg'])

    # ==================== Loss ====================
    axs['loss'].plot(logs.epoch, logs.loss, label='loss')
    axs['loss'].plot(logs.epoch, logs.val_loss, label='validation loss')
    axs['loss'].vlines(best_epoch, *axs['loss'].get_ylim(), label=f'best epoch: {best_epoch}', linestyle='dashed', color='k')
    axs['loss'].set_xlabel('epoch')
    axs['loss'].set_ylabel('loss')
    axs['loss'].semilogy()
    axs['loss'].grid(True, axis='y')
    axs['loss'].legend()

    # ==================== Precision ====================
    axs['prec'].scatter(np.mean(unet.y_train, axis=(-1, -2, -3)), area_pred_train, alpha=0.7, label='training data')
    axs['prec'].scatter(np.mean(unet.y_test, axis=(-1, -2, -3)), area_pred_test, alpha=0.7, label='validation data')
    axs['prec'].set_aspect('equal')
    xmin, xmax = axs['prec'].get_xlim()
    dx = (xmax - xmin)*0.1
    xmin, xmax = xmin - dx, xmax + dx
    x = np.linspace(xmin, xmax, 25)
    axs['prec'].plot(x, x, 'k-', alpha=0.7, label=r'$y=x$')
    axs['prec'].set_xlim(xmin, xmax)
    axs['prec'].set_ylim(xmin, xmax)
    axs['prec'].set_xlabel('true rel area')
    axs['prec'].set_ylabel('pred rel area')
    axs['prec'].legend()
    
    # ==================== Metrics ====================
    for i, metric in enumerate(unet.model.metrics[1:]):
        ax = fig.add_subplot(metrics_grid[0, i])
        ax.plot(logs.epoch, logs[metric.name], label='training data')
        ax.plot(logs.epoch, logs[f'val_{metric.name}'], label=f'validation data')
        ax.set_xlabel('epoch')
        ax.set_ylabel(metric.name)
        ax.grid(True)
        ax.legend()
    
    # ==================== Show ====================
    fig.tight_layout()
    if clear: 
        clear_output(wait=True)
    plt.show()

    if ranking != False: 
        display(HTML(logs.sort_values('val_loss', ascending=True).head(int(ranking)).to_html()))

class TrainingBoard(Callback):
    def __init__(self, unet, period, ranking):
        super().__init__()
        self.unet = unet
        self.period = period
        self.ranking = ranking
    
    def on_epoch_end(self, epoch, logs=None):
        if epoch%self.period == 0:
            plot_training(self.unet, clear=True, ranking=self.ranking)