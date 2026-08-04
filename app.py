r"""
=====================================================================
  APP - SOLICITAÇÃO DE AVALIAÇÃO GEOTÉCNICA  (versão NUVEM / Neon)
  Site (Streamlit) — Geotecnia Operacional, Corredor Norte
  Telas: Início | Dashboard | Cadastramento | Gestão (ADM)
  Banco de dados: PostgreSQL (Neon)  —  dados de TESTE (fictícios)
  Autor: Gledson Silva — Msc. Recursos Hídricos
---------------------------------------------------------------------
  Conexão e senha vêm dos SECRETS (não ficam no código):
    - DB_URL    = string de conexão do Neon (postgresql://...)
    - SENHA_ADM = senha da tela de Gestão
  Local: crie .streamlit/secrets.toml  |  Nuvem: cole nos Secrets do app.
=====================================================================
"""

# ------------------------------------------------------------------ #
# 0. BOOTSTRAP (apenas p/ rodar local; na nuvem é ignorado)
# ------------------------------------------------------------------ #
import os
import sys
import subprocess
import importlib.util


def _sob_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


def _resolver_self():
    try:
        p = os.path.abspath(__file__)
        if os.path.isfile(p):
            return p
    except NameError:
        pass
    for cand in sys.argv:
        if isinstance(cand, str) and cand.lower().endswith(".py") and os.path.isfile(cand):
            return os.path.abspath(cand)
    return "app.py"


def _preparar_streamlit():
    try:
        cfg = os.path.join(os.path.expanduser("~"), ".streamlit")
        os.makedirs(cfg, exist_ok=True)
        cred = os.path.join(cfg, "credentials.toml")
        if not os.path.exists(cred):
            with open(cred, "w", encoding="utf-8") as f:
                f.write('[general]\nemail = ""\n')
    except Exception:
        pass


def _bootstrap():
    _self = _resolver_self()
    necessarios = [("pandas", "pandas"), ("plotly", "plotly"),
                   ("sqlalchemy", "sqlalchemy"), ("psycopg2", "psycopg2-binary"),
                   ("PIL", "pillow"), ("folium", "folium"),
                   ("streamlit_folium", "streamlit-folium"), ("fpdf", "fpdf2"),
                   ("streamlit", "streamlit")]
    faltando = [pip for mod, pip in necessarios if importlib.util.find_spec(mod) is None]
    if faltando:
        print(">> Instalando dependências:", ", ".join(faltando))
        subprocess.call([sys.executable, "-m", "pip", "install", *faltando])
    _preparar_streamlit()
    print(">> Iniciando o site... aguarde, o navegador vai abrir.")
    print("   (se nao abrir, acesse http://localhost:8501 )")
    subprocess.run([sys.executable, "-m", "streamlit", "run", _self, "--server.headless=false"])
    sys.exit(0)


if not _sob_streamlit():
    _bootstrap()

# ------------------------------------------------------------------ #
# 1. IMPORTS / CONFIG
# ------------------------------------------------------------------ #
from datetime import date
import io
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Solicitação de Avaliação Geotécnica",
                   page_icon="📊", layout="wide")

# --- Segredos (conexão e senha) ---
try:
    SENHA_ADM = st.secrets["SENHA_ADM"]
except Exception:
    SENHA_ADM = "01124033289"   # fallback local; o ideal é definir nos Secrets


def _ler_db_url():
    try:
        url = st.secrets["DB_URL"]
    except Exception:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


@st.cache_resource(show_spinner=False)
def get_engine():
    url = _ler_db_url()
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True)


engine = get_engine()

TEAL_D, TEAL, TEAL_L, GOLD, BLUE = "#0A4D49", "#0E6B62", "#15857A", "#F2B705", "#3B5A86"
STATUS_COLORS = {
    "Aprovado": "#15847B", "Aprovado com Ressalva": "#8CCFC7",
    "Cancelado": "#9A9A9A", "Reprovado": "#C0392B",
    "Aguardando avaliação": "#F2B705", "Interdição": "#E8820E",
}
STATUS_ORDER = list(STATUS_COLORS.keys())
STATUS_FALLBACK = "#6B7B78"   # cor neutra p/ status novos criados pelo ADM
MESES = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
         7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}

# Mapa coluna do banco (snake_case)  ->  rótulo usado nas telas
COLMAP = {
    "id": "ID", "data_criacao": "Data de criação", "solicitante": "Solicitante",
    "area_solicitante": "Área do Solicitante", "complexo": "Complexo",
    "tipo_solicitacao": "Tipo de Solicitação", "tipo_estrutura": "Tipo de Estrutura",
    "estrutura": "Estrutura", "localizacao": "Localização da Estrutura",
    "descricao": "Descrição do Evento ou Projeto", "coord_x": "Coordenada X (WGS84)",
    "coord_y": "Coordenada Y (WGS84)", "responsavel": "Responsável pela avaliação",
    "status": "Status", "resultado_avaliacao": "Resultado da avaliação",
    "aprovador": "Aprovador", "data_resposta": "Data da Resposta",
    "comentarios": "Comentários", "plano_acao": "Plano de Ação",
}

LISTAS_DEFAULT = {
    "Área do Solicitante": ["Planejamento curto / Médio prazo", "Usina", "Outros",
        "Terraplenagem N4", "Hidrogeologia", "Operação de Mina Autônoma",
        "Terraplenagem N5", "Geotecnia", "Meio Ambiente", "Operação de Mina N4",
        "Perfuração / Desmonte", "Operação de Mina N5", "Sondagem",
        "Geociências - Topografia"],
    "Complexo": ["Serra Norte", "Serra Leste", "Manganês"],
    "Tipo de Solicitação": ["Inspeção Geotécnica", "Avaliação de Projeto / Plano",
        "Elaboração de Seções", "Entrega de obra"],
    "Tipo de Estrutura": ["Cava", "Usina e Acessos", "Pilha de Estéril", "Pilha de Produto"],
    "Estrutura": ["N4E", "Acessos", "Morro I", "N4WS - CAVA II", "N5E",
        "Cominuição (Britagem)", "N4WS - CAVA III", "N5S", "N4WN - CAVA II",
        "N4WS - CAVA IV", "Estocagem e Exp.", "N4WS - CAVA I", "Classificação",
        "Pellet", "Áreas de apoio", "JACARÉ", "N5W", "SUDESTE", "SUL I", "Usina I",
        "N4EN", "N4EN - CAVA II", "N4WN - CAVA I", "N4WN - CENTRAL", "NORDESTE",
        "Projeto Gelado", "Usina IV", "CENTRAL", "NWII", "PDE MINA 2",
        "Provisórias Mina", "SUL III", "Usina II", "W"],
    "Status": STATUS_ORDER,
    "Responsável pela avaliação": ["Jozias Caetano", "Juliana Oliveira",
        "Paulo Silva Lopes", "Marcelo Alves", "Marcos Araujo", "Guilherme Oriente",
        "Simei Lima", "Ezequias Sousa", "Nayara Pinheiro", "Jonas Silva",
        "Denilson Torres", "Diogo Costa"],
}

