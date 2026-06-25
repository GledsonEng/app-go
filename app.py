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

LISTAS = {
    "Área do Solicitante": ["Planejamento curto / Médio prazo", "Usina", "Outros",
        "Terraplenagem N4", "Hidrogeologia", "Operação de Mina Autônoma",
        "Terraplenagem N5", "Geotecnia", "Meio Ambiente", "Operação de Mina N4",
        "Perfuração / Desmonte", "Operação de Mina N5", "Sondagem",
        "Geociências - Topografia"],
    "Complexo": ["Serra Norte", "Serra Leste", "Mn"],
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
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1300px; }}
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
    if st.button("← Voltar à tela inicial"):
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
    st.caption("O ID é gerado automaticamente pelo banco de dados.")
    with st.form("form_cad", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            solicitante = st.text_input("Solicitante *")
            complexo = st.selectbox("Complexo *", LISTAS["Complexo"])
            tipo_estrutura = st.selectbox("Tipo de Estrutura *", LISTAS["Tipo de Estrutura"])
            localizacao = st.text_area("Localização da Estrutura", height=90)
            coord_x = st.number_input("Coordenada X (WGS84)", format="%.6f", value=0.0)
        with c2:
            area = st.selectbox("Área do Solicitante *", LISTAS["Área do Solicitante"])
            tipo_solic = st.selectbox("Tipo de Solicitação *", LISTAS["Tipo de Solicitação"])
            estrutura = st.selectbox("Estrutura *", LISTAS["Estrutura"])
            descricao = st.text_area("Descrição do Evento ou Projeto", height=90)
            coord_y = st.number_input("Coordenada Y (WGS84)", format="%.6f", value=0.0)
        st.caption("Obs.: o solicitante deverá acompanhar em campo as tratativas com o "
                   "geotécnico responsável. Telefone da Geomecânica: (94) 99944-2667.")
        enviar = st.form_submit_button("ENVIAR SOLICITAÇÃO", type="primary", use_container_width=True)
    if enviar:
        if not solicitante.strip():
            st.error("Informe o Solicitante.")
        else:
            reg = {"data_criacao": date.today(), "solicitante": solicitante.strip(),
                   "area_solicitante": area, "complexo": complexo,
                   "tipo_solicitacao": tipo_solic, "tipo_estrutura": tipo_estrutura,
                   "estrutura": estrutura, "localizacao": localizacao.strip(),
                   "descricao": descricao.strip(),
                   "coord_x": coord_x or None, "coord_y": coord_y or None,
                   "responsavel": None, "status": "Aguardando avaliação",
                   "resultado_avaliacao": None, "aprovador": None,
                   "data_resposta": None, "comentarios": None, "plano_acao": None}
            try:
                novo_id = gravar_nova(reg)
                st.cache_data.clear()
                st.success(f"Solicitação cadastrada com sucesso! ID gerado: {novo_id}")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
    st.divider()
    st.markdown("##### Últimas solicitações cadastradas")
    u = carregar().sort_values("ID", ascending=False).head(8)
    cu = [c for c in ["ID", "Data de criação", "Solicitante", "Complexo",
                      "Tipo de Estrutura", "Estrutura", "Status"] if c in u.columns]
    u = u[cu].copy()
    u["Data de criação"] = u["Data de criação"].dt.strftime("%d/%m/%Y")
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

    def _idx(lista, valor, extra0=None):
        opts = ([extra0] if extra0 is not None else []) + lista
        v = "" if pd.isna(valor) else str(valor)
        return opts, (opts.index(v) if v in opts else 0)

    with st.form("form_gestao"):
        st.markdown("###### Atualizar avaliação")
        g1, g2 = st.columns(2)
        with g1:
            op_st, ix_st = _idx(STATUS_ORDER, linha["Status"])
            novo_status = st.selectbox("Status", op_st, index=ix_st)
            op_rp, ix_rp = _idx(LISTAS["Responsável pela avaliação"],
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
           "Responsável pela avaliação": f6.selectbox("Responsável", opcoes("Responsável pela avaliação"))}
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

    LAYOUT = dict(margin=dict(l=10, r=10, t=10, b=10),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0, font=dict(size=10)),
                  font=dict(size=11, color="#333"))

    def painel(t): st.markdown(f'<h4 class="painel">{t}</h4>', unsafe_allow_html=True)

    def g_status(d):
        c = d["Status"].value_counts().reindex(STATUS_ORDER).dropna().reset_index()
        c.columns = ["Status", "qtd"]
        fig = px.bar(c, x="Status", y="qtd", text="qtd", color="Status", color_discrete_map=STATUS_COLORS)
        fig.update_traces(textposition="outside", showlegend=False)
        fig.update_layout(**LAYOUT, xaxis_title=None, yaxis_title=None, height=300)
        fig.update_yaxes(visible=False); fig.update_xaxes(tickangle=-30); return fig

    def g_emp(d, col, horizontal=False, height=320, ordem_x=None):
        g = d.groupby([col, "Status"]).size().reset_index(name="qtd")
        if horizontal:
            tot = g.groupby(col)["qtd"].sum().sort_values().index.tolist()
            fig = px.bar(g, y=col, x="qtd", color="Status", orientation="h",
                         color_discrete_map=STATUS_COLORS,
                         category_orders={col: tot, "Status": STATUS_ORDER})
            fig.update_xaxes(visible=False)
        else:
            fig = px.bar(g, x=col, y="qtd", color="Status", color_discrete_map=STATUS_COLORS,
                         category_orders={col: ordem_x or sorted(g[col].unique()), "Status": STATUS_ORDER})
            fig.update_yaxes(visible=False)
        fig.update_layout(**LAYOUT, height=height, barmode="stack", xaxis_title=None, yaxis_title=None)
        return fig

    def g_cont(d, col, height=300):
        c = d[col].value_counts().reset_index(); c.columns = [col, "qtd"]
        c = c.sort_values("qtd", ascending=False)
        fig = px.bar(c, x=col, y="qtd", text="qtd")
        fig.update_traces(marker_color=BLUE, textposition="outside")
        fig.update_layout(**LAYOUT, height=height, xaxis_title=None, yaxis_title=None, showlegend=False)
        fig.update_yaxes(visible=False); fig.update_xaxes(tickangle=-45); return fig

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
