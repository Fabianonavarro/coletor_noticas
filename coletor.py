import requests
import json

# Função para carregar configurações a partir do arquivo JSON
def carregar_configuracoes(caminho='config.json'):
    with open(caminho, 'r') as f:
        return json.load(f)

# Carregar as configurações
config = carregar_configuracoes()
CHAVE_API = config['CHAVE_API']
URL_BASE_TOP_HEADLINES = config['URL_BASE_TOP_HEADLINES']
URL_BASE_EVERYTHING = config['URL_BASE_EVERYTHING']

def construir_url_top_noticias(pais, fonte=None, categoria=None, pesquisa=None):
    if fonte:
        return f"{URL_BASE_TOP_HEADLINES}sources={fonte}&apiKey={CHAVE_API}"
    elif categoria:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&category={categoria}&apiKey={CHAVE_API}"
    elif pesquisa:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&q={pesquisa}&apiKey={CHAVE_API}"
    else:
        return f"{URL_BASE_TOP_HEADLINES}country={pais}&apiKey={CHAVE_API}"

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

        top_noticias = [f"{artigo['title']}, Imagem: {artigo['url']}, Publicado em: {artigo['publishedAt']}"
                        for artigo in artigos]

        return top_noticias
    except requests.RequestException as e:
        print(f"Erro ao obter notícias: {e}")
        return []

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

        todas_noticias = [f"{artigo['title']}, Imagem: {artigo['url']}, Publicado em: {artigo['publishedAt']}"
                          for artigo in artigos]

        return todas_noticias
    except requests.RequestException as e:
        print(f"Erro ao obter notícias: {e}")
        return []
