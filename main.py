import pymysql
import base64

from mangum import Mangum
from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import date, datetime

app = FastAPI()

# Configuração de sessão
app.add_middleware(
    SessionMiddleware,
    secret_key="carlink",
    session_cookie="carlink_session",
    max_age = 60,  
    same_site="lax",
    https_only=False
)

@app.middleware("http")
async def clear_swal_messages(request: Request, call_next):
    # Mostra a sessão ANTES de qualquer coisa nesta requisição específica
    print(f"DEBUG clear_swal_messages (INÍCIO): ID da Sessão (hash): {hash(str(request.session)) if 'session' in request.scope else 'N/A'}")
    print(f"DEBUG clear_swal_messages (INÍCIO): Sessão ANTES de call_next: {dict(request.session) if 'session' in request.scope else 'Sessão não acessível ainda'}")

    response = await call_next(request) # Processa a rota

    # Mostra a sessão DEPOIS que a rota foi processada, mas ANTES de tentar limpar
    print(f"DEBUG clear_swal_messages (MEIO): Sessão DEPOIS de call_next, ANTES de limpar: {dict(request.session)}")

    try:
        if "swal_message" in request.session:
            print("DEBUG clear_swal_messages (MEIO): 'swal_message' ENCONTRADA. Tentando deletar...")
            del request.session["swal_message"]
            print("DEBUG clear_swal_messages (FIM): 'swal_message' DELETADA da instância da sessão atual.")
            # Para verificar se a modificação "pegou" na sessão atual:
            if "swal_message" not in request.session:
                print("DEBUG clear_swal_messages (FIM): Confirmação - 'swal_message' NÃO está mais na sessão atual.")
            else:
                print("DEBUG clear_swal_messages (FIM): ALERTA - 'swal_message' AINDA está na sessão atual APÓS del!")
        else:
            print("DEBUG clear_swal_messages (FIM): 'swal_message' NÃO foi encontrada na sessão para deletar.")
    except Exception as e:
        print(f"AVISO clear_swal_messages: Exceção ao tentar limpar 'swal_message': {e}")

    # Mostra a sessão FINAL, que deveria ser salva pelo SessionMiddleware
    print(f"DEBUG clear_swal_messages (FIM): Sessão FINAL a ser persistida: {dict(request.session)}")
    return response

# Configuração de arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração de templates Jinja2
templates = Jinja2Templates(directory="templates")

# Configuração do banco de dados
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Senha@123",
    "database": "carlink"
}

# Função para obter conexão com MySQL
def get_db():
    return pymysql.connect(**DB_CONFIG)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Pega o nome do usuário da sessão. Será None se não estiver logado ou se a chave não existir.
    nome_usuario = request.session.get("nome_usuario", None)
    user_is_logged_in = bool(nome_usuario)

    print(f"DEBUG: Rota '/', nome_usuario da sessão: {nome_usuario}") # Para depuração

    return templates.TemplateResponse("index.html", {
        "request": request,
        "nome_usuario": nome_usuario, # ESSENCIAL para o menu.html funcionar como esperado
        "user_logged_in": user_is_logged_in # Opcional, se index.html também usar
    }) 

@app.get("/login", response_class=HTMLResponse)
async def mostrar_login(request: Request):
    request.session.pop("login_error", None)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    Login: str = Form(...),
    Senha: str = Form(...),
    db = Depends(get_db)
):
    try:
        with db.cursor() as cursor:

            cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = MD5(%s)", (Login, Senha))
            user = cursor.fetchone()

            if user:
                request.session["user_logged_in"] = True
                request.session["nome_usuario"] = user[1]
                request.session["cargo"] = user[8]
                print(user[1])
                return RedirectResponse(url="/", status_code=303)
            else:
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Erro no login",
                    "text": "Usuário ou senha inválidos.",
                    "confirmButtonColor": '#303030'
                }
                return RedirectResponse(url="/login", status_code=303)
    finally:
        db.close()

