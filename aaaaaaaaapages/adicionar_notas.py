import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import base64
from dotenv import load_dotenv

# ----------------------------------------------------
# 2.1. Carrega variáveis de ambiente do .env
# ----------------------------------------------------
load_dotenv()  # Carrega FIREBASE_CREDENTIALS_BASE64 para os.environ :contentReference[oaicite:6]{index=6}

# ----------------------------------------------------
# 2.2. Inicialização do Firebase (Firestore) via Base64
# ----------------------------------------------------
@st.cache_resource
def init_firestore():
    # 1) Recupera a string Base64 contendo o JSON de credenciais
    base64_str = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if not base64_str:
        st.error("A variável FIREBASE_CREDENTIALS_BASE64 não está definida no .env.")
        st.stop()  # Interrompe a execução caso falte a variável :contentReference[oaicite:7]{index=7}

    # 2) Decodifica Base64 para bytes
    try:
        json_bytes = base64.b64decode(base64_str)
    except Exception as e:
        st.error(f"Erro ao decodificar Base64: {e}")
        st.stop()  # Interrompe se houver falha na decodificação :contentReference[oaicite:8]{index=8}

    # 3) Converte bytes para string e carrega em dicionário JSON
    try:
        firebase_config = json.loads(json_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        st.error("Erro ao converter os bytes decodificados em JSON. Verifique FIREBASE_CREDENTIALS_BASE64.")
        st.stop()  # Interrompe se o JSON estiver mal formado :contentReference[oaicite:9]{index=9}

    # 4) Inicializa apenas se ainda não houver um app criado
    if not firebase_admin._apps:  # Checa se já existe algum app inicializado :contentReference[oaicite:10]{index=10}
        try:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Falha ao inicializar o Firebase: {e}")
            st.stop()  # Interrompe caso a inicialização falhe :contentReference[oaicite:11]{index=11}

    return firestore.client()

# Chama a função uma única vez por sessão
db = init_firestore()  # Cliente Firestore autenticado em memória :contentReference[oaicite:12]{index=12}

st.title("Adicionar Notas de Trimestre")

# ----------------------------------------------------
# 2.3. Carrega os códigos de trimestre a partir de turmas.json
# ----------------------------------------------------
@st.cache_data
def carregar_codigos_de_turmas():
    caminho_arquivo = os.path.join(os.getcwd(), "turmas.json")
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("codigos_trimestres", [])
    except FileNotFoundError:
        st.error(f"Arquivo 'turmas.json' não encontrado em: {caminho_arquivo}")
        return []
    except json.JSONDecodeError:
        st.error("Erro ao decodificar o JSON. Verifique se o 'turmas.json' está bem formatado.")
        return []

todos_codigos = carregar_codigos_de_turmas()
if not todos_codigos:
    st.warning("Nenhum código de trimestre carregado de 'turmas.json'.")
    st.stop()  # Para se não houver trimestres :contentReference[oaicite:13]{index=13}

# ----------------------------------------------------
# 2.4. Obtém lista de alunos para popular o dropdown
# ----------------------------------------------------
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
    st.stop()  # Para se não houver alunos cadastrados :contentReference[oaicite:14]{index=14}

# Dropdown para selecionar o aluno
selecionado = st.selectbox("Selecione o aluno pelo nome:", list(alunos_dict.keys()))
ra_selecionado = alunos_dict[selecionado]

# ----------------------------------------------------
# 2.5. Obtém dados do aluno selecionado
# ----------------------------------------------------
doc_ref = db.collection("alunos").document(ra_selecionado)
doc = doc_ref.get()
dados_aluno = doc.to_dict() if doc.exists else {"nome": "", "trimestres": {}}

st.markdown(f"**Aluno selecionado:** {dados_aluno.get('nome', '')}  \n**RA:** {ra_selecionado}")

# ----------------------------------------------------
# 2.6. Filtra trimestres ainda não cadastrados para esse aluno
# ----------------------------------------------------
trimestres_existentes = list(dados_aluno.get("trimestres", {}).keys())
opcoes_disponiveis = [c for c in todos_codigos if c not in trimestres_existentes]

if not opcoes_disponiveis:
    st.warning("Não há trimestres disponíveis para adicionar (todos já cadastrados).")
    st.stop()  # Para se não houver novas opções :contentReference[oaicite:15]{index=15}

codigo_trimestre = st.selectbox("Selecione o código do trimestre a ser cadastrado:", opcoes_disponiveis)

# ----------------------------------------------------
# 2.7. Campos para inserir as notas
# ----------------------------------------------------
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
    # Grava no Firestore usando merge=True para não sobrescrever outros trimestres
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
    st.rerun()  # Recarrega a página para atualizar opções e listas :contentReference[oaicite:16]{index=16}
