import requests

# CONFIG.PY 
CHAVE_API = "a56f1d245fac46468e6c802f87a9452d"
URL_BASE_TOP_HEADLINES = "http://newsapi.org/v2/top-headlines?"
URL_BASE_EVERYTHING = "https://newsapi.org/v2/everything?"

# HELPERS.PY #
def top_noticias(pais, fonte=None, categoria=None, pesquisa=None):
    """
    Retorna as top noticias do site newsapi.org
    :param pais: requerido - ex: br
    :param fonte: opcional - ex: globo
    :param categoria: opcional - ex: 'technology'
    :param pesquisa: opcional - ex: bolsonaro
    :return: lista de top notícias
    """

    if fonte:
        url = f"{URL_BASE_TOP_HEADLINES}sources={fonte}&apiKey={CHAVE_API}"
    elif categoria:
        url = f"{URL_BASE_TOP_HEADLINES}country={pais}&category={categoria}&apiKey={CHAVE_API}"
    elif pesquisa:
        url = f"{URL_BASE_TOP_HEADLINES}country={pais}&q={pesquisa}&apiKey={CHAVE_API}"
    else:
        url = f"{URL_BASE_TOP_HEADLINES}country={pais}&apiKey={CHAVE_API}"

    # Coletando dados em formato json
    resposta = requests.get(url).json()
    
    # Pegando todos os artigos
    artigos = resposta['articles']

    # Lista vazia para preencher com noticias
    top_noticias = []

    for artigo in artigos:
        top_noticias.append(f"{artigo['title']}, "
                            f"Imagem: {artigo['url']}, "
                            f"Publicado em: {artigo['publishedAt']}")

    return top_noticias


def todas_noticias(pesquisa, lingua=None):
    """
    Retorna todas as notícias do site newsapi.org
    :param pesquisa: requerido - Ex: 'trump'
    :param lingua: opcional - Ex: 'pt'
    :return: Lista de todas as notícias
    """
    """
    Retorna todas as noticias do site newsapi.org
    :param pesquisa: inserir o país para pesquisar as noticias
    :return: Lista de noticias do país
    """
    todas_noticias = []
    if pesquisa:
        # Lista vazia para preencher com noticias

        if lingua:
            url = f"{URL_BASE_EVERYTHING}q={pesquisa}&language={lingua}&apiKey={CHAVE_API}"

        # Coletando dados em formato json
        resposta = requests.get(url).json()

        # Pegando todos os artigos
        artigos = resposta['articles']

        for artigo in artigos:
            todas_noticias.append(f"{artigo['title']}, "
                                  f"Imagem: {artigo['url']}, "
                                  f"Publicado em: {artigo['publishedAt']}")

    return todas_noticias

# MAIN.PY #
print("===COLETOR NOTÍCIAS VIA API - NEWSAPI.ORG===")
print()
print("Favor, insira as informações solicitadas abaixo")
pais = input("Insira o país da notícia (br, us, de, etc): ")
pesquisa = input("Insira o que pesquisar (palavra ou frase): ")
fonte = input("Insira a fonte (globo, blasting-news-br, google-news-br): ")
categoria = input("Insira a categoria (business, entertainment, general, health, science, sports, technology): ")

# Chamando a função
print()
print()
noticias = top_noticias(pais, pesquisa=pesquisa)

print(f" **** Listando as Top Notícias do País - {pais.upper()} ****")
if noticias:
    for numero in range(len(noticias)):
        print(f"{numero + 1} - {noticias[numero]}")
else:
    print("Não encontrei notícias com as opções informadas!")

# Chamando a função
print()
print()
todas_noticias = todas_noticias(pesquisa, lingua='pt')

print(f" **** Listando Todas as Notícias sobre - {pesquisa.upper()} ****")
if todas_noticias:
    for numero in range(len(todas_noticias)):
        print(f"{numero + 1} - {todas_noticias[numero]}")
else:
    print("Não encontrei notícias com as opções informadas!")
