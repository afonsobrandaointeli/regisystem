import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import base64
from dotenv import load_dotenv

# ----------------------------------------------------
# Carrega variáveis do .env (incluindo FIREBASE_CREDENTIALS_BASE64)
# ----------------------------------------------------
load_dotenv()  # carrega as variáveis definidas em .env

# ----------------------------------------------------
# Inicialização do Firebase (apenas uma vez)
# ----------------------------------------------------
@st.cache_resource
def init_firestore():
    # 1) Recupera a string Base64 das credenciais
    base64_str = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if not base64_str:
        st.error("A variável FIREBASE_CREDENTIALS_BASE64 não está definida no .env.")
        st.stop()

    # 2) Decodifica Base64 para bytes
    try:
        json_bytes = base64.b64decode(base64_str)
    except Exception as e:
        st.error(f"Erro ao decodificar Base64: {e}")
        st.stop()

    # 3) Converte bytes para string JSON e carrega em dicionário
    try:
        firebase_config = json.loads(json_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        st.error("Erro ao converter os bytes decodificados em JSON. Verifique FIREBASE_CREDENTIALS_BASE64.")
        st.stop()

    # 4) Inicializa apenas se ainda não houver um app criado
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Falha ao inicializar o Firebase: {e}")
            st.stop()

    return firestore.client()

db = init_firestore()

st.title("Buscar, Cadastrar e Editar Aluno")

# -- Inputs de busca --
col1, col2 = st.columns(2)
with col1:
    ra_busca = st.text_input("RA do aluno (ex: 20230001):", key="ra_busca")
with col2:
    nome_busca = st.text_input("Nome completo do aluno:", key="nome_busca")

if st.button("Buscar"):
    ra_busca = ra_busca.strip()
    nome_busca = nome_busca.strip()
    st.session_state.pop("AlunoEncontrado", None)
    st.session_state.pop("RA_Encontrado", None)
    st.session_state.pop("DadosAluno", None)

    # 1) Busca por RA, se informado
    if ra_busca:
        doc_ref = db.collection("alunos").document(ra_busca)
        doc = doc_ref.get()
        if doc.exists:
            st.session_state["AlunoEncontrado"] = True
            st.session_state["RA_Encontrado"] = ra_busca
            st.session_state["DadosAluno"] = doc.to_dict()
            st.success(f"Aluno encontrado por RA: {ra_busca}")
        else:
            st.info(f"Nenhum aluno encontrado com RA {ra_busca}.")
            st.session_state["AlunoEncontrado"] = False
            st.session_state["RA_Encontrado"] = ra_busca

    # 2) Se RA não informado, tenta busca por nome exato
    elif nome_busca:
        query = db.collection("alunos").where("nome", "==", nome_busca).get()
        if not query:
            st.info(f"Nenhum aluno encontrado com nome '{nome_busca}'.")
            st.session_state["AlunoEncontrado"] = False
        elif len(query) == 1:
            doc = query[0]
            ra_encontrado = doc.id
            st.session_state["AlunoEncontrado"] = True
            st.session_state["RA_Encontrado"] = ra_encontrado
            st.session_state["DadosAluno"] = doc.to_dict()
            st.success(f"Aluno encontrado por nome: '{nome_busca}' (RA: {ra_encontrado})")
        else:
            # Se houver múltiplos com mesmo nome, mostra dropdown para escolher
            options = {f"{doc.to_dict().get('nome')} (RA: {doc.id})": doc.id for doc in query}
            escolha = st.selectbox("Foram encontrados vários alunos. Selecione:", list(options.keys()))
            if st.button("Selecionar este aluno"):
                ra_encontrado = options[escolha]
                doc_ref = db.collection("alunos").document(ra_encontrado)
                doc = doc_ref.get()
                st.session_state["AlunoEncontrado"] = True
                st.session_state["RA_Encontrado"] = ra_encontrado
                st.session_state["DadosAluno"] = doc.to_dict()
                st.success(f"Aluno selecionado: {st.session_state['DadosAluno']['nome']} (RA: {ra_encontrado})")
    else:
        st.warning("Por favor, informe o RA ou o nome para buscar.")

# 3) Exibir formulário de cadastro se buscou por RA e não encontrou
if "AlunoEncontrado" in st.session_state and st.session_state["AlunoEncontrado"] is False:
    ra_para_cadastro = st.session_state.get("RA_Encontrado")
    if ra_para_cadastro:
        st.subheader("Cadastrar Novo Aluno")
        st.info(f"RA informado para cadastro: {ra_para_cadastro}")
        nome_novo = st.text_input("Nome completo do aluno para cadastrar este RA:", key="nome_novo_cad")
        if st.button("Cadastrar Aluno"):
            if not nome_novo.strip():
                st.error("Preencha o nome para cadastrar o aluno.")
            else:
                doc_ref = db.collection("alunos").document(ra_para_cadastro)
                doc_ref.set({"nome": nome_novo.strip(), "ra": ra_para_cadastro})
                obter_lista_alunos.clear()  # <-- Limpa o cache aqui!
                st.success(f"Aluno '{nome_novo.strip()}' cadastrado com sucesso!")
                # Atualiza estado para edição imediatamente
                st.session_state["AlunoEncontrado"] = True
                st.session_state["RA_Encontrado"] = ra_para_cadastro
                st.session_state["DadosAluno"] = {"nome": nome_novo.strip(), "ra": ra_para_cadastro}

# 4) Exibir formulário de edição se aluno foi encontrado
if st.session_state.get("AlunoEncontrado"):
    ra_encontrado = st.session_state["RA_Encontrado"]
    dados = st.session_state["DadosAluno"]

    st.subheader("Editar Aluno")
    st.write(f"RA: {ra_encontrado}")
    nome_atual = dados.get("nome", "")
    novo_nome = st.text_input("Nome completo do aluno:", value=nome_atual, key="nome_edicao")

    if st.button("Salvar Alterações", key="btn_salvar_edicao"):
        if not novo_nome.strip():
            st.error("O nome não pode ficar em branco.")
        else:
            doc_ref = db.collection("alunos").document(ra_encontrado)
            doc_ref.update({"nome": novo_nome.strip()})
            st.success(f"Nome do aluno atualizado para '{novo_nome.strip()}'.")
            # Atualiza o estado
            st.session_state["DadosAluno"]["nome"] = novo_nome.strip()
