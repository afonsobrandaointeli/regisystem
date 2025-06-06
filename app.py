import streamlit as st
st.set_page_config(page_title="Sistema de Notas", layout="wide")  # PRIMEIRA INSTRUÇÃO

import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import base64
from dotenv import load_dotenv
import plotly.graph_objects as go

# ----------------------------------------------------
# Inicialização Firebase
# ----------------------------------------------------
load_dotenv()
@st.cache_resource
def init_firestore():
    base64_str = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if not base64_str:
        st.error("Variável FIREBASE_CREDENTIALS_BASE64 não definida.")
        st.stop()
    try:
        json_bytes = base64.b64decode(base64_str)
        firebase_config = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        st.error(f"Erro ao decodificar credenciais: {e}")
        st.stop()
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

@st.cache_data
def obter_lista_alunos():
    alunos = db.collection("alunos").stream()
    return {f"{doc.to_dict().get('nome')} (RA: {doc.id})": doc.id for doc in alunos}

@st.cache_data
def carregar_codigos_trimestres():
    try:
        with open("turmas.json", "r", encoding="utf-8") as f:
            return json.load(f).get("codigos_trimestres", [])
    except:
        return []

# ----------------------------------------------------
# Navegação
# ----------------------------------------------------
aba = st.sidebar.radio("Escolha a funcionalidade:", ["Cadastrar Notas", "Editar Notas", "Buscar/Editar Aluno", "Relatório"])

# ----------------------------------------------------
# Aba: Cadastrar Notas
# ----------------------------------------------------
if aba == "Cadastrar Notas":
    st.title("📥 Cadastrar Notas")
    alunos_dict = obter_lista_alunos()
    codigos = carregar_codigos_trimestres()

    if not alunos_dict or not codigos:
        st.warning("Dados ausentes.")
        st.stop()

    aluno_sel = st.selectbox("Selecione o aluno:", list(alunos_dict.keys()), key="cadastro_aluno")
    ra = alunos_dict[aluno_sel]
    doc = db.collection("alunos").document(ra).get()
    dados = doc.to_dict() or {}
    existentes = dados.get("trimestres", {}).keys()
    disponiveis = [c for c in codigos if c not in existentes]

    if not disponiveis:
        st.info("Todos os trimestres já estão cadastrados.")
        st.stop()

    cod = st.selectbox("Trimestre:", disponiveis, key="trimestre_cadastro")
    bd = st.slider("Business Drivers", 0, 10, 0, key="bd_cad")
    func = st.slider("Funcionalidade", 0, 10, 0, key="func_cad")
    rnf = st.slider("Req Não Funcionais", 0, 10, 0, key="rnf_cad")
    eng = st.slider("Engenharia", 0, 10, 0, key="eng_cad")
    tec = st.slider("Tecnologia", 0, 10, 0, key="tec_cad")

    if st.button("Salvar", key="btn_cad"):
        db.collection("alunos").document(ra).set({
            "trimestres": {
                cod: {
                    "Business Drivers": bd,
                    "Funcionalidade": func,
                    "Req Não Funcionais": rnf,
                    "Engenharia": eng,
                    "Tecnologia": tec
                }
            }
        }, merge=True)
        st.success("Notas cadastradas!")
        st.rerun()

# ----------------------------------------------------
# Aba: Editar Notas
# ----------------------------------------------------
elif aba == "Editar Notas":
    st.title("✏️ Editar Notas")
    alunos_dict = obter_lista_alunos()
    if not alunos_dict:
        st.warning("Nenhum aluno encontrado.")
        st.stop()

    aluno_sel = st.selectbox("Selecione o aluno:", list(alunos_dict.keys()), key="editar_aluno")
    ra = alunos_dict[aluno_sel]
    doc = db.collection("alunos").document(ra).get()
    dados = doc.to_dict() or {}
    trimestres = dados.get("trimestres", {})
    if not trimestres:
        st.info("Sem notas para editar.")
        st.stop()

    cod = st.selectbox("Trimestre:", sorted(trimestres.keys()), key="editar_cod")
    notas = trimestres.get(cod, {})
    bd = st.slider("Business Drivers", 0, 10, notas.get("Business Drivers", 0), key="bd_edit")
    func = st.slider("Funcionalidade", 0, 10, notas.get("Funcionalidade", 0), key="func_edit")
    rnf = st.slider("Req Não Funcionais", 0, 10, notas.get("Req Não Funcionais", 0), key="rnf_edit")
    eng = st.slider("Engenharia", 0, 10, notas.get("Engenharia", 0), key="eng_edit")
    tec = st.slider("Tecnologia", 0, 10, notas.get("Tecnologia", 0), key="tec_edit")

    if st.button("Atualizar", key="btn_edit"):
        db.collection("alunos").document(ra).update({
            f"trimestres.{cod}": {
                "Business Drivers": bd,
                "Funcionalidade": func,
                "Req Não Funcionais": rnf,
                "Engenharia": eng,
                "Tecnologia": tec
            }
        })
        st.success("Notas atualizadas!")
        st.rerun()

