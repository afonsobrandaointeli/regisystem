import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# Inicializa o Firebase uma única vez
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("jey.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

st.title("Adicionar Notas de Trimestre")

# 1. Carrega os códigos de trimestre a partir de turmas.json
@st.cache_data
def carregar_codigos_de_turmas():
    caminho_arquivo = os.path.join(os.getcwd(), "turmas.json")
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("codigos_trimestres", [])
    except FileNotFoundError:
        st.error(f"Arquivo turmas.json não encontrado em: {caminho_arquivo}")
        return []
    except json.JSONDecodeError:
        st.error("Erro ao decodificar o JSON. Verifique se o turmas.json está bem formatado.")
        return []

todos_codigos = carregar_codigos_de_turmas()
if not todos_codigos:
    st.warning("Nenhum código de trimestre carregado de turmas.json.")
    st.stop()

# 2. Busca todos os alunos para popular o dropdown
@st.cache_data
def obter_lista_alunos():
    alunos = db.collection("alunos").stream()
    mapeamento = {}
    for doc in alunos:
        dados = doc.to_dict()
        nome = dados.get("nome", "")
        ra = doc.id
        mapeamento[f"{nome} (RA: {ra})"] = ra
    return mapeamento

alunos_dict = obter_lista_alunos()
if not alunos_dict:
    st.warning("Não há nenhum aluno cadastrado.")
    st.stop()

selecionado = st.selectbox("Selecione o aluno pelo nome:", list(alunos_dict.keys()))
ra_selecionado = alunos_dict[selecionado]

# 3. Obtém dados do aluno selecionado
doc_ref = db.collection("alunos").document(ra_selecionado)
doc = doc_ref.get()
dados_aluno = doc.to_dict() if doc.exists else {"nome": "", "trimestres": {}}

st.markdown(f"**Aluno selecionado:** {dados_aluno.get('nome', '')}  \n**RA:** {ra_selecionado}")

# 4. Filtra trimestres ainda não cadastrados para esse aluno
trimestres_existentes = list(dados_aluno.get("trimestres", {}).keys())
opcoes_disponiveis = [c for c in todos_codigos if c not in trimestres_existentes]

if not opcoes_disponiveis:
    st.warning("Não há trimestres disponíveis para adicionar (todos já cadastrados).")
    st.stop()

codigo_trimestre = st.selectbox("Selecione o código do trimestre a ser cadastrado:", opcoes_disponiveis)

st.subheader(f"Notas para o trimestre {codigo_trimestre}")
bd = st.slider("Business Drivers", 0, 10, 0, step=1)
func = st.slider("Funcionalidade", 0, 10, 0, step=1)
rnf = st.slider("Req. Não Funcionais", 0, 10, 0, step=1)
eng = st.slider("Engenharia", 0, 10, 0, step=1)
tec = st.slider("Tecnologia", 0, 10, 0, step=1)

if st.button("Salvar Notas"):
    notas_dict = {
        "Business Drivers": bd,
        "Funcionalidade": func,
        "Req Não Funcionais": rnf,
        "Engenharia": eng,
        "Tecnologia": tec
    }
    # Grava no Firestore usando merge para não sobrescrever outros trimestres
    doc_ref.set(
        {
            "trimestres": {
                codigo_trimestre: {
                    **notas_dict,
                    "dataAval": firestore.SERVER_TIMESTAMP
                }
            }
        },
        merge=True,
    )
    st.success(f"Notas do {codigo_trimestre} salvas para {dados_aluno.get('nome')}.")
    st.rerun()
