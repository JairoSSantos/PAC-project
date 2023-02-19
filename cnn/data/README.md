# Conjunto de dados

Nesta pasta são armazenadas as imagens utilizadas nos treinamentos e testes dos modelos. As imagens do subdiretório `/data/raw` são aquelas que necessitam de tratamento para serem utilizadas, enquando as imagens em `/data/dataset` já foram processadas. É importante ressaltar que todas as imagens pertencentes à este diretório devem conter apenas uma amostra, além de estarem nomeadas com suas respectivas áreas, obdecendo a notação `<área>_<unidade>.<ext>`, onde:

- `<área>`: Valor da área, no formato de ponto flutuante ou inteiro, obtido convencionalmente utilizando ImajeJ ou semelhante
- `<unidade>`: Unidade de área medida para a amostra (Ex.: "mm2" para milímetro quadrado)
- `<ext>`: Extenção da imagem, utilize ".jpg" para a imagem da amostra e ".png" para sua respectiva máscara

Em modelos de segmentação, é necessário que haja uma máscara para cada imagem utilizada no treinamento. Portanto, garanta que esta condição sempre seja satisfeita.