@app.get("/logout")
async def logout(request: Request):
    # Encerra a sessão do usuário e retorna à página inicial.
    request.session.clear()  # remove todos os dados de sessão
    return RedirectResponse(url="/", status_code=303)

@app.post("/cadastro", name="cadastro")
async def cadastrar_usuario(
    request: Request,
    nome: str = Form(...),
    Login: str = Form(...),
    Celular: str = Form(...),
    Senha1: str = Form(...),
    db = Depends(get_db)
):
    try:
        with db.cursor() as cursor:

            cursor.execute("SELECT ID_Usuario FROM Usuario WHERE Login = %s", (Login,))
            if cursor.fetchone():
                request.session["nao_autenticado"] = True
                request.session["mensagem_header"] = "Cadastro"
                request.session["mensagem"] = "Erro: Este login já está em uso!"
                return RedirectResponse(url="/", status_code=303)

            sql = "INSERT INTO Usuario (Nome, Celular, Login, Senha) VALUES (%s, %s, %s, MD5(%s))"
            cursor.execute(sql, (nome, Celular, Login, Senha1))
            db.commit()

            request.session["nao_autenticado"] = True
            request.session["mensagem_header"] = "Cadastro"
            request.session["mensagem"] = "Registro cadastrado com sucesso! Você já pode realizar login."
            return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        request.session["nao_autenticado"] = True
        request.session["mensagem_header"] = "Cadastro"
        request.session["mensagem"] = f"Erro ao cadastrar: {str(e)}"
        return RedirectResponse(url="/", status_code=303)

    finally:
        db.close()

app.get("/cadastrocarro", name="cadastrocarro", response_class=HTMLResponse)
async def cadastro_carro_form(request: Request):
    """
    Exibe o formulário de cadastro de carro.
    """
    nome_usuario = request.session.get("nome_usuario", None)
    return templates.TemplateResponse("cadastrocarro.html", {"request": request, "nome_usuario": nome_usuario})