if "adm_ok" not in st.session_state:
    st.session_state.adm_ok = False
PAGES = {}

# ------------------------------------------------------------------ #
# 2. ESTILO
# ------------------------------------------------------------------ #
st.markdown(f"""
<style>
  .block-container {{ padding-top: 3rem; padding-bottom: 2rem; max-width: 1300px; }}
  .home-wrap {{ position:relative; border-radius:12px; overflow:hidden; min-height:430px;
    padding:44px 50px;
    background:
      radial-gradient(120% 80% at 80% 10%, rgba(255,255,255,.10), transparent 60%),
      linear-gradient(170deg, {TEAL_L} 0%, {TEAL} 38%, {TEAL_D} 70%, {GOLD} 130%); }}
  .home-wave {{ position:absolute; left:0; right:0; bottom:0; height:120px;
    background: linear-gradient(90deg, rgba(242,183,5,0), rgba(242,183,5,.85) 45%, rgba(255,210,90,.95));
    clip-path: polygon(0 60%,12% 48%,28% 58%,45% 42%,62% 56%,80% 44%,100% 54%,100% 100%,0 100%); }}
  .home-grid {{ position:absolute; inset:0; opacity:.18;
    background-image: linear-gradient(rgba(255,255,255,.25) 1px, transparent 1px);
    background-size:100% 46px; }}
  .home-brand {{ color:#fff; font-size:24px; font-weight:800; letter-spacing:-.5px; margin-bottom:16px; }}
  .home-brand span {{ color:{GOLD}; }}
  .home-title {{ color:{GOLD}; font-size:36px; font-weight:800; line-height:1.08;
    text-shadow:0 1px 6px rgba(0,0,0,.25); margin-bottom:14px; }}
  .home-sub {{ color:{GOLD}; font-size:18px; font-weight:700; margin:2px 0; text-shadow:0 1px 4px rgba(0,0,0,.2); }}
  .home-foot {{ position:absolute; left:50px; bottom:24px; color:#eef; font-size:15px; opacity:.85; }}
  div[data-testid="column"] div.stButton > button {{
    background:{GOLD}; color:{TEAL_D}; font-weight:800; font-size:16px; border:none;
    border-radius:8px; padding:18px 10px; width:100%; box-shadow:0 3px 10px rgba(0,0,0,.18); transition:.15s; }}
  div[data-testid="column"] div.stButton > button:hover {{ background:#ffca2c; color:#000; transform:translateY(-1px); }}
  .st-key-btn_voltar button {{ background:#ffffff; color:{TEAL_D}; border:1px solid {TEAL};
    font-weight:600; font-size:14px; border-radius:8px; padding:6px 16px; width:auto;
    box-shadow:none; }}
  .st-key-btn_voltar button:hover {{ background:{TEAL_L}; color:#ffffff; border-color:{TEAL_L}; }}
  .st-key-btn_voltar button p {{ color:inherit; }}
  .vale-header {{ background: linear-gradient(105deg, {TEAL_D} 0%, {TEAL} 48%, {TEAL_L} 100%);
    border-radius:6px; padding:14px 22px; margin-bottom:10px; display:flex; align-items:center;
    justify-content:space-between; border-bottom:3px solid {GOLD}; }}
  .vale-header .brand {{ color:#fff; font-size:26px; font-weight:800; letter-spacing:-1px; }}
  .vale-header .brand span {{ color:{GOLD}; }}
  .vale-header .titulo {{ color:#fff; font-size:18px; font-weight:800; line-height:1.15; }}
  .vale-header .subtitulo {{ color:rgba(255,255,255,.85); font-size:12px; font-weight:600; letter-spacing:.5px; }}
  .kpi {{ border:2px solid #2b3a3a; border-radius:6px; padding:8px 18px; text-align:center; background:#fff; }}
  .kpi .lbl {{ font-size:13px; font-weight:700; color:#2b3a3a; line-height:1.1; }}
  .kpi .val {{ font-size:34px; font-weight:800; color:#2b3a3a; }}
  h4.painel {{ text-align:center; color:#44524f; font-weight:700; margin:2px 0 6px 0; font-size:16px; }}
</style>
""", unsafe_allow_html=True)


def cabecalho(subtitulo):
    data_atual = pd.Timestamp.today().strftime("%d/%m/%Y")
    st.markdown(f"""
    <div class="vale-header">
      <div style="display:flex; align-items:center; gap:16px;">
        <div class="brand"><span>❯</span>VALE</div>
        <div><div class="titulo">APP - SOLICITAÇÃO DE AVALIAÇÃO GEOTÉCNICA</div>
        <div class="subtitulo">{subtitulo}</div></div>
      </div>
      <div style="color:rgba(255,255,255,.9); font-size:12px; text-align:right;">
        Atualizado em:<br><b>{data_atual}</b></div>
    </div>""", unsafe_allow_html=True)


def botao_inicio():
    if st.button("← Voltar à tela inicial", key="btn_voltar"):
        st.switch_page(PAGES["home"])


# ------------------------------------------------------------------ #
# 3. BANCO DE DADOS (Neon / PostgreSQL)
# ------------------------------------------------------------------ #
def _base_ok():
    if engine is None:
        st.error("Conexão com o banco não configurada. Defina **DB_URL** nos Secrets "
                 "(local: .streamlit/secrets.toml · nuvem: aba Secrets do app).")
        return False
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception as e:
        st.error(f"Não consegui conectar ao banco: {e}")
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar():
    df = pd.read_sql("SELECT * FROM solicitacoes ORDER BY id", engine)
    df = df.rename(columns=COLMAP)
    for col in ["Data de criação", "Data da Resposta"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    dt = df["Data de criação"]
    df["MesNum"] = dt.dt.year * 100 + dt.dt.month
    df["MesAno"] = dt.dt.month.map(MESES) + "/" + dt.dt.year.astype("Int64").astype(str)
    return df


def gravar_nova(reg: dict):
    sql = text("""
        INSERT INTO solicitacoes
        (data_criacao, solicitante, area_solicitante, complexo, tipo_solicitacao,
         tipo_estrutura, estrutura, localizacao, descricao, coord_x, coord_y,
         responsavel, status, resultado_avaliacao, aprovador, data_resposta,
         comentarios, plano_acao)
        VALUES
        (:data_criacao, :solicitante, :area_solicitante, :complexo, :tipo_solicitacao,
         :tipo_estrutura, :estrutura, :localizacao, :descricao, :coord_x, :coord_y,
         :responsavel, :status, :resultado_avaliacao, :aprovador, :data_resposta,
         :comentarios, :plano_acao)
        RETURNING id
    """)
    with engine.begin() as conn:
        return conn.execute(sql, reg).scalar()


def atualizar_demanda(id_alvo, campos: dict):
    sets = ", ".join(f"{k} = :{k}" for k in campos)
    sql = text(f"UPDATE solicitacoes SET {sets} WHERE id = :id_alvo")
    params = dict(campos)
    params["id_alvo"] = int(id_alvo)
    with engine.begin() as conn:
        conn.execute(sql, params)


# ---- Listas de opções (master data editável pelo ADM) ----
LISTAS_GERENCIAVEIS = ["Complexo", "Área do Solicitante", "Tipo de Solicitação",
                       "Tipo de Estrutura", "Estrutura", "Status",
                       "Responsável pela avaliação", "Solicitante"]


@st.cache_data(ttl=60, show_spinner=False)
def carregar_listas():
    """Lê as opções do banco; usa o padrão se a tabela ainda não existir."""
    base = {k: list(v) for k, v in LISTAS_DEFAULT.items()}
    try:
        dl = pd.read_sql("SELECT lista, valor FROM listas_opcoes ORDER BY valor", engine)
        do_banco = {}
        for _, r in dl.iterrows():
            do_banco.setdefault(r["lista"], []).append(r["valor"])
        for k, v in do_banco.items():
            if v:
                base[k] = v
    except Exception:
        pass
    base.setdefault("Solicitante", [])
    return base


def lista_add(lista, valor):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO listas_opcoes (lista, valor) VALUES (:l, :v) "
            "ON CONFLICT (lista, valor) DO NOTHING"), {"l": lista, "v": valor})


