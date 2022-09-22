from segmentation import *
from DScontrol import *
#from collections.abc import Iterable
#import time

N_IMAGES_TESTING = 5

def gaussian(x, mean, std):
    return np.exp(-(x - mean)**2/(2*std**2))/np.sqrt(2*np.pi*std**2)

@dataclass
class GeneInt:
    name:str
    range:tuple[int, int]
    std:float

    def mutation(self, value:int):
        return np.clip(value + int(np.random.normal(0, self.std, 1)/gaussian(0, 0, self.std)), self.range[0], self.range[1])

    def random(self):
        return np.random.randint(*self.range)

class GeneticAlgorithm:
    def __init__(self, genes, pop_size, fitness):
        self.genes = genes
        self.pop_size = pop_size
        self.fitness = fitness

        self.population = [np.array([gene.random() for gene in self.genes]) for _ in range(self.pop_size)]
        self.history = {gene.name:[] for gene in self.genes}
        self.history.update({'M':[], 'bscore':[]})
    
    def load(self, path):
        self.history = pd.read_csv(path).to_dict('list')
        self.population = [np.array([gene.mutation(self.history[gene.name][-1]) 
                                     for gene in self.genes]) for _ in range(self.pop_size)] 

    def selection(self, epochs=500):
        for t in range(epochs):
            selec = [np.nan, np.nan]
            betters = [0, 0]
            scores_sum = 0

            print(f'Verificando população {t} |' + '-'*25 + '|', end='')
            for i in range(self.pop_size):
                score = self.fitness(*self.population[i])
                scores_sum += score
                if score > betters[0]:
                    betters[1] = betters[0]
                    betters[0] = score
                    selec[1] = selec[0]
                    selec[0] = self.population[i]

                hn = int(i/self.pop_size*25)
                print(f'\rVerificando população {t} {i+1}/{self.pop_size} |' + 'H'*hn + '-'*(25-hn) + '|', 
                    f'Último:{score:.5f}', f'Melhor:{betters[0]:.5f}', f'Média:{scores_sum/(i+1)}', end='')
            
            self.history['M'].append(scores_sum/self.pop_size)
            self.history['bscore'].append(betters[0])
            for i, gene in enumerate(self.genes):
                self.history[gene.name].append(selec[0][i])
            pd.DataFrame(self.history).to_csv('genefitting.csv', index=False)

            self.population = [np.array([gene.mutation(selec[i%2][i])
                                for i, gene in enumerate(self.genes)]) for _ in range(self.pop_size)] #+ selec
            print(f'\rDescrição da população {t} | MPs:{betters} | GN:{selec[0]} | Média: {scores_sum/self.pop_size}')

def fitness(*values):
    model = Model(*values)
    error = 0
    for image, filename in random_images(N_IMAGES_TESTING, True):
        area = float(DS.loc[DS.filename == filename].area)
        error += np.abs(area - model.predict(image))/area
    return 1 - error/N_IMAGES_TESTING

if __name__ == '__main__':
    GA = GeneticAlgorithm([
        GeneInt('variance_size', (0, 128), 1.7),
        GeneInt('minimum_size', (0, 128), 1.7),
        GeneInt('opening_iter', (0, 50), 1.7),
        GeneInt('closing_iter', (0, 50), 1.7),
        GeneInt('dilation_iter', (0, 50), 1.7)
    ], pop_size=80, fitness=fitness)
    GA.load('genefitting.csv')
    GA.selection()