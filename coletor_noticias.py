import html
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import feedparser
import requests
import streamlit as st

st.set_page_config(page_title="Central de Informações", page_icon="🧭", layout="wide")

GNEWS_URL = "https://gnews.io/api/v4"
VIACEP_URL = "https://viacep.com.br/ws/{}/json/"
CONFIG_PATH = ".config/config.json"
USER_AGENT = "Mozilla/5.0 (compatible; CentralInformacoes/1.0)"

IDIOMAS = {"Português": "pt", "English": "en"}
PAISES = {
    "Todos os países": None, "Brasil": "br", "Estados Unidos": "us", "Alemanha": "de",
    "França": "fr", "Reino Unido": "gb", "Japão": "jp", "Canadá": "ca",
    "Austrália": "au", "Itália": "it", "México": "mx",
}
# Categorias aceitas pelo endpoint /top-headlines da GNews
CATEGORIAS = {
    "Geral": "general", "Mundo": "world", "Nacional": "nation", "Economia": "business",
    "Tecnologia": "technology", "Entretenimento": "entertainment",
    "Esportes": "sports", "Ciência": "science", "Saúde": "health",
}
FONTES = {"GNews (API, mundo)": "GNews", "RSS (G1, Folha, Agência Brasil)": "RSS"}

# Feeds RSS por categoria: (nome do portal, URL).
# Se algum feed mudar de endereço, é só ajustar aqui: feeds que falham são ignorados.
RSS_FEEDS = {
    "general": [
        ("G1", "https://g1.globo.com/rss/g1/"),
        ("Folha", "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"),
    ],
    "world": [
        ("G1", "https://g1.globo.com/rss/g1/mundo/"),
        ("Folha", "https://feeds.folha.uol.com.br/mundo/rss091.xml"),
    ],
    "nation": [
        ("G1", "https://g1.globo.com/rss/g1/brasil/"),
        ("Folha", "https://feeds.folha.uol.com.br/poder/rss091.xml"),
    ],
    "business": [
        ("G1", "https://g1.globo.com/rss/g1/economia/"),
        ("Folha", "https://feeds.folha.uol.com.br/mercado/rss091.xml"),
    ],
    "technology": [
        ("G1", "https://g1.globo.com/rss/g1/tecnologia/"),
        ("Folha", "https://feeds.folha.uol.com.br/tec/rss091.xml"),
    ],
    "entertainment": [
        ("G1", "https://g1.globo.com/rss/g1/pop-arte/"),
        ("Folha", "https://feeds.folha.uol.com.br/ilustrada/rss091.xml"),
    ],
    "sports": [
        ("Folha", "https://feeds.folha.uol.com.br/esporte/rss091.xml"),
    ],
    "science": [
        ("Folha", "https://feeds.folha.uol.com.br/ciencia/rss091.xml"),
    ],
    "health": [
        ("G1", "https://g1.globo.com/rss/g1/ciencia-e-saude/"),
        ("Folha", "https://feeds.folha.uol.com.br/saude/rss091.xml"),
    ],
}


# ---------- Configuração ----------
def carregar_config():
    """Prioriza st.secrets; usa .config/config.json como alternativa local."""
    config = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    try:
        api_key = st.secrets["API_KEY"]
    except Exception:
        api_key = config.get("API_KEY")
    return api_key, int(config.get("MAX_RESULTS", 20))


API_KEY, MAX_RESULTS = carregar_config()


# ---------- Utilidades ----------
def _norm(txt):
    """Minúsculas, sem acentos e sem pontuação (para busca e deduplicação)."""
    txt = unicodedata.normalize("NFKD", txt or "")
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", txt.lower())).strip()