@app.post("/cadastrocarro", name="cadastrocarro_post")
async def cadastrar_carro(
    request: Request,
    marca: str = Form(...),
    modelo: str = Form(...),
    ano: int = Form(...),
    placa: str = Form(...),
    renavam: str = Form(...),
    chassi: str = Form(...),
    cor: str = Form(...),
    motor: str = Form(...),
    potencia: float = Form(...),
    preco: float = Form(...),
    imagem: UploadFile = File(None),
    db: pymysql.Connection = Depends(get_db)  # Use type hinting for clarity
):
    """
    Processa o envio do formulário de cadastro de carro e salva os dados no banco de dados.
    """
    try:
        foto_bytes: Optional[bytes] = None
        if imagem and imagem.filename:
            foto_bytes = await imagem.read()

        with db.cursor() as cursor:
            sql = """
                INSERT INTO Carro (Marca, Modelo, Ano, Placa, Renavam, Chassi, Cor, Motor, Potencia, Preco, Imagem) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (marca, modelo, ano, placa, renavam, chassi, cor, motor, potencia, preco, foto_bytes))
            db.commit()

        request.session["swal_message"] = {
            "icon": "success",
            "title": "Cadastro de Carro",
            "text": "Carro cadastrado com sucesso!",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/cadastrocarro", status_code=303)

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Cadastrar Carro",
            "text": f"Erro ao cadastrar o carro: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/cadastrocarro", status_code=303)

    finally:
        db.close()

@app.get("/medListar", name="medListar", response_class=HTMLResponse)
async def listar_medicos(request: Request, db=Depends(get_db)):
    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        # Consulta SQL unindo Medico e Especialidade, ordenando por nome
        sql = """
            SELECT M.ID_Medico, M.CRM, M.Nome, E.Nome_Espec AS Especialidade,
                   M.Foto, M.Dt_Nasc
            FROM Medico AS M 
            JOIN Especialidade AS E ON M.ID_Espec = E.ID_Espec
            ORDER BY M.Nome
        """
        cursor.execute(sql)
        medicos = cursor.fetchall()  # lista de dicts com dados dos médicos

    # Processa os dados (calcula idade e converte foto para base64 se necessário)
    hoje = date.today()
    for med in medicos:
        # Calcula idade baseado em Dt_Nasc (formato date/datetime do MySQL)
        dt_nasc = med["Dt_Nasc"]
        if isinstance(dt_nasc, str):
            # Se vier como string "YYYY-MM-DD", converte para date
            ano, mes, dia = map(int, dt_nasc.split("-"))
            dt_nasc = date(ano, mes, dia)
        idade = hoje.year - dt_nasc.year
        # Ajusta se aniversário ainda não ocorreu no ano corrente
        if (dt_nasc.month, dt_nasc.day) > (hoje.month, hoje.day):
            idade -= 1
        med["idade"] = idade

        # Converter foto blob para base64 (se houver)
        if med["Foto"]:
            med["Foto_base64"] = base64.b64encode(med["Foto"]).decode('utf-8')
        else:
            med["Foto_base64"] = None

    nome_usuario = request.session.get("nome_usuario", None)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Renderiza o template 'medListar.html' com os dados dos médicos
    return templates.TemplateResponse("medListar.html", {
        "request": request,
        "medicos": medicos,
        "hoje": agora,
        "nome_usuario": nome_usuario
    })

@app.get("/medIncluir", response_class=HTMLResponse)
async def medIncluir(request: Request, db=Depends(get_db)):
    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != "admin":
        return RedirectResponse(url="/medListar", status_code=303)

    # Obter especialidades do banco para o combo
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT ID_Espec, Nome_Espec FROM Especialidade")
        especialidades = cursor.fetchall()
    db.close()

    # Dados para o template (incluindo data/hora e nome do usuário)
    nome_usuario = request.session.get("nome_usuario", None)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return templates.TemplateResponse("medIncluir.html", {
        "request": request,
        "especialidades": especialidades,
        "hoje": agora,
        "nome_usuario": nome_usuario
    })

@app.post("/medIncluir_exe")
async def medIncluir_exe(
    request: Request,
    Nome: str = Form(...),
    CRM: str = Form(...),
    Especialidade: str = Form(...),
    DataNasc: str = Form(None),
    Imagem: UploadFile = File(None),
    db=Depends(get_db)
):
    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != "admin":
        return RedirectResponse(url="/medListar", status_code=303)

    foto_bytes = None
    if Imagem and Imagem.filename:
        foto_bytes = await Imagem.read()

    try:
        with db.cursor() as cursor:
            sql = """INSERT INTO Medico (Nome, CRM, ID_Espec, Dt_Nasc, Foto)
                     VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(sql, (Nome, CRM, Especialidade, DataNasc, foto_bytes))
            db.commit()

        request.session["mensagem_header"] = "Inclusão de Novo Médico"
        request.session["mensagem"] = "Registro cadastrado com sucesso!"
    except Exception as e:
        request.session["mensagem_header"] = "Erro ao cadastrar"
        request.session["mensagem"] = str(e)
    finally:
        db.close()

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nome_usuario = request.session.get("nome_usuario", None)

    return templates.TemplateResponse("medIncluir_exe.html", {
        "request": request,
        "mensagem_header": request.session.get("mensagem_header", ""),
        "mensagem": request.session.get("mensagem", ""),
        "hoje": agora,
        "nome_usuario": nome_usuario
    })

