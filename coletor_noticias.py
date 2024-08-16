import streamlit as st
import requests
import json
from datetime import datetime

# Função para carregar configurações a partir do arquivo JSON
def carregar_configuracoes(caminho='config.json'):
    try:
        with open(caminho, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Arquivo de configuração não encontrado!")
        raise
    except json.JSONDecodeError:
        st.error("Erro ao ler o arquivo de configuração. Verifique o formato JSON.")
        raise

# Carregar as configurações
config = carregar_configuracoes()
CHAVE_API = config['CHAVE_API']
URL_BASE_TOP_HEADLINES = config['URL_BASE_TOP_HEADLINES']
URL_BASE_EVERYTHING = config['URL_BASE_EVERYTHING']

# Lista de países para seleção
PAISES = {
    "Brasil": "br",
    "Estados Unidos": "us",
    "Alemanha": "de",
    "França": "fr",
    "Reino Unido": "gb",
    "Japão": "jp",
    "Canadá": "ca",
    "Austrália": "au",
    "Itália": "it",
    "México": "mx",
    # Adicione outros países conforme necessário
}

# Lista de categorias para seleção
CATEGORIAS = [
    "", "business", "entertainment", "general", "health", "science", "sports", "technology"
]

def construir_url_top_noticias(pais, fonte=None, categoria=None, pesquisa=None):
    if fonte:
        return f"{URL_BASE_TOP_HEADLINES}sources={fonte}&apiKey={CHAVE_API}"
    elif categoria:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&category={categoria}&apiKey={CHAVE_API}"
    elif pesquisa:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&q={pesquisa}&apiKey={CHAVE_API}"
    else:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&apiKey={CHAVE_API}"

@st.cache_data
def top_noticias(pais, fonte=None, categoria=None, pesquisa=None):
    """
    Retorna as top notícias do site newsapi.org
    :param pais: requerido - ex: br
    :param fonte: opcional - ex: globo
    :param categoria: opcional - ex: 'technology'
    :param pesquisa: opcional - ex: bolsonaro
    :return: lista de top notícias
    """
    url = construir_url_top_noticias(pais, fonte, categoria, pesquisa)
    
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        artigos = dados.get('articles', [])

        top_noticias = [(
            artigo['title'],
            artigo['url'],
            artigo['publishedAt']
        ) for artigo in artigos]

        return top_noticias
    except requests.RequestException as e:
        st.error(f"Erro ao obter notícias: {e}")
        return []

@st.cache_data
def todas_noticias(pesquisa, lingua=None):
    """
    Retorna todas as notícias do site newsapi.org
    :param pesquisa: requerido - Ex: 'trump'
    :param lingua: opcional - Ex: 'pt'
    :return: Lista de todas as notícias
    """
    url = f"{URL_BASE_EVERYTHING}q={pesquisa}&language={lingua or 'en'}&apiKey={CHAVE_API}"
    
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        artigos = dados.get('articles', [])

        todas_noticias = [(
            artigo['title'],
            artigo['url'],
            artigo['publishedAt']
        ) for artigo in artigos]

        return todas_noticias
    except requests.RequestException as e:
        st.error(f"Erro ao obter notícias: {e}")
        return []

def main():
    st.title("🔍 Coletor de Notícias com NewsAPI")

    st.sidebar.header("Parâmetros de Pesquisa")

    pais = st.sidebar.selectbox(
        "Escolha o país da notícia:",
        options=list(PAISES.keys()),
        format_func=lambda x: f"{x} ({PAISES[x]})"
    )
    codigo_pais = PAISES[pais]
    
    pesquisa = st.sidebar.text_input("Insira o que pesquisar (palavra ou frase):", "")
    fonte = st.sidebar.text_input("Insira a fonte (opcional, ex: globo):", "")
    categoria = st.sidebar.selectbox(
        "Escolha a categoria (opcional):",
        CATEGORIAS
    )

    if st.sidebar.button("Buscar Top Notícias"):
        st.subheader(f"Top Notícias do País - {pais.upper()}")
        noticias = top_noticias(codigo_pais, fonte=fonte, categoria=categoria, pesquisa=pesquisa)

        if noticias:
            for i, (titulo, url, publicado_em) in enumerate(noticias, 1):
                publicado_em = datetime.fromisoformat(publicado_em).strftime('%d/%m/%Y %H:%M:%S')
                st.write(f"{i}. {titulo} \n[Leia mais]({url}) \nPublicado em: {publicado_em}")
        else:
            st.write("Não encontrei notícias com as opções informadas!")

    if st.sidebar.button("Buscar Todas as Notícias"):
        st.subheader(f"Todas as Notícias sobre - {pesquisa.upper()}")
        todas_noticias_resultado = todas_noticias(pesquisa, lingua='pt')

        if todas_noticias_resultado:
            for i, (titulo, url, publicado_em) in enumerate(todas_noticias_resultado, 1):
                publicado_em = datetime.fromisoformat(publicado_em).strftime('%d/%m/%Y %H:%M:%S')
                st.write(f"{i}. {titulo} \n[Leia mais]({url}) \nPublicado em: {publicado_em}")
        else:
            st.write("Não encontrei notícias com as opções informadas!")

if __name__ == "__main__":
    main()