def lista_add(lista, valor, grupo=None, complexo=None):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO listas_opcoes (lista, valor, grupo, complexo) "
            "VALUES (:l, :v, :g, :c) ON CONFLICT (lista, valor) DO NOTHING"),
            {"l": lista, "v": valor, "g": grupo, "c": complexo})


def lista_del(lista, valor):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM listas_opcoes WHERE lista = :l AND valor = :v"),
                     {"l": lista, "v": valor})


@st.cache_data(ttl=60, show_spinner=False)
def estruturas_por_tipo():
    """Retorna {tipo_de_estrutura: [estruturas]} e as não classificadas em '(sem tipo)'."""
    try:
        df = pd.read_sql("SELECT valor, grupo FROM listas_opcoes "
                         "WHERE lista = 'Estrutura' ORDER BY valor", engine)
        d = {}
        for _, r in df.iterrows():
            chave = r["grupo"] if pd.notna(r["grupo"]) and r["grupo"] else "(sem tipo)"
            d.setdefault(chave, []).append(r["valor"])
        return d
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def estruturas_meta():
    """Estruturas com seu Tipo (grupo) e Complexo. Colunas: valor, grupo, complexo."""
    try:
        return pd.read_sql("SELECT valor, grupo, complexo FROM listas_opcoes "
                           "WHERE lista = 'Estrutura' ORDER BY valor", engine)
    except Exception:
        return pd.DataFrame(columns=["valor", "grupo", "complexo"])


def estrutura_set_tipo(valor, grupo):
    with engine.begin() as conn:
        conn.execute(text("UPDATE listas_opcoes SET grupo = :g "
                          "WHERE lista = 'Estrutura' AND valor = :v"),
                     {"g": grupo, "v": valor})


def estrutura_set_meta(valor, grupo, complexo):
    with engine.begin() as conn:
        conn.execute(text("UPDATE listas_opcoes SET grupo = :g, complexo = :c "
                          "WHERE lista = 'Estrutura' AND valor = :v"),
                     {"g": grupo, "c": complexo, "v": valor})


# ---- Anexos de fotos (armazenados no próprio banco) ----
MAX_FOTOS = 5
MAX_BYTES_FOTO = 1_000_000        # 1 MB por foto (após compressão)
MAX_BYTES_TOTAL = 5_000_000       # 5 MB por solicitação
MAX_LADO_PX = 1920                # maior lado da imagem


def comprimir_imagem(file_bytes):
    """Redimensiona (máx. 1920px) e comprime em JPEG mirando <= 1 MB.
    Se necessário, reduz a dimensão progressivamente para respeitar o teto.
    Retorna bytes JPEG ou levanta exceção se a imagem não puder ser processada."""
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)            # respeita orientação da câmera
    if img.mode != "RGB":
        img = img.convert("RGB")

    def _redimensionar(im, lado):
        w, h = im.size
        if max(w, h) <= lado:
            return im
        if w >= h:
            return im.resize((lado, max(1, round(h * lado / w))), Image.LANCZOS)
        return im.resize((max(1, round(w * lado / h)), lado), Image.LANCZOS)

    lado, dados = MAX_LADO_PX, None
    for _ in range(6):
        base = _redimensionar(img, lado)
        for q in (85, 82, 80, 78, 75, 70, 65, 60):
            buf = io.BytesIO()
            base.save(buf, format="JPEG", quality=q, optimize=True)
            dados = buf.getvalue()
            if len(dados) <= MAX_BYTES_FOTO:
                return dados
        lado = int(lado * 0.82)                    # reduz a dimensão e tenta de novo
        if lado < 800:
            break
    return dados                                   # caso extremo: menor tamanho obtido


def salvar_anexo(solic_id, nome, dados):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO anexos (solicitacao_id, nome, mime, tamanho, imagem) "
            "VALUES (:s, :n, :m, :t, :img)"),
            {"s": int(solic_id), "n": nome, "m": "image/jpeg",
             "t": len(dados), "img": dados})


def anexos_da(solic_id):
    return pd.read_sql(text("SELECT id, nome, tamanho, imagem FROM anexos "
                            "WHERE solicitacao_id = :s ORDER BY id"),
                       engine, params={"s": int(solic_id)})


def contar_anexos(df):
    """Retorna dict {solicitacao_id: qtd} para exibir nas listagens."""
    try:
        c = pd.read_sql("SELECT solicitacao_id, COUNT(*) AS n FROM anexos "
                        "GROUP BY solicitacao_id", engine)
        return dict(zip(c["solicitacao_id"], c["n"]))
    except Exception:
        return {}


