from pathlib import Path

class Paths:
    DATA = Path('.data/')
    TRAIN = DATA / 'train'
    TEST = DATA / 'test'
    MODELS = Path('.models/')