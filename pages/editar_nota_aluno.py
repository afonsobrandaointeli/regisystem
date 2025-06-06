import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializa o Firebase apenas uma vez
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("jey.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

st.title("Editar Notas de Trimestre")

# 1. Função para obter lista de alunos (nome + RA) para dropdown
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
    st.warning("Não há alunos cadastrados.")
    st.stop()

selecionado_aluno = st.selectbox("Selecione o aluno pelo nome:", list(alunos_dict.keys()))
ra_selecionado = alunos_dict[selecionado_aluno]

# 2. Carrega dados do aluno selecionado
doc_ref = db.collection("alunos").document(ra_selecionado)
doc = doc_ref.get()
if not doc.exists:
    st.error("Documento do aluno não encontrado. Verifique o cadastro.")
    st.stop()

dados_aluno = doc.to_dict()
st.markdown(f"**Aluno selecionado:** {dados_aluno.get('nome')}  \n**RA:** {ra_selecionado}")

trimestres = dados_aluno.get("trimestres", {})
if not trimestres:
    st.info("Este aluno ainda não possui notas cadastradas.")
    st.stop()

# 3. Dropdown para selecionar qual trimestre editar
codigo_existentes = list(trimestres.keys())
codigo_existentes.sort()  # ordena alfabeticamente ou cronologicamente pelos códigos
codigo_selecionado = st.selectbox("Selecione o código do trimestre a editar:", codigo_existentes)

# 4. Carrega valores atuais daquele trimestre
notas_atuais = trimestres.get(codigo_selecionado, {})
bd_atual = notas_atuais.get("Business Drivers", 0)
func_atual = notas_atuais.get("Funcionalidade", 0)
rnf_atual = notas_atuais.get("Req Não Funcionais", 0)
eng_atual = notas_atuais.get("Engenharia", 0)
tec_atual = notas_atuais.get("Tecnologia", 0)

st.subheader(f"Notas atuais para {codigo_selecionado}")
col1, col2 = st.columns(2)
with col1:
    st.write(f"• Business Drivers: **{bd_atual}**")
    st.write(f"• Funcionalidade: **{func_atual}**")
    st.write(f"• Req. Não Funcionais: **{rnf_atual}**")
with col2:
    st.write(f"• Engenharia: **{eng_atual}**")
    st.write(f"• Tecnologia: **{tec_atual}**")

st.markdown("---")
st.subheader(f"Editar valores para {codigo_selecionado}")

# 5. Exibe sliders pré-preenchidos para permitir alteração
bd_novo = st.slider("Business Drivers", 0, 10, bd_atual, step=1)
func_novo = st.slider("Funcionalidade", 0, 10, func_atual, step=1)
rnf_novo = st.slider("Req. Não Funcionais", 0, 10, rnf_atual, step=1)
eng_novo = st.slider("Engenharia", 0, 10, eng_atual, step=1)
tec_novo = st.slider("Tecnologia", 0, 10, tec_atual, step=1)

if st.button("Salvar Atualizações"):
    notas_atualizadas = {
        "Business Drivers": bd_novo,
        "Funcionalidade": func_novo,
        "Req Não Funcionais": rnf_novo,
        "Engenharia": eng_novo,
        "Tecnologia": tec_novo
    }
    # Atualiza somente aquele subcampo dentro de "trimestres"
    doc_ref.update({
        f"trimestres.{codigo_selecionado}.Business Drivers": bd_novo,
        f"trimestres.{codigo_selecionado}.Funcionalidade": func_novo,
        f"trimestres.{codigo_selecionado}.Req Não Funcionais": rnf_novo,
        f"trimestres.{codigo_selecionado}.Engenharia": eng_novo,
        f"trimestres.{codigo_selecionado}.Tecnologia": tec_novo
    })
    st.success(f"Notas do {codigo_selecionado} atualizadas para {dados_aluno.get('nome')}.")
    st.rerun()
