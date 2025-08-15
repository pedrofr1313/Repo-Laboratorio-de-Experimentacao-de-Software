# 📊 GitHub Analyzer MVP - Lab01S01

Este projeto é parte do laboratório **Lab01S01** da disciplina de Engenharia de Software. O objetivo principal é analisar características de **repositórios populares open-source** utilizando a API GraphQL do GitHub.

## 🎯 Objetivo

Investigar as seguintes **Questões de Pesquisa (RQs)** com base em dados reais dos **1.000 repositórios com mais estrelas no GitHub**:

- **RQ01:** Sistemas populares são maduros/antigos?  
- **RQ02:** Sistemas populares recebem muita contribuição externa?  
- **RQ03:** Sistemas populares lançam releases com frequência?  
- **RQ04:** Sistemas populares são atualizados com frequência?  
- **RQ05:** Sistemas populares são escritos nas linguagens mais populares?  
- **RQ06:** Sistemas populares possuem um alto percentual de issues fechadas?  
- **RQ07 (Bônus):** Linguagens populares influenciam na contribuição, releases e atualizações?

---

## ⚙️ Metodologia

- **Coleta de Dados:**  
  Utilizamos a API GraphQL do GitHub para buscar 1.000 repositórios mais populares (`stars:>1000`), em lotes de 10 por requisição, usando paginação.

- **Requisições:**  
  Foram feitas 100 requisições para coletar os 1.000 repositórios desejados.

- **Métricas Coletadas:**
  - Data de criação (`createdAt`)
  - Data de última atualização (`updatedAt`)
  - Total de estrelas (`stargazerCount`)
  - Total de pull requests aceitas (merged)
  - Total de releases
  - Linguagem primária
  - Total de issues e issues fechadas

- **Análise:**  
  Os dados foram processados e resumidos em métricas estatísticas como **média**, **mediana**, **moda**, **frequência** e **percentuais**.

---

## 🧪 Execução

### ✅ Pré-requisitos

- Python 3.8+
- Biblioteca `requests`
- Biblioteca `python-dotenv`
- Um token de acesso do GitHub válido

### 📦 Instalar dependências

```bash
pip install -r requirements.txt
