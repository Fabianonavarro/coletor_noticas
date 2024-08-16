from coletor_noticias import top_noticias, todas_noticias

def main():
    print("=== COLETOR DE NOTÍCIAS VIA API - NEWSAPI.ORG ===")
    print()
    print("Favor, insira as informações solicitadas abaixo")

    pais = input("Insira o país da notícia (br, us, de, etc): ")
    pesquisa = input("Insira o que pesquisar (palavra ou frase): ")
    fonte = input("Insira a fonte (globo, blasting-news-br, google-news-br): ")
    categoria = input("Insira a categoria (business, entertainment, general, health, science, sports, technology): ")

    # Chamando a função top_noticias
    print("\n**** Listando as Top Notícias do País - {} ****".format(pais.upper()))
    noticias = top_noticias(pais, fonte=fonte, categoria=categoria, pesquisa=pesquisa)
    
    if noticias:
        for i, noticia in enumerate(noticias, 1):
            print(f"{i} - {noticia}")
    else:
        print("Não encontrei notícias com as opções informadas!")

    # Chamando a função todas_noticias
    print("\n**** Listando Todas as Notícias sobre - {} ****".format(pesquisa.upper()))
    todas_noticias_resultado = todas_noticias(pesquisa, lingua='pt')

    if todas_noticias_resultado:
        for i, noticia in enumerate(todas_noticias_resultado, 1):
            print(f"{i} - {noticia}")
    else:
        print("Não encontrei notícias com as opções informadas!")

if __name__ == "__main__":
    main()