# ----------------------------------------------------
# Aba: Buscar/Editar Aluno
# ----------------------------------------------------
elif aba == "Buscar/Editar Aluno":
    st.title("🔍 Buscar ou Editar Aluno")
    col1, col2 = st.columns(2)
    with col1:
        ra_input = st.text_input("RA do aluno:", key="ra_busca")
    with col2:
        nome_input = st.text_input("Nome do aluno:", key="nome_busca")

    aluno_encontrado = False
    ra_local = None
    dados_aluno = None

    if st.button("Buscar", key="btn_busca"):
        ra = ra_input.strip()
        nome = nome_input.strip()
        if ra:
            doc_ref = db.collection("alunos").document(ra)
            doc = doc_ref.get()
            if doc.exists:
                dados_aluno = doc.to_dict()
                ra_local = ra
                aluno_encontrado = True
                st.success(f"Aluno encontrado: {dados_aluno.get('nome')} (RA: {ra})")
            else:
                st.info(f"Nenhum aluno com RA {ra}. Preencha abaixo para cadastrar.")
                ra_local = ra
        elif nome:
            consulta = db.collection("alunos").where("nome", "==", nome).get()
            if len(consulta) == 1:
                doc = consulta[0]
                dados_aluno = doc.to_dict()
                ra_local = doc.id
                aluno_encontrado = True
                st.success(f"Aluno encontrado: {dados_aluno.get('nome')} (RA: {ra_local})")
            elif len(consulta) > 1:
                opcoes = {f"{doc.to_dict().get('nome')} (RA: {doc.id})": doc.id for doc in consulta}
                escolhido = st.selectbox("Vários alunos encontrados. Selecione:", list(opcoes.keys()), key="selec_duplicado")
                if st.button("Selecionar", key="btn_select_multi"):
                    ra_local = opcoes[escolhido]
                    doc = db.collection("alunos").document(ra_local).get()
                    dados_aluno = doc.to_dict()
                    aluno_encontrado = True
                    st.success(f"Aluno selecionado: {dados_aluno.get('nome')} (RA: {ra_local})")
            else:
                st.info("Nome não encontrado. Preencha abaixo para cadastrar.")

    if "aluno_cadastrado_msg" in st.session_state:
            st.success(st.session_state["aluno_cadastrado_msg"])
            del st.session_state["aluno_cadastrado_msg"]
            
    # Cadastro de novo aluno
    if not aluno_encontrado and ra_input:
        st.subheader("📋 Cadastrar Novo Aluno")
        nome_novo = st.text_input("Nome completo do novo aluno:", key="nome_novo_cad")
        if st.button("Cadastrar Aluno", key="btn_cadastrar_aluno"):
            if not nome_novo.strip():
                st.error("Nome não pode estar vazio.")
            else:
                db.collection("alunos").document(ra_input.strip()).set({
                    "nome": nome_novo.strip(),
                    "ra": ra_input.strip()
                })
                obter_lista_alunos.clear()
                st.session_state["aluno_cadastrado_msg"] = f"Aluno '{nome_novo}' cadastrado com sucesso!"
                st.rerun()

    # Edição de nome de aluno existente
    if aluno_encontrado and dados_aluno and ra_local:
        st.subheader("✏️ Editar Nome do Aluno")
        nome_atual = dados_aluno.get("nome", "")
        novo_nome = st.text_input("Novo nome:", value=nome_atual, key="editar_nome")
        if st.button("Salvar Alterações", key="btn_salvar_nome"):
            db.collection("alunos").document(ra_local).update({"nome": novo_nome.strip()})
            st.success("Nome atualizado!")
            obter_lista_alunos.clear()
            st.rerun()


# ----------------------------------------------------
# Aba: Relatório
# ----------------------------------------------------
elif aba == "Relatório":
    st.title("📊 Relatório de Notas")
    alunos_dict = obter_lista_alunos()
    if not alunos_dict:
        st.warning("Nenhum aluno.")
        st.stop()

    aluno_sel = st.selectbox("Selecione o aluno:", list(alunos_dict.keys()), key="relatorio_aluno")
    ra = alunos_dict[aluno_sel]
    doc = db.collection("alunos").document(ra).get()
    dados = doc.to_dict() or {}
    trimestres = dados.get("trimestres", {})
    if not trimestres:
        st.info("Sem dados de notas.")
        st.stop()

    metricas = ["Business Drivers", "Funcionalidade", "Req Não Funcionais", "Engenharia", "Tecnologia"]
    trimestres_ordenados = sorted(trimestres.items(), key=lambda x: x[0])
    codigos = []
    dados_por_met = {m: [] for m in metricas}

    for cod, notas in trimestres_ordenados:
        codigos.append(cod)
        for m in metricas:
            dados_por_met[m].append(notas.get(m, 0))

    st.subheader("📌 Radar do Último Trimestre")
    fig = go.Figure()
    for cod, notas in trimestres_ordenados[:-1]:
        valores = [notas.get(m, 0) for m in metricas]
        fig.add_trace(go.Scatterpolar(r=valores + [valores[0]], theta=metricas + [metricas[0]], name=cod, opacity=0.3, fill='toself'))
    ultimo_cod, ultimo_notas = trimestres_ordenados[-1]
    fig.add_trace(go.Scatterpolar(
        r=[ultimo_notas.get(m, 0) for m in metricas] + [ultimo_notas.get(metricas[0], 0)],
        theta=metricas + [metricas[0]],
        name=f"{ultimo_cod} (Último)",
        fill='toself',
        line=dict(width=3)
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Gráficos por Métrica")
    for m in metricas:
        fig_linha = go.Figure()
        fig_linha.add_trace(go.Scatter(x=codigos, y=dados_por_met[m], mode='lines+markers', name=m))
        fig_linha.update_layout(title=m, yaxis=dict(range=[0, 10]))
        st.plotly_chart(fig_linha, use_container_width=True)
