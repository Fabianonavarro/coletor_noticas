import streamlit as st
import requests
import json
from datetime import datetime

# Função para carregar configurações a partir do arquivo JSON
def carregar_configuracoes(caminho='.config/config.json'):
    """
    Carrega as configurações do arquivo JSON.
    
    :param caminho: Caminho para o arquivo de configuração.
    :return: Dicionário com as configurações.
    """
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
    """
    Constrói a URL para a API de top notícias.

    :param pais: Código do país.
    :param fonte: Opcional. Código da fonte de notícias.
    :param categoria: Opcional. Categoria de notícias.
    :param pesquisa: Opcional. Palavra-chave para pesquisa.
    :return: URL completa para a requisição.
    """
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
    Retorna as top notícias do site newsapi.org.

    :param pais: Requerido - Código do país (ex: br).
    :param fonte: Opcional - Código da fonte de notícias (ex: globo).
    :param categoria: Opcional - Categoria de notícias (ex: 'technology').
    :param pesquisa: Opcional - Palavra-chave para pesquisa (ex: bolsonaro).
    :return: Lista de top notícias.
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
    Retorna todas as notícias do site newsapi.org.

    :param pesquisa: Requerido - Palavra-chave para pesquisa (ex: 'trump').
    :param lingua: Opcional - Idioma das notícias (ex: 'pt').
    :return: Lista de todas as notícias.
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
    """
    Função principal para executar o aplicativo Streamlit.
    """
    st.markdown("""
        <style>
            .title {
                font-size: 36px;
                font-weight: bold;
                color: #0033A0;
                text-align: center;
                margin-bottom: 10px;
            }
            .newsapi {
                font-size: 28px;
                font-weight: bold;
                color: #0033A0;
                text-align: center;
                margin-bottom: 20px;
            }
            .sidebar-header {
                color: #0033A0;
                font-size: 22px;
                font-weight: bold;
            }
            .footer {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: #f1f1f1;
                text-align: center;
                padding: 10px;
                font-size: 14px;
            }
            .footer a {
                color: #0033A0;
                text-decoration: none;
            }
            .footer a:hover {
                text-decoration: underline;
            }
        </style>
        <div class="title">Coletor de Notícias</div>
        <div class="newsapi">com NewsAPI</div>
        """, unsafe_allow_html=True)

    st.sidebar.markdown('<p class="sidebar-header">Filtros para Pesquisa</p>', unsafe_allow_html=True)

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

    st.markdown("""
        <div class="footer">
            Desenvolvido por <strong>Fabiano Navarro</strong><br>
            <a href="https://www.linkedin.com/in/fabiano-de-navarro" target="_blank">Meu LinkedIn</a>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
