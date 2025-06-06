import streamlit as st

st.set_page_config(page_title="Relatório Trimestral", layout="wide")

# ---- Demais imports ----
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.graph_objects as go
import json
import os
import base64
from dotenv import load_dotenv


# ----------------------------------------------------
# 1. Carregar variáveis de ambiente
# ----------------------------------------------------
load_dotenv()

# ----------------------------------------------------
# 2. Inicialização do Firebase (Firestore) via Base64
# ----------------------------------------------------
@st.cache_resource
def init_firestore():
    base64_str = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if not base64_str:
        st.error("A variável FIREBASE_CREDENTIALS_BASE64 não está definida no .env.")
        st.stop()

    try:
        json_bytes = base64.b64decode(base64_str)
        firebase_config = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        st.error(f"Erro ao processar as credenciais do Firebase: {e}")
        st.stop()

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Falha ao inicializar o Firebase: {e}")
        st.stop()

    return firestore.client()

db = init_firestore()

# ----------------------------------------------------
# 3. Carregamento dos códigos de trimestres
# ----------------------------------------------------
@st.cache_data
def carregar_codigos_trimestres():
    caminho = os.path.join(os.getcwd(), "turmas.json")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("codigos_trimestres", [])
    except FileNotFoundError:
        st.error(f"Arquivo 'turmas.json' não encontrado em: {caminho}")
        return []
    except json.JSONDecodeError:
        st.error("Erro ao decodificar 'turmas.json'. Verifique o formato JSON.")
        return []

todos_codigos = carregar_codigos_trimestres()
if not todos_codigos:
    st.warning("Nenhum código de trimestre foi carregado de 'turmas.json'.")
    st.stop()

# ----------------------------------------------------
# 4. Obter lista de alunos (Nome + RA) para dropdown
# ----------------------------------------------------
@st.cache_data
def obter_lista_alunos():
    alunos_stream = db.collection("alunos").stream()
    mapeamento = {}
    for doc in alunos_stream:
        dados = doc.to_dict()
        nome = dados.get("nome", "")
        ra = doc.id
        mapeamento[f"{nome} (RA: {ra})"] = ra
    return mapeamento

alunos_dict = obter_lista_alunos()
if not alunos_dict:
    st.warning("Não há nenhum aluno cadastrado no Firestore.")
    st.stop()

# ----------------------------------------------------
# 5. Interface de Seleção de Aluno
# ----------------------------------------------------
st.title("📊 Relatório de Evolução Trimestral por Aluno")
selecionado = st.selectbox("Selecione o aluno pelo nome:", list(alunos_dict.keys()))
ra_selecionado = alunos_dict[selecionado]

# ----------------------------------------------------
# 6. Carregar dados do aluno selecionado
# ----------------------------------------------------
doc_ref = db.collection("alunos").document(ra_selecionado)
doc = doc_ref.get()
if not doc.exists:
    st.error("Documento do aluno não encontrado no Firestore.")
    st.stop()

dados_aluno = doc.to_dict()
st.markdown(f"**Aluno:** {dados_aluno.get('nome')}  \n**RA:** {ra_selecionado}")

trimestres_map = dados_aluno.get("trimestres", {})
if not trimestres_map:
    st.info("Este aluno ainda não possui notas cadastradas em nenhum trimestre.")
    st.stop()

trimestres_ordenados = sorted(trimestres_map.items(), key=lambda x: x[0])

# ----------------------------------------------------
# 7. Preparar dados para gráficos
# ----------------------------------------------------
listas_metricas = [
    "Business Drivers",
    "Funcionalidade",
    "Req Não Funcionais",
    "Engenharia",
    "Tecnologia"
]

dados_por_met = {met: [] for met in listas_metricas}
lista_trimestres = []

for codigo, notas in trimestres_ordenados:
    lista_trimestres.append(codigo)
    for met in listas_metricas:
        dados_por_met[met].append(notas.get(met, 0))

# ----------------------------------------------------
# 8. Construir Gráfico de Radar
# ----------------------------------------------------
st.header("📌 Gráfico de Radar da Evolução")

ultimo_codigo, notas_ultimo = trimestres_ordenados[-1]
valores_ultimo = [notas_ultimo.get(m, 0) for m in listas_metricas]

fig_radar = go.Figure()

for codigo, notas in trimestres_ordenados[:-1]:
    valores = [notas.get(m, 0) for m in listas_metricas]
    fig_radar.add_trace(go.Scatterpolar(
        r=valores + [valores[0]],
        theta=listas_metricas + [listas_metricas[0]],
        name=codigo,
        fill='toself',
        opacity=0.3,
        line=dict(width=1),
    ))

fig_radar.add_trace(go.Scatterpolar(
    r=valores_ultimo + [valores_ultimo[0]],
    theta=listas_metricas + [listas_metricas[0]],
    name=f"{ultimo_codigo} (Último)",
    fill='toself',
    opacity=0.9,
    line=dict(width=3, color='red'),
))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
    showlegend=True,
    legend=dict(title="Trimestres"),
    title_text="Radar da Evolução Trimestral (último trimestre em destaque)"
)

st.plotly_chart(fig_radar, use_container_width=True)

# ----------------------------------------------------
# 9. Gráficos de Linha por Atributo
# ----------------------------------------------------
st.header("📈 Gráficos de Linha por Atributo")

for met in listas_metricas:
    st.subheader(f"{met} ao longo dos trimestres")
    fig_linha = go.Figure(
        data=go.Scatter(
            x=lista_trimestres,
            y=dados_por_met[met],
            mode='lines+markers',
            name=met,
            line=dict(width=2),
            marker=dict(size=6)
        )
    )

    fig_linha.update_layout(
        xaxis=dict(tickangle=45, tickfont=dict(size=10), automargin=True),
        yaxis=dict(title=met, range=[0, 10]),
        margin=dict(l=40, r=20, t=30, b=80),
        height=350,
        showlegend=False
    )

    st.plotly_chart(fig_linha, use_container_width=True)