def _dt(publicado_em):
    try:
        return datetime.fromisoformat(publicado_em.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def formatar_data(publicado_em):
    try:
        dt = datetime.fromisoformat(publicado_em.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return publicado_em or "Sem data"


# ---------- Fonte 1: GNews ----------
@st.cache_data(ttl=600, show_spinner="Buscando na GNews...")
def buscar_noticias(pesquisa, lingua, pais, categoria, maximo):
    """Busca na GNews. Erros viram RuntimeError (e não entram no cache)."""
    endpoint = "top-headlines" if categoria else "search"
    params = {"lang": lingua, "max": maximo, "apikey": API_KEY}
    if pesquisa:
        params["q"] = pesquisa
    if pais:
        params["country"] = pais
    if categoria:
        params["category"] = categoria

    try:
        resp = requests.get(f"{GNEWS_URL}/{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("articles", [])
    except requests.exceptions.HTTPError as e:
        mensagens = {
            401: "Chave da API inválida.",
            403: "Limite diário de requisições atingido.",
            429: "Muitas requisições em pouco tempo. Tente novamente em instantes.",
        }
        codigo = e.response.status_code if e.response is not None else None
        raise RuntimeError(mensagens.get(codigo, f"A API retornou erro HTTP {codigo}.")) from None
    except (requests.exceptions.RequestException, ValueError):
        raise RuntimeError("Não foi possível obter notícias agora.") from None


def _de_gnews(a):
    return {
        "title": a.get("title") or "Sem título",
        "description": a.get("description"),
        "url": a.get("url") or "#",
        "image": a.get("image"),
        "publishedAt": a.get("publishedAt"),
        "fonte": (a.get("source") or {}).get("name", "GNews"),
        "via": "GNews",
    }


# ---------- Fonte 2: RSS ----------
def _imagem_entry(e):
    for chave in ("media_content", "media_thumbnail"):
        itens = e.get(chave) or []
        if itens and itens[0].get("url"):
            return itens[0]["url"]
    for link in e.get("links", []):
        if (link.get("type") or "").startswith("image"):
            return link.get("href")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', e.get("summary", "") or "")
    return m.group(1) if m else None


def _limpar_html(txt):
    txt = html.unescape(re.sub(r"<[^>]+>", " ", txt or ""))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:300] + ("…" if len(txt) > 300 else "")


def _baixar_feed(nome, url):
    """Baixa e normaliza um feed. Levanta exceção se falhar."""
    resp = requests.get(url, timeout=8, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    artigos = []
    for e in feed.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        data = datetime(*t[:6], tzinfo=timezone.utc).isoformat() if t else None
        artigos.append({
            "title": (e.get("title") or "Sem título").strip(),
            "description": _limpar_html(e.get("summary")),
            "url": e.get("link") or "#",
            "image": _imagem_entry(e),
            "publishedAt": data,
            "fonte": nome,
            "via": "RSS",
        })
    return artigos


@st.cache_data(ttl=300, show_spinner="Lendo feeds RSS...")
def buscar_rss(pesquisa, categoria, maximo):
    """Lê os feeds em paralelo e filtra pela palavra-chave. Retorna (artigos, nº de falhas)."""
    if categoria:
        feeds = RSS_FEEDS.get(categoria, [])
    else:
        feeds = [f for lista in RSS_FEEDS.values() for f in lista]
    feeds = list(dict.fromkeys(feeds))  # remove repetidos

    artigos, falhas = [], 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futuros = [ex.submit(_baixar_feed, nome, url) for nome, url in feeds]
        for futuro in futuros:
            try:
                artigos.extend(futuro.result())
            except Exception:
                falhas += 1

    palavras = _norm(pesquisa).split()
    if palavras:
        artigos = [
            a for a in artigos
            if all(p in _norm(f"{a['title']} {a['description']}") for p in palavras)
        ]
    artigos.sort(key=lambda a: _dt(a["publishedAt"]), reverse=True)
    return artigos[:maximo], falhas


# ---------- Combinação das fontes ----------
def mesclar(artigos):
    """Ordena por data (mais recente primeiro) e remove duplicados por URL ou título."""
    vistos, saida = set(), []
    for a in sorted(artigos, key=lambda x: _dt(x.get("publishedAt")), reverse=True):
        chaves = {c for c in (a.get("url"), _norm(a.get("title"))) if c}
        if vistos & chaves:
            continue
        vistos |= chaves
        saida.append(a)
    return saida


def coletar(pesquisa, lingua, pais, categoria, fontes, maximo):
    """Busca nas fontes escolhidas. Retorna (artigos mesclados, lista de avisos)."""
    resultados, avisos = [], []

    if "GNews" in fontes:
        if not API_KEY:
            avisos.append("GNews: chave da API não configurada.")
        else:
            try:
                resultados += [_de_gnews(a) for a in buscar_noticias(pesquisa, lingua, pais, categoria, maximo)]
            except RuntimeError as e:
                avisos.append(f"GNews: {e}")

    if "RSS" in fontes:
        artigos, falhas = buscar_rss(pesquisa, categoria, maximo)
        resultados += artigos
        if falhas:
            avisos.append(f"RSS: {falhas} feed(s) não responderam e foram ignorados.")

    return mesclar(resultados)[: maximo * 2], avisos


# ---------- Serviço de CEP ----------
@st.cache_data(ttl=86400, show_spinner="Consultando CEP...")
def consultar_cep(cep):
    """Retorna dict do endereço, ou None se o CEP não existir."""
    try:
        resp = requests.get(VIACEP_URL.format(cep), timeout=10)
        resp.raise_for_status()
        dados = resp.json()
    except (requests.exceptions.RequestException, ValueError):
        raise RuntimeError("Não foi possível consultar o ViaCEP. Tente novamente.") from None
    return None if dados.get("erro") else dados


# ---------- Exibição ----------
def mostrar_artigos(artigos, avisos=()):
    for aviso in avisos:
        st.warning(aviso)
    if not artigos:
        st.info("Nenhuma notícia encontrada!")
        return
    for artigo in artigos:
        with st.container(border=True):
            col_img, col_txt = st.columns([1, 3])
            if artigo.get("image"):
                col_img.image(artigo["image"])
            col_txt.markdown(f"#### [{artigo['title']}]({artigo['url']})")
            col_txt.write(artigo.get("description") or "Sem descrição")
            col_txt.caption(
                f"{artigo['fonte']} • {formatar_data(artigo.get('publishedAt'))} • via {artigo['via']}"
            )


# ---------- Abas ----------
def aba_noticias():
    with st.form("form_noticias"):
        c1, c2 = st.columns([2, 1])
        pesquisa = c1.text_input("O que você está buscando?", placeholder="Ex.: inteligência artificial").strip()
        categoria_nome = c2.selectbox("Categoria", ["Todas as categorias"] + list(CATEGORIAS))
        c3, c4 = st.columns(2)
        lingua_nome = c3.selectbox("Idioma", list(IDIOMAS))
        pais_nome = c4.selectbox("País", list(PAISES))
        fontes_nomes = st.multiselect("Fontes", list(FONTES), default=list(FONTES))
        st.caption("O RSS traz só notícias do Brasil em português; idioma e país valem apenas para a GNews.")
        enviar = st.form_submit_button("🔎 Buscar notícias")

    if not enviar:
        st.info("Digite uma busca ou escolha uma categoria para ver as notícias.")
        return

    categoria = CATEGORIAS.get(categoria_nome)
    fontes = [FONTES[n] for n in fontes_nomes]
    if not fontes:
        st.error("Selecione pelo menos uma fonte.")
        return
    if not pesquisa and not categoria:
        st.error("Por favor, insira uma palavra-chave ou selecione uma categoria.")
        return

    st.subheader(f"Notícias sobre: {pesquisa or 'Manchetes'} · {categoria_nome}")
    artigos, avisos = coletar(pesquisa, IDIOMAS[lingua_nome], PAISES[pais_nome], categoria, fontes, MAX_RESULTS)
    mostrar_artigos(artigos, avisos)


def aba_cep():
    with st.form("form_cep"):
        entrada = st.text_input("CEP", placeholder="01001-000", max_chars=9)
        enviar = st.form_submit_button("📍 Consultar CEP")

    if enviar:
        cep = re.sub(r"\D", "", entrada)  # aceita 01001-000, 01001 000 etc.
        st.session_state.pop("cep_resultado", None)
        if len(cep) != 8:
            st.error("CEP inválido: informe exatamente 8 dígitos.")
            return
        try:
            dados = consultar_cep(cep)
        except RuntimeError as e:
            st.error(str(e))
            return
        if not dados:
            st.warning(f"CEP {cep} não encontrado. Verifique o número digitado.")
            return
        st.session_state["cep_resultado"] = dados

    dados = st.session_state.get("cep_resultado")
    if not dados:
        st.info("Digite um CEP com 8 dígitos para consultar o endereço.")
        return

    cidade, uf = dados.get("localidade", "-"), dados.get("uf", "-")
    st.success(f"CEP {dados.get('cep', '-')} encontrado!")

    c1, c2, c3 = st.columns(3)
    c1.metric("Cidade", cidade)
    c2.metric("Estado", uf)
    c3.metric("DDD", dados.get("ddd") or "-")

    st.write(f"**Endereço:** {dados.get('logradouro') or '-'}")
    st.write(f"**Complemento:** {dados.get('complemento') or '-'}")
    st.write(f"**Bairro:** {dados.get('bairro') or '-'}")

    endereco = ", ".join(filter(None, [dados.get("logradouro"), dados.get("bairro"), cidade, uf, "Brasil"]))
    st.link_button("🗺️ Ver no Google Maps", f"https://www.google.com/maps/search/?api=1&query={quote_plus(endereco)}")

    # Integração: notícias da cidade do CEP, nas duas fontes
    st.divider()
    if st.toggle(f"📰 Mostrar notícias de {cidade}"):
        artigos, avisos = coletar(cidade, "pt", "br", None, ["GNews", "RSS"], 5)
        mostrar_artigos(artigos, avisos)


# ---------- Página ----------
st.markdown(
    """
    <style>
        .hero { padding: 1.4rem 1.6rem; border-radius: 16px; margin-bottom: 1rem;
                background: linear-gradient(135deg, #0033A0, #1e6bff); color: #fff; }
        .hero h1 { margin: 0; font-size: 2rem; color: #fff; }
        .hero p { margin: .25rem 0 0; opacity: .9; }
    </style>
    <div class="hero">
        <h1>🧭 Central de Informações</h1>
        <p>Notícias de duas fontes (GNews + RSS) e consulta de CEP em um só lugar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not API_KEY:
    st.warning("Chave da GNews não encontrada: só o RSS vai funcionar na aba de notícias. "
               "Defina `API_KEY` em st.secrets ou em .config/config.json.")

tab_noticias, tab_cep = st.tabs(["📰 Notícias", "📍 Consulta de CEP"])
with tab_noticias:
    aba_noticias()
with tab_cep:
    aba_cep()

st.divider()
st.caption("Desenvolvido por **Fabiano Navarro** · [LinkedIn](https://www.linkedin.com/in/fabiano-de-navarro)")
