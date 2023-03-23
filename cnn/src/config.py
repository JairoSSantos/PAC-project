from pathlib import Path

class Paths:
    DATA = Path('data/dataset')
    RAW = Path('data/raw')
    TRAIN = DATA/'train'
    TEST = DATA/'test'
    MODELS = Path('models/')