def excluir_anexo(anexo_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anexos WHERE id = :i"), {"i": int(anexo_id)})


def excluir_demanda(id_alvo):
    # os anexos saem junto (ON DELETE CASCADE); apagamos explicitamente por garantia
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anexos WHERE solicitacao_id = :i"), {"i": int(id_alvo)})
        conn.execute(text("DELETE FROM solicitacoes WHERE id = :i"), {"i": int(id_alvo)})


def _txt(s):
    """Sanitiza texto para o PDF (fontes core usam latin-1)."""
    if s is None:
        return "-"
    return str(s).encode("latin-1", "replace").decode("latin-1")


def gerar_pdf(linha, fotos_df):
    """Monta um relatório PDF do chamado com dados, coordenadas e fotos."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    NX, NY = XPos.LMARGIN, YPos.NEXT
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Cabeçalho VALE
    pdf.set_fill_color(14, 77, 73)
    pdf.rect(0, 0, 210, 24, "F")
    pdf.set_xy(10, 6)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 6, _txt("VALE - Solicitacao de Avaliacao Geotecnica"), new_x=NX, new_y=NY)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _txt("Geotecnia Operacional - Corredor Norte"), new_x=NX, new_y=NY)
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _txt(f"Chamado ID {linha['ID']}  -  Status: {linha['Status']}"),
             new_x=NX, new_y=NY)
    pdf.ln(2)

    def campo(rotulo, valor):
        y0 = pdf.get_y()
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(235, 240, 239)
        pdf.cell(55, 7, _txt(rotulo), border=0, fill=True,
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(65, y0)
        pdf.multi_cell(135, 7, _txt(valor), border=0, new_x=NX, new_y=NY)

    def _data(v):
        try:
            return v.strftime("%d/%m/%Y")
        except Exception:
            return "-" if v is None else str(v)

    campo("Data de criacao", _data(linha.get("Data de criação")))
    campo("Solicitante", linha.get("Solicitante"))
    campo("Area do Solicitante", linha.get("Área do Solicitante"))
    campo("Complexo", linha.get("Complexo"))
    campo("Tipo de Solicitacao", linha.get("Tipo de Solicitação"))
    campo("Tipo de Estrutura", linha.get("Tipo de Estrutura"))
    campo("Estrutura", linha.get("Estrutura"))
    campo("Localizacao", linha.get("Localização da Estrutura"))
    cx, cy = linha.get("Coordenada X (WGS84)"), linha.get("Coordenada Y (WGS84)")
    coord = "-"
    if cx not in (None, "") and cy not in (None, "") and not (pd.isna(cx) or pd.isna(cy)):
        coord = f"Lat {cx:.6f} , Lon {cy:.6f}"
    campo("Coordenadas (X=Lat, Y=Lon)", coord)
    campo("Descricao do Evento/Projeto", linha.get("Descrição do Evento ou Projeto"))
    campo("Responsavel pela avaliacao", linha.get("Responsável pela avaliação"))
    campo("Resultado da avaliacao", linha.get("Resultado da avaliação"))
    campo("Aprovador", linha.get("Aprovador"))
    campo("Data da Resposta", _data(linha.get("Data da Resposta")))
    campo("Comentarios", linha.get("Comentários"))
    campo("Plano de Acao", linha.get("Plano de Ação"))

    # Fotos
    if fotos_df is not None and not fotos_df.empty:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _txt(f"Fotos anexadas ({len(fotos_df)})"), new_x=NX, new_y=NY)
        for _, r in fotos_df.iterrows():
            try:
                img = io.BytesIO(bytes(r["imagem"]))
                if pdf.get_y() > 240:
                    pdf.add_page()
                pdf.image(img, w=120)
                pdf.set_font("Helvetica", "I", 8)
                pdf.cell(0, 5, _txt(f"{r['nome']} ({r['tamanho']/1000:.0f} KB)"),
                         new_x=NX, new_y=NY)
                pdf.ln(2)
            except Exception:
                pdf.set_font("Helvetica", "I", 8)
                pdf.cell(0, 5, _txt(f"[falha ao inserir {r['nome']}]"), new_x=NX, new_y=NY)

    return bytes(pdf.output())


# ================================================================== #
#  PÁGINA: HOME
# ================================================================== #
def pg_home():
    st.markdown(f"""
    <div class="home-wrap">
      <div class="home-grid"></div>
      <div class="home-brand"><span>❯</span> VALE</div>
      <div class="home-title">APP SOLICITAÇÃO DE<br>AVALIAÇÃO GEOTÉCNICA</div>
      <div class="home-sub">Geotecnia Operacional SN, SL e Mn</div>
      <div class="home-sub">Corredor Norte</div>
      <div class="home-foot">Controle Interno · Acesso Restrito</div>
      <div class="home-wave"></div>
    </div>""", unsafe_allow_html=True)
    st.write("")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("📊 Dashboard", use_container_width=True):
            st.switch_page(PAGES["dashboard"])
    with b2:
        if st.button("📝 Cadastramento de Demandas", use_container_width=True):
            st.switch_page(PAGES["cadastro"])
    with b3:
        if st.button("🔒 Gestão de Demandas (ADM)", use_container_width=True):
            st.switch_page(PAGES["gestao"])


# ================================================================== #
#  PÁGINA: CADASTRAMENTO
# ================================================================== #
def pg_cadastro():
    botao_inicio()
    cabecalho("CADASTRAMENTO DE DEMANDAS")
    if not _base_ok():
        return
    st.caption("O ID é gerado automaticamente pelo banco de dados. Campos com * são obrigatórios.")
    ok = st.session_state.pop("cad_ok", None)
    if ok:
        st.success("✅ Solicitação registrada com sucesso!")
        det = (f"**Protocolo (ID): {ok['id']}** · Solicitante: {ok['solic']} · "
               f"Status inicial: **Aguardando avaliação**.")
        if ok["fotos"]:
            det += f" · {ok['fotos']} foto(s) anexada(s) ({ok['mb']:.1f} MB)."
        st.info(det + "\n\nA solicitação está registrada e disponível para a equipe de "
                "Geotecnia avaliar. Acompanhe o andamento pela tela de Gestão.")
        st.balloons()
    LIS = carregar_listas()

    def campo_outros(label, chave, opcoes):
        """Selectbox com opção 'Outros'; ao escolher, libera um campo para digitar."""
        lst = list(opcoes)
        if "Outros" not in lst:
            lst = lst + ["Outros"]
        sel = st.selectbox(f"{label} *", ["(selecione)"] + lst, key=f"cad_sel_{chave}")
        if sel == "Outros":
            return st.text_input(f"↳ Especifique {label.lower()}", key=f"cad_out_{chave}").strip()
        return "" if sel == "(selecione)" else sel

    c1, c2 = st.columns(2)
    with c1:
        # Solicitante: lista + opção de novo nome (entra na lista ao cadastrar)
        sol_opts = ["(selecione)"] + LIS.get("Solicitante", []) + ["Outros (novo)"]
        sol_sel = st.selectbox("Solicitante *", sol_opts, key="cad_sel_sol")
        if sol_sel == "Outros (novo)":
            solicitante = st.text_input("↳ Nome do novo solicitante", key="cad_out_sol").strip()
            solicitante_novo = bool(solicitante)
        else:
            solicitante = "" if sol_sel == "(selecione)" else sol_sel
            solicitante_novo = False
        complexo = campo_outros("Complexo", "complexo", LIS["Complexo"])
        tipo_estrutura = campo_outros("Tipo de Estrutura", "testrut", LIS["Tipo de Estrutura"])
        localizacao = st.text_area("Localização da Estrutura", height=90, key="cad_loc")
    with c2:
        area = campo_outros("Área do Solicitante", "area", LIS["Área do Solicitante"])
        tipo_solic = campo_outros("Tipo de Solicitação", "tsolic", LIS["Tipo de Solicitação"])
        # Estrutura filtrada por Complexo + Tipo de Estrutura (evita erro de cadastro)
        dfm = estruturas_meta()
        if dfm.empty:
            classificadas, nao_class = dfm, dfm
        else:
            mask = (dfm["grupo"].notna() & (dfm["grupo"].astype(str) != "") &
                    dfm["complexo"].notna() & (dfm["complexo"].astype(str) != ""))
            classificadas, nao_class = dfm[mask], dfm[~mask]
        if not (complexo and tipo_estrutura):
            st.selectbox("Estrutura *", ["(selecione Complexo e Tipo de Estrutura primeiro)"],
                         disabled=True, key="cad_sel_estrut_ph")
            estrutura = ""
        else:
            if not classificadas.empty:
                match = classificadas[(classificadas["complexo"] == complexo) &
                                      (classificadas["grupo"] == tipo_estrutura)]
                ops_estrut = list(match["valor"]) + list(nao_class["valor"])
            else:
                ops_estrut = list(nao_class["valor"])
            estrutura = campo_outros("Estrutura", "estrut", ops_estrut)
            if not nao_class.empty:
                st.caption(f"⚠️ {len(nao_class)} estrutura(s) ainda sem Tipo/Complexo definido "
                           f"aparecem em todos. Classifique-as em Gestão (ADM).")
        descricao = st.text_area("Descrição do Evento ou Projeto", height=90, key="cad_desc")

    # ---- Coordenadas (com mapa interativo opcional) ----
    st.markdown("**Coordenadas (WGS84)** — clique no mapa ou digite manualmente")
    st.session_state.setdefault("cad_x", 0.0)
    st.session_state.setdefault("cad_y", 0.0)
    with st.expander("📍 Selecionar coordenadas no mapa (clique no ponto)"):
        try:
            import folium
            from streamlit_folium import st_folium
            lat0 = st.session_state.cad_x or -6.05
            lon0 = st.session_state.cad_y or -50.16
            m = folium.Map(location=[lat0, lon0], zoom_start=13,
                           control_scale=True, tiles=None)
            # Camada padrão: satélite (Esri World Imagery)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
                      "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri, Maxar, Earthstar Geographics",
                name="Satélite", overlay=False, control=True).add_to(m)
            # Camada alternativa: mapa de ruas
            folium.TileLayer("OpenStreetMap", name="Mapa de ruas",
                             overlay=False, control=True).add_to(m)
            folium.LayerControl(collapsed=False).add_to(m)
            if st.session_state.cad_x and st.session_state.cad_y:
                folium.Marker([st.session_state.cad_x, st.session_state.cad_y],
                              tooltip="Ponto selecionado").add_to(m)
            md = st_folium(m, height=350, width=725, key="cad_map")
            if md and md.get("last_clicked"):
                st.session_state.cad_x = round(md["last_clicked"]["lat"], 6)
                st.session_state.cad_y = round(md["last_clicked"]["lng"], 6)
            st.caption("Convenção do app: X = Latitude · Y = Longitude. "
                       "Use o seletor no canto do mapa para alternar Satélite / Ruas.")
        except Exception:
            st.info("Mapa indisponível agora — digite as coordenadas manualmente abaixo.")
    cc1, cc2 = st.columns(2)
    coord_x = cc1.number_input("Coordenada X (Latitude)", format="%.6f", key="cad_x")
    coord_y = cc2.number_input("Coordenada Y (Longitude)", format="%.6f", key="cad_y")

    # ---- Anexos de fotos ----
    st.markdown(f"**Anexos — fotos da inspeção** · até {MAX_FOTOS} fotos, "
                f"{MAX_BYTES_FOTO//1_000_000} MB por foto e "
                f"{MAX_BYTES_TOTAL//1_000_000} MB no total (comprimidas automaticamente)")
    fotos = st.file_uploader("Selecionar fotos (JPG/PNG)", type=["jpg", "jpeg", "png"],
                             accept_multiple_files=True, key="cad_fotos")
    if fotos and len(fotos) > MAX_FOTOS:
        st.warning(f"Você selecionou {len(fotos)} fotos; o máximo é {MAX_FOTOS}. "
                   f"Apenas as {MAX_FOTOS} primeiras serão anexadas.")

    st.caption("Obs.: o solicitante deverá acompanhar em campo as tratativas com o "
               "geotécnico responsável.")
    enviar = st.button("ENVIAR SOLICITAÇÃO", type="primary", use_container_width=True)

    if enviar:
        obrig = [("Solicitante", solicitante), ("Complexo", complexo),
                 ("Área do Solicitante", area), ("Tipo de Solicitação", tipo_solic),
                 ("Tipo de Estrutura", tipo_estrutura), ("Estrutura", estrutura)]
        faltando = [nome for nome, val in obrig if not val]
        if faltando:
            st.error("Preencha os campos obrigatórios: " + ", ".join(faltando) + ".")
        else:
            # Processa/comprime as fotos ANTES de gravar (evita registro órfão)
            processadas, total, erro = [], 0, None
            fotos_lim = (fotos or [])[:MAX_FOTOS]
            if fotos_lim:
                pb = st.progress(0.0, text="Processando fotos...")
                for i, f in enumerate(fotos_lim):
                    try:
                        dados = comprimir_imagem(f.getvalue())
                    except Exception:
                        erro = f"Não foi possível processar a imagem '{f.name}'."
                        break
                    total += len(dados)
                    processadas.append((f.name, dados))
                    pb.progress((i + 1) / len(fotos_lim),
                                text=f"Processando foto {i + 1}/{len(fotos_lim)}...")
                pb.empty()
            if erro:
                st.error(erro + " Remova essa imagem e tente novamente.")
            elif total > MAX_BYTES_TOTAL:
                st.error(f"O total das fotos ficou em {total/1_000_000:.1f} MB, acima do "
                         f"limite de {MAX_BYTES_TOTAL//1_000_000} MB. Remova alguma foto.")
            else:
                reg = {"data_criacao": date.today(), "solicitante": solicitante,
                       "area_solicitante": area, "complexo": complexo,
                       "tipo_solicitacao": tipo_solic, "tipo_estrutura": tipo_estrutura,
                       "estrutura": estrutura, "localizacao": (localizacao or "").strip(),
                       "descricao": (descricao or "").strip(),
                       "coord_x": coord_x or None, "coord_y": coord_y or None,
                       "responsavel": None, "status": "Aguardando avaliação",
                       "resultado_avaliacao": None, "aprovador": None,
                       "data_resposta": None, "comentarios": None, "plano_acao": None}
                try:
                    novo_id = gravar_nova(reg)
                    for nome, dados in processadas:
                        salvar_anexo(novo_id, nome, dados)
                    if solicitante_novo and solicitante not in LIS.get("Solicitante", []):
                        try:
                            lista_add("Solicitante", solicitante)
                        except Exception:
                            pass
                    st.cache_data.clear()
                    st.session_state["cad_ok"] = {
                        "id": novo_id, "fotos": len(processadas),
                        "mb": total / 1_000_000, "solic": solicitante}
                    for k in ["cad_sel_sol", "cad_out_sol", "cad_sel_complexo", "cad_out_complexo",
                              "cad_sel_area", "cad_out_area", "cad_sel_tsolic", "cad_out_tsolic",
                              "cad_sel_testrut", "cad_out_testrut", "cad_sel_estrut", "cad_out_estrut",
                              "cad_loc", "cad_desc", "cad_fotos", "cad_x", "cad_y"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    st.divider()
    st.markdown("##### Últimas solicitações cadastradas")
    u = carregar().sort_values("ID", ascending=False).head(8)
    qtd = contar_anexos(u)
    cu = [c for c in ["ID", "Data de criação", "Solicitante", "Complexo",
                      "Tipo de Estrutura", "Estrutura", "Status"] if c in u.columns]
    u = u[cu].copy()
    u["Data de criação"] = u["Data de criação"].dt.strftime("%d/%m/%Y")
    u["Fotos"] = u["ID"].map(lambda i: qtd.get(i, 0))
    st.dataframe(u, use_container_width=True, hide_index=True)


# ================================================================== #
#  PÁGINA: GESTÃO (ADM)
# ================================================================== #
def pg_gestao():
    botao_inicio()
    cabecalho("GESTÃO DE DEMANDAS — ACESSO RESTRITO (ADM)")
    if not _base_ok():
        return
    if not st.session_state.adm_ok:
        st.info("Área restrita. Informe a senha de administrador.")
        senha = st.text_input("Senha do ADM", type="password")
        if st.button("Entrar"):
            if senha == SENHA_ADM:
                st.session_state.adm_ok = True
            else:
                st.error("Senha incorreta.")
        if not st.session_state.adm_ok:
            return
    ctop = st.columns([4, 1])
    ctop[1].button("Sair do ADM", on_click=lambda: st.session_state.update(adm_ok=False))
    df = carregar().sort_values("ID")
    ids = df["ID"].dropna().astype(int).tolist()
    if not ids:
        st.info("Não há demandas cadastradas ainda.")
        return
    alvo = st.selectbox("Selecione a demanda (ID)", ids,
                        format_func=lambda i: f"ID {i} — "
                        f"{df.loc[df['ID']==i,'Solicitante'].values[0]} · "
                        f"{df.loc[df['ID']==i,'Estrutura'].values[0]}")
    linha = df[df["ID"] == alvo].iloc[0]
    st.markdown("**Resumo da solicitação**")
    st.dataframe(pd.DataFrame({
        "Campo": ["Solicitante", "Complexo", "Tipo de Estrutura", "Estrutura",
                  "Tipo de Solicitação", "Descrição"],
        "Valor": [linha["Solicitante"], linha["Complexo"], linha["Tipo de Estrutura"],
                  linha["Estrutura"], linha["Tipo de Solicitação"],
                  linha["Descrição do Evento ou Projeto"]],
    }), use_container_width=True, hide_index=True)

    # Coordenadas + mini-mapa de satélite (para quem avalia ver o local)
    cx, cy = linha.get("Coordenada X (WGS84)"), linha.get("Coordenada Y (WGS84)")
    tem_coord = (cx not in (None, "") and cy not in (None, "")
                 and not (pd.isna(cx) or pd.isna(cy)) and (cx or cy))
    st.markdown("**Localização (coordenadas WGS84)**")
    if tem_coord:
        st.write(f"X (Latitude): `{cx:.6f}`  ·  Y (Longitude): `{cy:.6f}`")
        try:
            import folium
            from streamlit_folium import st_folium
            mm = folium.Map(location=[cx, cy], zoom_start=14, control_scale=True, tiles=None)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
                      "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri, Maxar, Earthstar Geographics",
                name="Satélite", control=True).add_to(mm)
            folium.TileLayer("OpenStreetMap", name="Mapa de ruas", control=True).add_to(mm)
            folium.LayerControl(collapsed=True).add_to(mm)
            folium.CircleMarker([cx, cy], radius=9, color="#C0392B", weight=3,
                                fill=True, fill_color="#C0392B", fill_opacity=0.9,
                                tooltip="Local da solicitação").add_to(mm)
            st_folium(mm, height=320, width=725, key=f"map_gestao_{alvo}")
        except Exception:
            st.info("Mini-mapa indisponível no momento. As coordenadas estão acima.")
    else:
        st.caption("Esta solicitação não possui coordenadas cadastradas.")

    # Fotos anexadas a esta demanda
    fotos_df = anexos_da(alvo)
    st.markdown(f"**Fotos anexadas ({len(fotos_df)})**")
    if fotos_df.empty:
        st.caption("Nenhuma foto anexada a esta solicitação.")
    else:
        gcols = st.columns(min(len(fotos_df), 5))
        for i, (_, r) in enumerate(fotos_df.iterrows()):
            with gcols[i % 5]:
                st.image(bytes(r["imagem"]),
                         caption=f"{r['nome']} ({r['tamanho']/1000:.0f} KB)",
                         use_container_width=True)
                if st.button("🗑️ Excluir foto", key=f"delfoto_{r['id']}", use_container_width=True):
                    try:
                        excluir_anexo(int(r["id"]))
                        st.cache_data.clear()
                        st.success("Foto excluída.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir foto: {e}")

    # Exportar relatório do chamado em PDF
    try:
        pdf_bytes = gerar_pdf(linha, fotos_df)
        st.download_button("📄 Exportar relatório do chamado (PDF)", data=pdf_bytes,
                           file_name=f"chamado_{alvo}.pdf", mime="application/pdf",
                           use_container_width=True, key=f"pdf_{alvo}")
    except Exception as e:
        st.caption(f"Não foi possível gerar o PDF agora: {e}")

    def _idx(lista, valor, extra0=None):
        opts = ([extra0] if extra0 is not None else []) + lista
        v = "" if pd.isna(valor) else str(valor)
        return opts, (opts.index(v) if v in opts else 0)

    LIS = carregar_listas()
    with st.form("form_gestao"):
        st.markdown("###### Atualizar avaliação")
        g1, g2 = st.columns(2)
        with g1:
            op_st, ix_st = _idx(LIS.get("Status", STATUS_ORDER), linha["Status"])
            novo_status = st.selectbox("Status", op_st, index=ix_st)
            op_rp, ix_rp = _idx(LIS["Responsável pela avaliação"],
                                linha["Responsável pela avaliação"], extra0="(a definir)")
            novo_resp = st.selectbox("Responsável pela avaliação", op_rp, index=ix_rp)
            aprovador = st.text_input("Aprovador",
                value="" if pd.isna(linha["Aprovador"]) else str(linha["Aprovador"]))
        with g2:
            resultado = st.text_area("Resultado da avaliação", height=90,
                value="" if pd.isna(linha["Resultado da avaliação"]) else str(linha["Resultado da avaliação"]))
            data_resp = st.date_input("Data da Resposta",
                value=linha["Data da Resposta"].date() if pd.notna(linha["Data da Resposta"]) else date.today())
        comentarios = st.text_area("Comentários", height=80,
            value="" if pd.isna(linha["Comentários"]) else str(linha["Comentários"]))
        plano = st.text_area("Plano de Ação", height=80,
            value="" if pd.isna(linha["Plano de Ação"]) else str(linha["Plano de Ação"]))
        salvar = st.form_submit_button("SALVAR ALTERAÇÕES", type="primary", use_container_width=True)
    if salvar:
        campos = {"status": novo_status,
                  "responsavel": None if novo_resp == "(a definir)" else novo_resp,
                  "aprovador": aprovador.strip() or None,
                  "resultado_avaliacao": resultado.strip() or None,
                  "data_resposta": data_resp,
                  "comentarios": comentarios.strip() or None,
                  "plano_acao": plano.strip() or None}
        try:
            atualizar_demanda(int(alvo), campos)
            st.cache_data.clear()
            st.success(f"Demanda ID {alvo} atualizada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # ---------------- Excluir solicitação ----------------
    st.divider()
    with st.expander("🗑️ Excluir esta solicitação (ação irreversível)"):
        st.warning(f"Isto apaga permanentemente a solicitação ID {alvo} "
                   f"e todas as fotos anexadas a ela.")
        conf = st.checkbox("Confirmo que desejo excluir esta solicitação.", key="conf_del_sol")
        if st.button("Excluir definitivamente", type="primary",
                     disabled=not conf, key="btn_del_sol", use_container_width=True):
            try:
                excluir_demanda(int(alvo))
                st.cache_data.clear()
                st.session_state.pop("conf_del_sol", None)
                st.success(f"Solicitação ID {alvo} excluída com sucesso.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

    # ---------------- Gerenciar listas de opções ----------------
    st.divider()
    with st.expander("⚙️ Gerenciar listas de opções (adicionar / excluir)"):
        st.caption("As alterações refletem nos menus de Cadastramento e Gestão. "
                   "Excluir uma opção da lista não altera as solicitações já registradas.")
        LIS_G = carregar_listas()
        nome_lista = st.selectbox("Escolha a lista", LISTAS_GERENCIAVEIS, key="sel_lista_g")
        valores = LIS_G.get(nome_lista, [])
        eh_estrutura = (nome_lista == "Estrutura")
        st.markdown(f"**Opções atuais de _{nome_lista}_ — {len(valores)} item(ns):**")

        if eh_estrutura:
            # Vínculo Estrutura -> Tipo + Complexo (classificação editável)
            tipos_estr = LIS_G.get("Tipo de Estrutura", [])
            complexos = LIS_G.get("Complexo", [])
            dfm = estruturas_meta()
            if not dfm.empty:
                dfc = pd.DataFrame({
                    "Estrutura": dfm["valor"],
                    "Tipo de Estrutura": dfm["grupo"].fillna(""),
                    "Complexo": dfm["complexo"].fillna("")}).reset_index(drop=True)
            else:
                dfc = pd.DataFrame({"Estrutura": [], "Tipo de Estrutura": [], "Complexo": []})
            st.caption("Defina o Tipo e o Complexo de cada Estrutura. No Cadastramento, ao escolher "
                       "Complexo + Tipo, só aparecem as estruturas que batem com os dois.")
            editado = st.data_editor(
                dfc, use_container_width=True, hide_index=True, height=320, key="editor_estrut",
                column_config={
                    "Estrutura": st.column_config.TextColumn("Estrutura", disabled=True),
                    "Tipo de Estrutura": st.column_config.SelectboxColumn(
                        "Tipo de Estrutura", options=tipos_estr),
                    "Complexo": st.column_config.SelectboxColumn(
                        "Complexo", options=complexos)})
            if st.button("💾 Salvar Tipo/Complexo das estruturas",
                         use_container_width=True, key="btn_save_tipos"):
                try:
                    ant = {r["Estrutura"]: (r["Tipo de Estrutura"], r["Complexo"])
                           for _, r in dfc.iterrows()}
                    for _, r in editado.iterrows():
                        nt = (r["Tipo de Estrutura"] or "").strip()
                        nc = (r["Complexo"] or "").strip()
                        if ant.get(r["Estrutura"], ("", "")) != (nt, nc):
                            estrutura_set_meta(r["Estrutura"], nt or None, nc or None)
                    st.cache_data.clear()
                    st.success("Tipo/Complexo das estruturas atualizados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
        elif valores:
            st.dataframe(pd.DataFrame({nome_lista: valores}),
                         use_container_width=True, hide_index=True, height=220)
        else:
            st.info("Esta lista ainda não possui opções cadastradas.")

        ca, cb = st.columns(2)
        with ca:
            novo_v = st.text_input("Adicionar nova opção", key="add_opt_g")
            tipo_novo = complexo_novo = None
            if eh_estrutura:
                tipo_novo = st.selectbox("Tipo desta estrutura",
                                         ["(selecione)"] + LIS_G.get("Tipo de Estrutura", []),
                                         key="add_tipo_estrut")
                complexo_novo = st.selectbox("Complexo desta estrutura",
                                             ["(selecione)"] + LIS_G.get("Complexo", []),
                                             key="add_complexo_estrut")
            if st.button("➕ Adicionar", use_container_width=True, key="btn_add_g"):
                v = novo_v.strip()
                if not v:
                    st.warning("Digite um valor para adicionar.")
                elif v in valores:
                    st.warning("Essa opção já existe na lista.")
                elif eh_estrutura and (not tipo_novo or tipo_novo == "(selecione)"
                                       or not complexo_novo or complexo_novo == "(selecione)"):
                    st.warning("Selecione o Tipo e o Complexo desta estrutura.")
                else:
                    try:
                        lista_add(nome_lista, v,
                                  grupo=(tipo_novo if eh_estrutura else None),
                                  complexo=(complexo_novo if eh_estrutura else None))
                        st.cache_data.clear()
                        st.success(f"'{v}' adicionado a {nome_lista}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {e}")
        with cb:
            if valores:
                rem_v = st.selectbox("Excluir opção", ["(selecione)"] + valores, key="del_opt_g")
                if st.button("🗑️ Excluir", use_container_width=True, key="btn_del_g"):
                    if rem_v == "(selecione)":
                        st.warning("Selecione uma opção para excluir.")
                    else:
                        try:
                            lista_del(nome_lista, rem_v)
                            st.cache_data.clear()
                            st.success(f"'{rem_v}' excluído de {nome_lista}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")


# ================================================================== #
#  PÁGINA: DASHBOARD
# ================================================================== #
def pg_dashboard():
    botao_inicio()
    cabecalho("GEOTECNIA OPERACIONAL - CORREDOR NORTE")
    if not _base_ok():
        return
    dados = carregar()
    if dados.empty:
        st.info("Banco sem registros. Cadastre demandas para ver os gráficos.")
        return

    def opcoes(col):
        return ["Todos"] + list(map(str, sorted([v for v in dados[col].dropna().unique()])))

    f1, f2, f3, f4, f5, f6 = st.columns(6)
    sel = {"Tipo de Estrutura": f1.selectbox("Tipo de Estrutura", opcoes("Tipo de Estrutura")),
           "Complexo": f2.selectbox("Complexo", opcoes("Complexo")),
           "Estrutura": f3.selectbox("Estrutura", opcoes("Estrutura")),
           "Status": f4.selectbox("Status", opcoes("Status")),
           "Solicitante": f5.selectbox("Solicitante", opcoes("Solicitante")),
           "Responsável pela avaliação": f6.selectbox("Responsável pela avaliação", opcoes("Responsável pela avaliação"))}
    dmin, dmax = dados["Data de criação"].min(), dados["Data de criação"].max()
    periodo = st.date_input("Período (Data de criação)", value=(dmin.date(), dmax.date()),
                            min_value=dmin.date(), max_value=dmax.date())
    df = dados.copy()
    for col, val in sel.items():
        if val != "Todos":
            df = df[df[col].astype(str) == val]
    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        df = df[(df["Data de criação"] >= pd.Timestamp(periodo[0])) &
                (df["Data de criação"] <= pd.Timestamp(periodo[1]))]

    k1, k2 = st.columns([1, 5])
    with k1:
        st.markdown(f'<div class="kpi"><div class="lbl">Total de<br>Solicitações</div>'
                    f'<div class="val">{len(df)}</div></div>', unsafe_allow_html=True)
    with k2:
        st.caption("Fonte: Banco Neon (PostgreSQL) · os filtros refletem em todos os gráficos.")
    if df.empty:
        st.info("Nenhum registro para os filtros selecionados.")
        return

    # Ordem e cores de Status — dinâmicas (inclui status novos criados pelo ADM)
    _LIS = carregar_listas()
    STAT_ORD = list(_LIS.get("Status") or STATUS_ORDER)
    for _s in dados["Status"].dropna().unique():
        if _s not in STAT_ORD:
            STAT_ORD.append(_s)
    SMAP = {s: STATUS_COLORS.get(s, STATUS_FALLBACK) for s in STAT_ORD}

    LAYOUT = dict(margin=dict(l=10, r=10, t=10, b=10),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  legend=dict(orientation="h", yanchor="top", y=-0.32, x=0.5,
                              xanchor="center", font=dict(size=10, color="#d6dedb"),
                              title=dict(text="")),
                  font=dict(size=11, color="#d6dedb"))
    # eixos: rótulos claros e reserva de espaço automática (evita corte/sobreposição)
    TICK = dict(tickfont=dict(size=10, color="#cdd6d3"), automargin=True)

    def painel(t): st.markdown(f'<h4 class="painel">{t}</h4>', unsafe_allow_html=True)

    def g_status(d):
        c = d["Status"].value_counts().reindex(STAT_ORD).dropna().reset_index()
        c.columns = ["Status", "qtd"]
        fig = px.bar(c, x="Status", y="qtd", text="qtd", color="Status", color_discrete_map=SMAP)
        fig.update_traces(textposition="outside", showlegend=False, cliponaxis=False)
        fig.update_layout(**LAYOUT, xaxis_title=None, yaxis_title=None, height=320)
        fig.update_yaxes(visible=False)
        fig.update_xaxes(tickangle=-25, **TICK)
        return fig

    def g_emp(d, col, horizontal=False, height=340, ordem_x=None):
        g = d.groupby([col, "Status"]).size().reset_index(name="qtd")
        if horizontal:
            tot = g.groupby(col)["qtd"].sum().sort_values().index.tolist()
            fig = px.bar(g, y=col, x="qtd", color="Status", orientation="h",
                         color_discrete_map=SMAP,
                         category_orders={col: tot, "Status": STAT_ORD})
            fig.update_xaxes(visible=False)
            fig.update_yaxes(**TICK)
        else:
            fig = px.bar(g, x=col, y="qtd", color="Status", color_discrete_map=SMAP,
                         category_orders={col: ordem_x or sorted(g[col].unique()), "Status": STAT_ORD})
            fig.update_yaxes(visible=False)
            fig.update_xaxes(tickangle=-45, **TICK)
        fig.update_layout(**LAYOUT, height=height, barmode="stack", xaxis_title=None, yaxis_title=None)
        return fig

    def g_cont(d, col, height=320):
        c = d[col].value_counts().reset_index(); c.columns = [col, "qtd"]
        c = c.sort_values("qtd", ascending=False)
        fig = px.bar(c, x=col, y="qtd", text="qtd")
        fig.update_traces(marker_color=BLUE, textposition="outside", cliponaxis=False)
        fig.update_layout(**LAYOUT, height=height, xaxis_title=None, yaxis_title=None, showlegend=False)
        fig.update_yaxes(visible=False)
        fig.update_xaxes(tickangle=-45, **TICK)
        return fig

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True): painel("Status das Solicitações"); st.plotly_chart(g_status(df), use_container_width=True)
    with c2:
        with st.container(border=True):
            painel("Solicitações por mês")
            ordem = df[["MesAno", "MesNum"]].drop_duplicates().sort_values("MesNum")["MesAno"].tolist()
            st.plotly_chart(g_emp(df, "MesAno", ordem_x=ordem), use_container_width=True)
    with c3:
        with st.container(border=True):
            painel("Responsável pela avaliação"); st.plotly_chart(g_emp(df, "Responsável pela avaliação", horizontal=True), use_container_width=True)
    c4, c5 = st.columns(2)
    with c4:
        with st.container(border=True): painel("Solicitações por Solicitante"); st.plotly_chart(g_emp(df, "Solicitante", horizontal=True, height=380), use_container_width=True)
    with c5:
        with st.container(border=True): painel("Solicitações por Área"); st.plotly_chart(g_emp(df, "Área do Solicitante", horizontal=True, height=380), use_container_width=True)
    c6, c7 = st.columns(2)
    with c6:
        with st.container(border=True): painel("Solicitações por Tipo de Estrutura"); st.plotly_chart(g_cont(df, "Tipo de Estrutura"), use_container_width=True)
    with c7:
        with st.container(border=True): painel("Tipo de Solicitação"); st.plotly_chart(g_cont(df, "Tipo de Solicitação"), use_container_width=True)
    with st.container(border=True): painel("Solicitações por Estrutura"); st.plotly_chart(g_cont(df, "Estrutura", height=360), use_container_width=True)
    with st.container(border=True):
        painel("Detalhamento das Solicitações")
        cd = [c for c in ["ID", "Solicitante", "Área do Solicitante", "Tipo de Solicitação",
              "Tipo de Estrutura", "Estrutura", "Data de criação",
              "Descrição do Evento ou Projeto", "Status"] if c in df.columns]
        t = df[cd].copy(); t["Data de criação"] = t["Data de criação"].dt.strftime("%d/%m/%Y")
        st.dataframe(t, use_container_width=True, hide_index=True, height=360)


# ------------------------------------------------------------------ #
# 4. NAVEGAÇÃO
# ------------------------------------------------------------------ #
home = st.Page(pg_home, title="Início", icon="🏠", default=True)
dash = st.Page(pg_dashboard, title="Dashboard", icon="📊")
cad = st.Page(pg_cadastro, title="Cadastramento", icon="📝")
ges = st.Page(pg_gestao, title="Gestão (ADM)", icon="🔒")
PAGES.update(home=home, dashboard=dash, cadastro=cad, gestao=ges)

st.navigation([home, dash, cad, ges]).run()
