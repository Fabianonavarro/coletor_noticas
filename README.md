# 📈 Coletor de Notícias

Bem-vindo ao **Coletor de Notícias**! Este é um projeto que coleta e exibe notícias de diversas fontes e categorias usando a [GnewsAPI](https://gnews.io/). 
O projeto foi desenvolvido em Python e utiliza a biblioteca [Streamlit](https://streamlit.io) para criar uma interface interativa.

## 🚀 Como Usar

1. **Clone o Repositório:**

   ```bash
   git clone https://github.com/Fabianonavarro/coletor_noticas.git
   cd coletor_noticas
Instale as Dependências:

Crie um ambiente virtual e instale as dependências:

bater

Copiar código
python -m venv venv
source venv/bin/activate  # Para Linux/MacOS
venv\Scripts\activate     # Para Windows
pip install -r requirements.txt
Configure a Chave da API:

Crie um arquivo de configuração chamado .config/config.json com o seguinte conteúdo:

json

Copiar código

{
  "API_KEY": "sua_chave_aqui",
  "URL_BASE_SEARCH": "https://gnews.io/api/v4/search",
  "LANG_DEFAULT": "pt",
  "MAX_RESULTS": 20,
  "CATEGORIAS": [
    "Sport",
    "Politics",
    "Economy",
    "Technology",
    "Health",
    "Science",
    "Entertainment"
  ]
}


Execute o Aplicativo:

Você pode executar o aplicativo de duas maneiras:

Usando o comando do Streamlit:

streamlit run coletor_noticias.py
Usando o arquivo roda.bat (para Windows):

Dê um duplo clique no arquivo roda.bat para iniciar o aplicativo.

🌐 Aplicativo Online
Você pode acessar o aplicativo online no seguinte link:

📲 Coletor de Notícias - https://coletornoticas-nav.streamlit.app/

🛠️ Funcionalidades
Obter Top Notícias: Veja as principais notícias por país, fonte, categoria ou pesquisa.
Buscar Notícias: Encontre todas as notícias relacionadas a uma palavra-chave específica.

📂 Estrutura do Projeto

coletor_noticias.py: Código principal do aplicativo Streamlit.

requirements.txt: Lista de

.config/config.json: Arquivo de configuração para a chave da API e URLs.

roda.bat: Script para facilitar a execução do aplicativo no Windows.

README.md: Documentação do projeto.

📜 Licença

Este projeto está licenciado sob a MIT License. Veja o arquivo LICENSE para mais detalhes.

📧 Contato

Se você tiver alguma dúvida ou sugestão, sinta-se à vontade para entrar em contato comigo:

GitHub: [Fabianonavarro](httpFabianonavarro
