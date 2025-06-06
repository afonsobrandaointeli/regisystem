import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.graph_objects as go
import json
import os

# ----------------------------------------
# 1. Inicialização do Firebase (Firestore)
# ----------------------------------------
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("jey.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

# ----------------------------------------
# 2. Carregamento dos códigos de trimestres
# ----------------------------------------
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

# ----------------------------------------
# 3. Obter lista de alunos (Nome + RA) para dropdown
# ----------------------------------------
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

# ----------------------------------------
# 4. Interface de Seleção de Aluno
# ----------------------------------------
st.title("Relatório de Evolução Trimestral por Aluno")
selecionado = st.selectbox("Selecione o aluno pelo nome:", list(alunos_dict.keys()))
ra_selecionado = alunos_dict[selecionado]

# ----------------------------------------
# 5. Carregar dados do aluno selecionado
# ----------------------------------------
doc_ref = db.collection("alunos").document(ra_selecionado)
doc = doc_ref.get()
if not doc.exists:
    st.error("Documento do aluno não encontrado no Firestore.")
    st.stop()

dados_aluno = doc.to_dict()
st.markdown(f"**Aluno:** {dados_aluno.get('nome')}  \n**RA:** {ra_selecionado}")

# Recupera o mapa de trimestres (pode estar vazio)
trimestres_map = dados_aluno.get("trimestres", {})
if not trimestres_map:
    st.info("Este aluno ainda não possui notas cadastradas em nenhum trimestre.")
    st.stop()

# Ordena os trimestres por chave (alfabeticamente, que no formato 'YYYY-...' respeita a ordem cronológica)
trimestres_ordenados = sorted(trimestres_map.items(), key=lambda x: x[0])

# ----------------------------------------
# 6. Preparar DataFrame para gráfico de linha de cada atributo
# ----------------------------------------
# Lista fixa de métricas, seguindo a ordem esperada
listas_metricas = [
    "Business Drivers",
    "Funcionalidade",
    "Req Não Funcionais",
    "Engenharia",
    "Tecnologia"
]

# Construir um dicionário cujas chaves são as métricas e valores serão listas na ordem dos trimestres
dados_por_met = {met: [] for met in listas_metricas}
lista_trimestres = []  # lista de códigos

for codigo, notas in trimestres_ordenados:
    lista_trimestres.append(codigo)
    for met in listas_metricas:
        # Se por acaso o campo não existir, assume 0
        dados_por_met[met].append(notas.get(met, 0))

# ----------------------------------------
# 7. Construir Gráfico de Radar com Plotly (primeiro)
# ----------------------------------------
st.header("Gráfico de Radar da Evolução")

# Para destacar o último trimestre, definimos:
ultimo_codigo, notas_ultimo = trimestres_ordenados[-1]
# Valores do último trimestre
valores_ultimo = [notas_ultimo.get(m, 0) for m in listas_metricas]

# Monta o gráfico polar
fig_radar = go.Figure()

# Primeiro, traça os trimestres anteriores com baixa opacidade
for codigo, notas in trimestres_ordenados[:-1]:
    valores = [notas.get(m, 0) for m in listas_metricas]
    fig_radar.add_trace(go.Scatterpolar(
        r=valores + [valores[0]],
        theta=listas_metricas + [listas_metricas[0]],
        name=codigo,
        fill='toself',
        opacity=0.3,              # menor opacidade para trimestres antigos
        line=dict(width=1),       # linha fina
    ))

# Agora, traça o último trimestre com destaque (opacidade total e linha mais grossa)
fig_radar.add_trace(go.Scatterpolar(
    r=valores_ultimo + [valores_ultimo[0]],
    theta=listas_metricas + [listas_metricas[0]],
    name=f"{ultimo_codigo} (Último)",
    fill='toself',
    opacity=0.9,                # quase opaco para destacar
    line=dict(width=3, color='red'),  # linha grossa e em vermelho para fácil visualização
))

# Configurações do layout
fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 10])
    ),
    showlegend=True,
    legend=dict(title="Trimestres"),
    title_text="Radar da Evolução Trimestral (último trimestre em destaque)"
)

# Exibe o gráfico de radar
st.plotly_chart(fig_radar, use_container_width=True)

# ----------------------------------------
# 8. Exibir 5 Gráficos de Linha, um para cada métrica (com rótulos rotacionados)
# ----------------------------------------
st.header("Gráficos de Linha por Atributo")

for met in listas_metricas:
    st.subheader(f"{met} ao longo dos trimestres")

    # Cria um Scatter do Plotly para a métrica atual
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

    # Ajusta layout para rotacionar os rótulos do eixo X em 45 graus
    fig_linha.update_layout(
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=10),
            automargin=True
        ),
        yaxis=dict(
            title=met,
            range=[0, 10]
        ),
        margin=dict(l=40, r=20, t=30, b=80),
        height=350,
        showlegend=False
    )

    # Exibe o gráfico usando Plotly
    st.plotly_chart(fig_linha, use_container_width=True)
