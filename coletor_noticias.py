import streamlit as st
import json
import urllib.request
from datetime import datetime

# Função para carregar configurações do arquivo JSON
def carregar_configuracoes(caminho='.config/config.json'):
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
apikey = config['API_KEY']
URL_BASE_SEARCH = config['URL_BASE_SEARCH']
LANG_DEFAULT = config.get('LANG_DEFAULT', 'pt')
MAX_RESULTS = config.get('MAX_RESULTS', 20)
CATEGORIAS = config.get('CATEGORIAS', [])

def construir_url(pesquisa='', lingua=LANG_DEFAULT, pais=None, categoria=None):
    params = {
        'q': pesquisa if pesquisa else '',
        'lang': lingua,
        'country': pais if pais else '',
        'max': MAX_RESULTS,
        'apikey': apikey
    }

    if categoria:
        params['topic'] = categoria.lower()

    params = {k: v for k, v in params.items() if v not in [None, '']}
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{URL_BASE_SEARCH}?{query_string}"

def buscar_noticias(pesquisa='', lingua=LANG_DEFAULT, pais=None, categoria=None):
    url = construir_url(pesquisa, lingua=lingua, pais=pais, categoria=categoria)
    if not url:
        return []

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            artigos = data.get("articles", [])
            return [
                (
                    artigo.get('title', 'Sem título'),
                    artigo.get('description', 'Sem descrição'),
                    artigo.get('url', 'Sem URL'),
                    artigo.get('publishedAt', 'Sem data')
                )
                for artigo in artigos
            ]
    except Exception as e:
        st.error(f"Erro ao obter notícias: {e}")
        return []

# Interface Streamlit
st.markdown("""
    <style>
        .title { font-size: 36px; font-weight: bold; color: #0033A0; text-align: center; margin-bottom: 10px; }
        .newsapi { font-size: 28px; font-weight: bold; color: #0033A0; text-align: center; margin-bottom: 20px; }
        .sidebar-header { color: #0033A0; font-size: 22px; font-weight: bold; }
        .footer { position: fixed; bottom: 0; left: 0; width: 100%; background-color: #f1f1f1; text-align: center; padding: 10px; font-size: 14px; }
        .footer a { color: #0033A0; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
    </style>
    <div class="title">Coletor de Notícias</div>
    <div class="newsapi">com GNews API</div>
    <p style="text-align: center; color: #0033A0; font-size: 18px;">Digite uma palavra-chave ou escolha uma categoria para buscar notícias.</p>
""", unsafe_allow_html=True)

# Filtros de pesquisa
st.sidebar.markdown('<p class="sidebar-header">Filtros para Pesquisa</p>', unsafe_allow_html=True)
pesquisa = st.sidebar.text_input("O que você está buscando?", "")
lingua = st.sidebar.selectbox("Idioma:", ["pt", "en"], index=["pt", "en"].index(LANG_DEFAULT))
pais = st.sidebar.selectbox(
    "País:",
    options=[None, "us", "br", "de", "fr", "gb", "jp", "ca", "au", "it", "mx"],
    format_func=lambda x: f"{x.upper()}" if x else "Todos os países"
)
categoria = st.sidebar.selectbox(
    "Categoria:",
    options=[None] + CATEGORIAS,
    format_func=lambda x: x if x else "Todas as categorias"
)

# Botão de busca
if st.sidebar.button("Buscar Notícias"):
    if not pesquisa.strip() and not categoria:
        st.error("Por favor, insira uma palavra-chave ou selecione uma categoria.")
    else:
        st.subheader(f"Notícias sobre: {pesquisa or 'Todas as notícias'} | Categoria: {categoria if categoria else 'Todas'}")
        noticias = buscar_noticias(pesquisa, lingua, pais, categoria)

        if noticias:
            for i, (titulo, descricao, url, publicado_em) in enumerate(noticias, 1):
                publicado_em = datetime.fromisoformat(publicado_em).strftime('%d/%m/%Y %H:%M:%S') if publicado_em != 'Sem data' else 'Sem data'
                st.write(f"{i}. {titulo} \nDescrição: {descricao} \n[Leia mais]({url}) \nPublicado em: {publicado_em}")
        else:
            st.write("Nenhuma notícia encontrada!")

st.markdown("""
    <div class="footer">
        Desenvolvido por <strong>Fabiano Navarro</strong><br>
        <a href="https://www.linkedin.com/in/fabiano-de-navarro" target="_blank">Meu LinkedIn</a>
    </div>
""", unsafe_allow_html=True)
