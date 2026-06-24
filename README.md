# Projeto LLD/LLB Detection

Este repositório contém os códigos desenvolvidos para a extração de atributos, pré-processamento, análise supervisionada e análise não supervisionada de programas PLC com foco na detecção estática de *Ladder Logic Bombs* (LLB).

O trabalho utiliza arquivos no formato **PLCopen XML** como entrada e converte a lógica de controle PLC em uma representação tabular de atributos. Esses atributos são posteriormente avaliados por modelos de aprendizado de máquina supervisionado e não supervisionado.

## Objetivo

O objetivo do projeto é investigar se atributos extraídos estaticamente da lógica de controle de PLC podem contribuir para distinguir programas normais de programas contendo lógicas maliciosas.

A análise busca identificar quais grupos de atributos apresentam maior potencial discriminativo, considerando:

* atributos estruturais e topológicos;
* atributos lógicos;
* atributos semânticos leves;
* atributos sequenciais.

## Estrutura geral do projeto

O projeto está organizado em etapas principais:

1. **Leitura dos arquivos PLCopen XML**
   Processamento dos arquivos XML contendo a lógica PLC.

2. **Extração de atributos**
   Uso de um parser em Python para extrair características da lógica de controle.

3. **Pré-processamento dos dados**
   Conversão de tipos, remoção de atributos inadequados à modelagem e organização dos dados.

4. **Análise supervisionada**
   Avaliação de classificadores para distinguir lógicas normais e lógicas contendo LLB.

5. **Análise por grupos de atributos**
   Avaliação separada dos grupos estruturais/topológicos, lógicos, semânticos leves e sequenciais.

6. **Análise não supervisionada**
   Aplicação de PCA e DBSCAN para verificar indícios de agrupamento natural entre as amostras.

## Modelos avaliados

Foram avaliados classificadores supervisionados, incluindo:

* Logistic Regression;
* Random Forest;
* Extra Trees;
* MLP Classifier;
* Gradient Boosting Classifier;
* LightGBM;
* SVM.

## Análise não supervisionada

A análise não supervisionada foi realizada com:

* **PCA**, para projeção dos atributos em duas componentes principais;
* **DBSCAN**, para identificar agrupamentos naturais e amostras classificadas como ruído.

## Requisitos

O projeto foi desenvolvido em Python. As principais bibliotecas utilizadas incluem:

```bash
pandas
numpy
scikit-learn
matplotlib
pycaret
```

Para instalar as dependências, execute:

```bash
pip install -r requirements.txt

1. Clone o repositório:


git clone https://github.com/dsmirandax/Projeto-LLD-detection.git
cd Projeto-LLD-detection
```

3. Execute o parser para extração de atributos dos arquivos PLCopen XML.

4. Execute o notebook ( ) para treinamento e avaliação dos modelos.
Esse notebook realiza a preparação dos dados, comparação dos modelos supervisionados, avaliação por grupos de atributos e análise não supervisionada.

## Resultados gerados

O notebook gera arquivos como:

* tabela de atributos extraídos;
* tabela comparativa de classificadores;
* métricas de avaliação;
* gráficos de importância de atributos;
* projeções PCA;
* clusters DBSCAN;
* tabelas de composição dos clusters.

## Observações

Os resultados devem ser interpretados no contexto do conjunto de dados analisado [Iacobelli, A. et. al.]

## Referência:
Iacobelli, A., Rinieri, L., Melis, A., Al Sadi, A., Prandini, M., & Callegati, F. (2024, May). Detection of Ladder Logic Bombs in PLC Control Programs: an Architecture based on Formal Verification. In 2024 IEEE 7th International Conference on Industrial Cyber-Physical Systems (ICPS) (pp. 1-7). IEEE.