@app.get("/medExcluir", response_class=HTMLResponse)
async def med_excluir(request: Request, id: int, db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != "admin":
        return RedirectResponse(url="/medListar", status_code=303)

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        sql = ("SELECT M.ID_Medico, M.Nome, M.CRM, M.Dt_Nasc, E.Nome_Espec "
               "FROM Medico M JOIN Especialidade E ON M.ID_Espec = E.ID_Espec "
               "WHERE M.ID_Medico = %s")
        cursor.execute(sql, (id,))
        medico = cursor.fetchone()
    db.close()

    # Formatar data (YYYY-MM-DD para dd/mm/aaaa)
    data_nasc = medico["Dt_Nasc"]
    if isinstance(data_nasc, str):
        ano, mes, dia = data_nasc.split("-")
    else:
        ano, mes, dia = data_nasc.year, f"{data_nasc.month:02d}", f"{data_nasc.day:02d}"
    data_formatada = f"{dia}/{mes}/{ano}"

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    nome_usuario = request.session.get("nome_usuario", None)

    return templates.TemplateResponse("medExcluir.html", {
        "request": request,
        "med": medico,
        "data_formatada": data_formatada,
        "hoje": hoje,
        "nome_usuario": nome_usuario
    })

@app.post("/medExcluir_exe")
async def med_excluir_exe(request: Request, id: int = Form(...), db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != "admin":
        return RedirectResponse(url="/medListar", status_code=303)

    try:
        with db.cursor(pymysql.cursors.DictCursor) as cursor:

            sql_delete = "DELETE FROM Medico WHERE ID_Medico = %s"
            cursor.execute(sql_delete, (id,))
            db.commit()

            request.session["mensagem_header"] = "Exclusão de Médico"
            request.session["mensagem"] = f"Médico excluído com sucesso."

    except Exception as e:
        request.session["mensagem_header"] = "Erro ao excluir"
        request.session["mensagem"] = str(e)
    finally:
        db.close()

    # Redireciona para a página de resultado da exclusão
    return templates.TemplateResponse("medExcluir_exe.html", {
        "request": request,
        "mensagem_header": request.session.get("mensagem_header", ""),
        "mensagem": request.session.get("mensagem", ""),
        "hoje": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "nome_usuario": request.session.get("nome_usuario", None)
    })

@app.get("/medAtualizar", response_class=HTMLResponse)
async def med_atualizar(request: Request, id: int, db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != "admin":
        return RedirectResponse(url="/medListar", status_code=303)

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM Medico WHERE ID_Medico = %s", (id,))
        medico = cursor.fetchone()
        cursor.execute("SELECT ID_Espec, Nome_Espec FROM Especialidade")
        especialidades = cursor.fetchall()
    db.close()

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    return templates.TemplateResponse("medAtualizar.html", {
        "request": request,
        "med": medico,
        "especialidades": especialidades,
        "hoje": hoje
    })

@app.post("/medAtualizar_exe")
async def med_atualizar_exe(
    request: Request,
    id: int = Form(...),
    Nome: str = Form(...),
    CRM: str = Form(...),
    Especialidade: str = Form(...),
    DataNasc: str = Form(None),
    Imagem: UploadFile = File(None),
    db=Depends(get_db)
):
    if not request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)

    foto_bytes = None
    if Imagem and Imagem.filename:
        foto_bytes = await Imagem.read()

    try:
        with db.cursor() as cursor:
            if foto_bytes:
                sql = """UPDATE Medico 
                         SET Nome=%s, CRM=%s, Dt_Nasc=%s, ID_Espec=%s, Foto=%s
                         WHERE ID_Medico=%s"""
                cursor.execute(sql, (Nome, CRM, DataNasc, Especialidade, foto_bytes, id))
            else:
                sql = """UPDATE Medico 
                         SET Nome=%s, CRM=%s, Dt_Nasc=%s, ID_Espec=%s
                         WHERE ID_Medico=%s"""
                cursor.execute(sql, (Nome, CRM, DataNasc, Especialidade, id))
            db.commit()

        request.session["mensagem_header"] = "Atualização de Médico"
        request.session["mensagem"] = "Registro atualizado com sucesso!"

    except Exception as e:
        request.session["mensagem_header"] = "Erro ao atualizar"
        request.session["mensagem"] = str(e)
    finally:
        db.close()

    return templates.TemplateResponse("medAtualizar_exe.html", {
        "request": request,
        "mensagem_header": request.session.get("mensagem_header", ""),
        "mensagem": request.session.get("mensagem", ""),
        "hoje": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "nome_usuario": request.session.get("nome_usuario", None)
    })

@app.post("/reset_session")
async def reset_session(request: Request):
    request.session.pop("mensagem_header", None)
    request.session.pop("mensagem", None)
    return {"status": "ok"}

Mangum(app)

