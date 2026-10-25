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
AWESOME_URL = "https://economia.awesomeapi.com.br/json/last"
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

# Moedas do conversor (sempre cotadas contra o real)
MOEDAS = {
    "USD": "Dólar americano", "EUR": "Euro", "GBP": "Libra esterlina",
    "ARS": "Peso argentino", "BTC": "Bitcoin",
}

# Feeds RSS por categoria: (nome do portal, URL).
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


# ---------- Configuração via st.secrets ----------
def carregar_config():
    """Lê as configurações exclusivamente dos Secrets do Streamlit."""
    try:
        api_key = st.secrets["API_KEY"]
    except Exception:
        api_key = None

    # Opcional: chave gratuita da AwesomeAPI (evita limites e cache nas cotações)
    try:
        awesome_key = st.secrets["AWESOMEAPI_KEY"]
    except Exception:
        awesome_key = None

    try:
        max_results = int(st.secrets.get("MAX_RESULTS", 20))
    except Exception:
        max_results = 20

    return api_key, awesome_key, max_results


API_KEY, AWESOME_KEY, MAX_RESULTS = carregar_config()


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


def fmt_num(valor, casas=2):
    """Formata no padrão brasileiro: 1.234,56"""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_brl(valor):
    return "R$ " + fmt_num(valor, 2 if valor >= 1 else 4)


# ---------- Fonte 1: GNews ----------
@st.cache_data(ttl=600, show_spinner="Buscando na GNews...")
def buscar_noticias(pesquisa, lingua, pais, categoria, maximo):
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
    if categoria:
        feeds = RSS_FEEDS.get(categoria, [])
    else:
        feeds = [f for lista in RSS_FEEDS.values() for f in lista]
    feeds = list(dict.fromkeys(feeds))

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
    vistos, saida = set(), []
    for a in sorted(artigos, key=lambda x: _dt(x.get("publishedAt")), reverse=True):
        chaves = {c for c in (a.get("url"), _norm(a.get("title"))) if c}
        if vistos & chaves:
            continue
        vistos |= chaves
        saida.append(a)
    return saida


def coletar(pesquisa, lingua, pais, categoria, fontes, maximo):
    resultados, avisos = [], []

    if "GNews" in fontes:
        if not API_KEY:
            avisos.append("GNews: chave da API não configurada nos Secrets.")
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
    try:
        resp = requests.get(VIACEP_URL.format(cep), timeout=10)
        resp.raise_for_status()
        dados = resp.json()
    except (requests.exceptions.RequestException, ValueError):
        raise RuntimeError("Não foi possível consultar o ViaCEP. Tente novamente.") from None
    return None if dados.get("erro") else dados


# ---------- Serviço de Cotações ----------
@st.cache_data(ttl=300, show_spinner="Buscando cotações...")
def obter_cotacoes():
    """
    Busca as cotações na AwesomeAPI. Falhas levantam RuntimeError, que o
    st.cache_data NÃO guarda (antes, um erro virava None e ficava em cache por 30 min).
    """
    pares = ",".join(f"{m}-BRL" for m in MOEDAS)
    headers = {"User-Agent": USER_AGENT}
    if AWESOME_KEY:
        headers["x-api-key"] = AWESOME_KEY

    try:
        resp = requests.get(f"{AWESOME_URL}/{pares}", headers=headers, timeout=10)
        resp.raise_for_status()
        dados = resp.json()
    except requests.exceptions.HTTPError as e:
        codigo = e.response.status_code if e.response is not None else "?"
        dicas = {
            404: "Alguma moeda da lista não foi encontrada.",
            429: "Limite de requisições atingido. Cadastre uma chave gratuita (AWESOMEAPI_KEY).",
        }
        raise RuntimeError(f"AwesomeAPI retornou erro HTTP {codigo}. {dicas.get(codigo, '')}".strip()) from None
    except (requests.exceptions.RequestException, ValueError):
        raise RuntimeError("Não foi possível conectar à AwesomeAPI.") from None

    if not isinstance(dados, dict) or not any(f"{m}BRL" in dados for m in MOEDAS):
        raise RuntimeError("Resposta inesperada da AwesomeAPI.")
    return dados


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
        cep = re.sub(r"\D", "", entrada)
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

    st.divider()
    if st.toggle(f"📰 Mostrar notícias de {cidade}"):
        artigos, avisos = coletar(cidade, "pt", "br", None, ["GNews", "RSS"], 5)
        mostrar_artigos(artigos, avisos)


def aba_conversor():
    st.subheader("💱 Cotações e Conversor de Moedas")

    try:
        dados = obter_cotacoes()
    except RuntimeError as e:
        st.error(f"Não foi possível carregar as cotações. {e}")
        return

    # Converte o JSON em {moeda: {"taxa": ..., "var": ...}}, ignorando itens incompletos
    cotacoes = {}
    for moeda in MOEDAS:
        item = dados.get(f"{moeda}BRL")
        try:
            cotacoes[moeda] = {"taxa": float(item["bid"]), "var": float(item["pctChange"])}
        except (KeyError, TypeError, ValueError):
            continue

    if not cotacoes:
        st.error("As cotações vieram em um formato inesperado. Tente novamente mais tarde.")
        return

    cols = st.columns(len(cotacoes))
    for col, (moeda, c) in zip(cols, cotacoes.items()):
        col.metric(MOEDAS[moeda], fmt_brl(c["taxa"]), f"{c['var']:+.2f}%".replace(".", ","))

    atualizado = next((dados[k].get("create_date") for k in dados if dados[k].get("create_date")), None)
    if atualizado:
        st.caption(f"Última atualização da fonte: {atualizado} · valores de compra (bid) · cache de até 5 min")

    st.divider()
    st.write("### Calculadora de conversão")
    c1, c2, c3 = st.columns(3)
    valor = c1.number_input("Valor", min_value=0.0, value=100.0, step=10.0)
    moeda = c2.selectbox("Moeda", list(cotacoes), format_func=lambda m: f"{MOEDAS[m]} ({m})")
    sentido = c3.radio("Sentido", ["Moeda → Real", "Real → Moeda"], horizontal=True)

    taxa = cotacoes[moeda]["taxa"]
    casas = 8 if moeda == "BTC" else 2
    if sentido == "Moeda → Real":
        st.success(f"{fmt_num(valor)} {moeda} equivalem a **{fmt_brl(valor * taxa)}**")
    else:
        st.success(f"{fmt_brl(valor)} equivalem a **{fmt_num(valor / taxa, casas)} {moeda}**")


# ---------- Página Principal ----------
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
        <p>Notícias (GNews + RSS), Consulta de CEP e Conversor de Moedas em um só lugar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not API_KEY:
    st.warning("Chave da GNews não encontrada nos Secrets: só o RSS vai funcionar na aba de notícias.")

tab_noticias, tab_cep, tab_conversor = st.tabs(["📰 Notícias", "📍 Consulta de CEP", "💱 Conversor de Moedas"])

with tab_noticias:
    aba_noticias()
with tab_cep:
    aba_cep()
with tab_conversor:
    aba_conversor()

st.divider()
st.caption("Desenvolvido por **Fabiano Navarro** · [LinkedIn](https://www.linkedin.com/in/fabiano-de-navarro)")
