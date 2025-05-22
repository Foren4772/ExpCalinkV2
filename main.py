import pymysql
import base64

from mangum import Mangum
from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import date, datetime
from typing import Optional, List, Dict, Any

app = FastAPI()

# Configuração de sessão
app.add_middleware(
    SessionMiddleware,
    secret_key="carlink", # ATENÇÃO: Em produção, use uma chave forte e segura!
    session_cookie="carlink_session",
    max_age = 6000,
    same_site="lax",
    https_only=False
)

@app.middleware("http")
async def clear_swal_messages(request: Request, call_next):
    # Esta função de middleware não precisa mais limpar swal_message ativamente,
    # pois a lógica de pop() já está nas rotas que consomem a mensagem.
    response = await call_next(request)
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
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        yield connection
    finally:
        if connection:
            connection.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    nome_usuario = request.session.get("nome_usuario", None)
    user_is_logged_in = bool(nome_usuario)
    # A mensagem será passada APENAS se for definida por outra rota que redirecione para cá.
    # swal_message = request.session.pop("swal_message", None) # Já foi movido para rotas específicas

    return templates.TemplateResponse("index.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "user_logged_in": user_is_logged_in,
        "swal_message": request.session.pop("swal_message", None) # Pega e remove a mensagem aqui
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
                request.session["nome_usuario"] = user["nome"]
                request.session["cargo"] = user["cargo_id"]
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
        pass

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

from fastapi.responses import RedirectResponse
from fastapi import status

from fastapi.responses import RedirectResponse
from fastapi import status

@app.get("/gerenciar", response_class=HTMLResponse)
async def gerenciar(request: Request):
    nome_usuario = request.session.get("nome_usuario", None)
    cargo = request.session.get("cargo", None)
    user_is_logged_in = bool(nome_usuario)

    # Verifica se o usuário está logado e tem permissão (cargo 1 ou 2)
    if not user_is_logged_in or cargo not in [1, 2]:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("gerenciar.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "user_logged_in": user_is_logged_in,
        "cargo": cargo
    })



@app.post("/cadastro", name="cadastro")
async def cadastrar_usuario_index(
    request: Request,
    nome: str = Form(...),
    Login: str = Form(...),
    Celular: str = Form(...),
    Senha1: str = Form(...),
    db = Depends(get_db)
):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s", (Login,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro",
                    "text": "Erro: Este e-mail já está em uso!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/", status_code=303)

            sql = "INSERT INTO Usuario (nome, telefone, email, senha, cargo_id) VALUES (%s, %s, %s, MD5(%s), %s)"
            cursor.execute(sql, (nome, Celular, Login, Senha1, 2)) # cargo_id = 2 para usuário comum
            db.commit()

            # O LAST_INSERT_ID() é específico do MySQL para obter o último ID inserido
            cursor.execute("SELECT LAST_INSERT_ID() as id_usuario")
            new_user_id = cursor.fetchone()['id_usuario']

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Cadastro",
                "text": f"Registro cadastrado com sucesso! Seu ID de usuário é: {new_user_id}. Você já pode realizar login.",
                "confirmButtonColor": '#303030'
            }
            return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Cadastro",
            "text": f"Erro ao cadastrar: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    finally:
        pass

# Rota para exibir o formulário de cadastro de usuário (ACESSO LIVRE)
@app.get("/cadastro-usuario", response_class=HTMLResponse)
async def cadastro_usuario_form(request: Request, db=Depends(get_db)):
    nome_usuario = request.session.get("nome_usuario", None)
    # REMOVIDA A RESTRIÇÃO DE CARGO AQUI. Qualquer um pode acessar esta página agora.
    # if request.session.get("cargo") != 1:
    #     request.session["swal_message"] = {
    #         "icon": "warning",
    #         "title": "Acesso Negado",
    #         "text": "Você não tem permissão para acessar esta página.",
    #         "confirmButtonColor": '#303030'
    #     }
    #     return RedirectResponse(url="/", status_code=303)

    swal_message = request.session.pop("swal_message", None)

    cargos = []
    # Se esta rota é para novos usuários gerais, eles não devem escolher o cargo.
    # Você pode remover a busca por cargos ou filtrar para mostrar apenas cargos permitidos para auto-cadastro.
    # Por exemplo, se só puderem se cadastrar como 'usuário comum', não precise carregar os cargos.
    # Se for uma página de cadastro *mais completa* onde o admin também pode usar para cadastrar
    # outros admins, aí a lista de cargos faz sentido, mas o default seria o cargo comum.
    try:
        with db.cursor() as cursor:
            # Buscar cargos para exibição (se necessário, ou remover)
            cursor.execute("SELECT id_cargo, nome FROM cargo ORDER BY nome")
            cargos = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar cargos: {e}")

    return templates.TemplateResponse("cadastro-usuario.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message,
        "cargos": cargos # Mantenho a lista de cargos, mas pense se faz sentido para um usuário comum
    })


# Rota para processar o cadastro de usuário (ACESSO LIVRE, atribuindo cargo padrão)
@app.post("/cadastro-usuario", name="criar_usuario")
async def criar_usuario(
    request: Request,
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None),
    cpf: str = Form(...),
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    senha: str = Form(...),
    cargo_id: Optional[int] = Form(2), # Defino o default como 2 (usuário comum)
    imagemPerfil: UploadFile = File(None),
    db = Depends(get_db)
):
    # REMOVIDA A RESTRIÇÃO DE CARGO AQUI. Qualquer um pode enviar este formulário.
    # if request.session.get("cargo") != 1:
    #     request.session["swal_message"] = {
    #         "icon": "warning",
    #         "title": "Acesso Negado",
    #         "text": "Você não tem permissão para realizar esta operação.",
    #         "confirmButtonColor": '#303030'
    #     }
    #     return RedirectResponse(url="/", status_code=303)

    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id_usuario FROM usuario WHERE cpf = %s", (cpf,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Usuário",
                    "text": "Erro: Este CPF já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-usuario", status_code=303)
            
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s", (email,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Usuário",
                    "text": "Erro: Este e-mail já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-usuario", status_code=303)


            imagem_bytes = None
            if imagem and imagem.filename:
                imagem_bytes = await imagem.read()

            data_nascimento_sql = None
            if dataNascimento:
                data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()

            # Garante que o cargo_id seja 2 (usuário comum) se não for admin logado
            # ou se o campo cargo_id não for enviado pelo formulário.
            # Se você quer que um ADMIN possa criar outros admins por essa tela,
            # então você precisaria de uma lógica mais complexa aqui, por exemplo:
            # se request.session.get("cargo") == 1 e cargo_id for enviado, use o cargo_id enviado.
            # Caso contrário, force cargo_id=2.
            # Para simplificar, vou manter que o cargo_id será 2 para qualquer cadastro nesta rota,
            # a menos que o admin, ao usar esta mesma tela, explicitamente envie outro cargo_id.
            # Considerando que a restrição de admin foi removida, o default é 2.
            final_cargo_id = cargo_id if request.session.get("cargo") == 1 else 2


            sql = """
                INSERT INTO usuario
                (nome, genero, dataNascimento, cpf, email, telefone, senha, cargo_id, imagemPerfil)
                VALUES (%s, %s, %s, %s, %s, %s, MD5(%s), %s, %s)
            """
            cursor.execute(sql, (
                nome, genero, data_nascimento_sql, cpf, email,
                telefone, senha, final_cargo_id, imagem_bytes # Usar final_cargo_id
            ))
            db.commit()

            # Captura o ID do usuário recém-criado
            cursor.execute("SELECT LAST_INSERT_ID() as id_usuario")
            new_user_id = cursor.fetchone()['id_usuario']

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Cadastro de Usuário",
                "text": f"Usuário cadastrado com sucesso! Seu ID é: {new_user_id}.",
                "confirmButtonColor": '#303030'
            }
            return RedirectResponse(url="/cadastro-usuario", status_code=303) # Redireciona para a mesma página

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Cadastro de Usuário",
            "text": f"Erro ao cadastrar usuário: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/cadastro-usuario", status_code=303)

    finally:
        pass

@app.get("/sobre-nos", response_class=HTMLResponse)
async def sobre_nos(request: Request):
    return templates.TemplateResponse("sobre-nos.html", {"request": request})

@app.get("/politicas", response_class=HTMLResponse)
async def read_politicas(request: Request):
    """
    Rota para exibir a página de políticas de uso e privacidade.
    """
    return templates.TemplateResponse("politicas.html", {"request": request})

# --- Rota de Cadastro de Carro (GET) - ALTERADA PARA REDIRECIONAR PARA /vender ---
@app.get("/cadastro-usuario", response_class=HTMLResponse)
async def cadastro_usuario_form(request: Request, db=Depends(get_db)):
    nome_usuario = request.session.get("nome_usuario", None)
    
    swal_message = request.session.pop("swal_message", None)

    cargos = []
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id_cargo, nome FROM cargo ORDER BY nome")
            cargos = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar cargos: {e}")

    return templates.TemplateResponse("cadastro-usuario.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message,
        "cargos": cargos
    })


@app.post("/cadastro-usuario", name="criar_usuario")
async def criar_usuario(
    request: Request,
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None),
    cpf: str = Form(...),
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    senha: str = Form(...),
    cargo_id: Optional[int] = Form(2), # Default para usuário comum
    imagemPerfil: UploadFile = File(None), # Parâmetro do arquivo de imagem
    db = Depends(get_db)
):
    try:
        with db.cursor() as cursor:
            # Validação de CPF e E-mail duplicados
            cursor.execute("SELECT id_usuario FROM usuario WHERE cpf = %s", (cpf,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Usuário",
                    "text": "Erro: Este CPF já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-usuario", status_code=303)
            
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s", (email,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Usuário",
                    "text": "Erro: Este e-mail já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-usuario", status_code=303)

            # Lida com o upload da imagem
            imagem_bytes = None
            # CORREÇÃO: Usando 'imagemPerfil' como nome da variável
            if imagemPerfil and imagemPerfil.filename and imagemPerfil.size > 0:
                imagem_bytes = await imagemPerfil.read()

            data_nascimento_sql = None
            if dataNascimento:
                data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()

            # Define o cargo_id (mantém o default 2 se não for admin logado)
            final_cargo_id = cargo_id if request.session.get("cargo") == 1 else 2

            sql = """
                INSERT INTO usuario
                (nome, genero, dataNascimento, cpf, email, telefone, senha, cargo_id, imagemPerfil)
                VALUES (%s, %s, %s, %s, %s, %s, MD5(%s), %s, %s)
            """
            cursor.execute(sql, (
                nome, genero, data_nascimento_sql, cpf, email,
                telefone, senha, final_cargo_id, imagem_bytes
            ))
            db.commit()

            cursor.execute("SELECT LAST_INSERT_ID() as id_usuario")
            new_user_id = cursor.fetchone()['id_usuario']

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Cadastro de Usuário",
                "text": f"Usuário cadastrado com sucesso! Seu ID é: {new_user_id}.",
                "confirmButtonColor": '#303030'
            }
            return RedirectResponse(url="/cadastro-usuario", status_code=303) # Redireciona para a mesma página

    except Exception as e:
        # Agora o erro será mais descritivo se não for o problema da imagem.
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Cadastro de Usuário",
            "text": f"Erro ao cadastrar usuário: {str(e)}", # Captura a mensagem de erro real
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/cadastro-usuario", status_code=303)

    finally:
        pass

# --- Rota para a página /vender (NOVA OU ATUALIZADA) ---
@app.get("/vender", response_class=HTMLResponse)
async def vender_carro_intro(request: Request):
    return templates.TemplateResponse("vender.html", {"request": request})


# --- ROTA PARA CADASTRO DE CARRO (NOVA OU CORRIGIDA) ---
@app.get("/cadastrocarro", response_class=HTMLResponse)
async def cadastro_carro_form(request: Request, db=Depends(get_db)):
    nome_usuario = request.session.get("nome_usuario", None)

    # VERIFICA SE ESTÁ LOGADO
    if not nome_usuario:
        return RedirectResponse(url="/", status_code=302)

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT modelo.id_modelo, modelo.nome AS modelo_nome, marca.nome AS marca_nome
            FROM modelo
            JOIN marca ON modelo.fk_id_marca = marca.id_marca
            ORDER BY marca.nome, modelo.nome
        """)
        modelos = cursor.fetchall()

    swal_message = request.session.pop("swal_message", None)  # pega e remove da sessão

    return templates.TemplateResponse("cadastrocarro.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "modelos": modelos,
        "swal_message": swal_message  # passa para o template
    })


@app.post("/cadastrocarro", name="cadastrocarro_post")
async def cadastrar_carro(
    request: Request,
    modelo: int = Form(...),
    ano: date = Form(...),
    placa: str = Form(...),
    renavam: str = Form(...),
    chassi: str = Form(...),
    cor: str = Form(...),
    motor: str = Form(...),
    potencia: float = Form(...),
    preco: float = Form(...),
    descricao: str = Form(...),
    imagem: UploadFile = File(None),
    db: pymysql.Connection = Depends(get_db)
):
    """
    Processa o envio do formulário de cadastro de carro e salva os dados no banco de dados.
    """
    try:
        foto_bytes = None
        if imagem and imagem.filename:
            foto_bytes = await imagem.read()

        with db.cursor() as cursor:
            sql = """
                INSERT INTO Carro (
                    fk_id_modelo, Ano, Placa, Renavam, Chassi, Cor, Motor,
                    Potencia, Preco, Imagem, Descricao
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                modelo, ano, placa, renavam, chassi, cor, motor,
                potencia, preco, foto_bytes, descricao
            ))
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

@app.get("/comprar", response_class=HTMLResponse)
async def comprar_carro(
    request: Request,
    marca_id: Optional[int] = None,
    modelo_id: Optional[int] = None,
    ano_min: Optional[int] = None,
    preco_max: Optional[str] = None,
    db: pymysql.Connection = Depends(get_db)
):
    nome_usuario = request.session.get("nome_usuario", None)

    query_params = []
    sql_where = []

    preco_max_float = None
    selected_preco_max_display = preco_max
    if preco_max:
        preco_max_clean = preco_max.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            preco_max_float = float(preco_max_clean)
            sql_where.append("Preco <= %s")
            query_params.append(preco_max_float)
        except ValueError:
            pass

    if marca_id:
        sql_where.append("marca.id_marca = %s")
        query_params.append(marca_id)

    if modelo_id:
        sql_where.append("modelo.id_modelo = %s")
        query_params.append(modelo_id)

    if ano_min:
        sql_where.append("Ano >= %s")
        query_params.append(ano_min)

    sql_base = """
        SELECT
            carro.id_carro,
            marca.nome AS marca_nome,
            modelo.nome AS modelo_nome,
            carro.Ano,
            carro.Cor,
            carro.Potencia,
            carro.Preco,
            carro.Descricao,
            carro.Imagem
        FROM
            Carro AS carro
        JOIN
            Modelo AS modelo ON carro.fk_id_modelo = modelo.id_modelo
        JOIN
            Marca AS marca ON modelo.fk_id_marca = marca.id_marca
    """
    if sql_where:
        sql_base += " WHERE " + " AND ".join(sql_where)
    sql_base += " ORDER BY carro.Ano DESC, carro.Preco ASC"

    carros = []
    marcas = []
    modelos_filtrados = []

    with db.cursor() as cursor:
        cursor.execute(sql_base, tuple(query_params))
        carros_db = cursor.fetchall()

        for carro in carros_db:
            if carro['Imagem']:
                if isinstance(carro['Imagem'], bytearray):
                    carro['Imagem'] = bytes(carro['Imagem'])
                carro['Imagem_base64'] = base64.b64encode(carro['Imagem']).decode('utf-8')
            else:
                carro['Imagem_base64'] = None

            carros.append(carro)

        cursor.execute("SELECT id_marca, nome FROM marca ORDER BY nome")
        marcas = cursor.fetchall()

        if marca_id:
            cursor.execute("SELECT id_modelo, nome FROM modelo WHERE fk_id_marca = %s ORDER BY nome", (marca_id,))
            modelos_filtrados = cursor.fetchall()

    swal_message = request.session.pop("swal_message", None) # Pega e remove a mensagem

    return templates.TemplateResponse("comprar.html", {
        "request": request,
        "nome_usuario": nome_usuario,
        "carros": carros,
        "marcas": marcas,
        "modelos_filtrados": modelos_filtrados,
        "selected_marca_id": marca_id,
        "selected_modelo_id": modelo_id,
        "selected_ano_min": ano_min,
        "selected_preco_max_display": selected_preco_max_display,
        "swal_message": swal_message # Passa a mensagem para o template
    })


@app.get("/usuariosListar", name="usuariosListar", response_class=HTMLResponse)
async def listar_usuarios(request: Request, db=Depends(get_db)):
    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)

    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para visualizar esta página.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        sql = """
            SELECT U.id_usuario, U.nome, U.genero, U.dataNascimento, U.cpf,
            U.email, U.telefone, U.imagemPerfil, U.cargo_id, C.nome AS cargo
            FROM usuario AS U
            LEFT JOIN cargo AS C ON U.cargo_id = C.id_cargo
            ORDER BY U.nome
            """

        cursor.execute(sql)
        usuarios = cursor.fetchall()

    hoje = date.today()
    for usuario in usuarios:
        dt_nasc = usuario["dataNascimento"]
        if dt_nasc:
            if isinstance(dt_nasc, str):
                ano, mes, dia = map(int, dt_nasc.split("-"))
                dt_nasc = date(ano, mes, dia)

            idade = hoje.year - dt_nasc.year
            if (dt_nasc.month, dt_nasc.day) > (hoje.month, hoje.day):
                idade -= 1
            usuario["idade"] = idade
        else:
            usuario["idade"] = "N/A"

        if usuario["imagemPerfil"]:
            if isinstance(usuario["imagemPerfil"], bytearray):
                usuario["imagemPerfil"] = bytes(usuario["imagemPerfil"])
            usuario["imagemPerfil_base64"] = "data:image/png;base64," + base64.b64encode(usuario["imagemPerfil"]).decode('utf-8')
        else:
            usuario["imagemPerfil_base64"] = None

    nome_usuario = request.session.get("nome_usuario", "Visitante")
    swal_message = request.session.pop("swal_message", None)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return templates.TemplateResponse("usuariosListar.html", {
        "request": request,
        "usuarios": usuarios,
        "hoje": agora,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message
    })

@app.get("/medIncluir", response_class=HTMLResponse)
async def medIncluir(request: Request, db=Depends(get_db)):
    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para acessar esta página.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    especialidades = []
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT ID_Espec, Nome_Espec FROM Especialidade")
            especialidades = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar especialidades: {e}")

    nome_usuario = request.session.get("nome_usuario", None)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    swal_message = request.session.pop("swal_message", None)

    return templates.TemplateResponse("medIncluir.html", {
        "request": request,
        "especialidades": especialidades,
        "hoje": agora,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message
    })

@app.post("/medIncluir_exe")
async def medIncluir_exe(
    request: Request,
    Nome: str = Form(...),
    CRM: str = Form(...),
    Especialidade: str = Form(...),
    DataNasc: Optional[str] = Form(None),
    Imagem: UploadFile = File(None),
    db=Depends(get_db)
):
    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    foto_bytes = None
    if Imagem and Imagem.filename:
        foto_bytes = await Imagem.read()

    try:
        with db.cursor() as cursor:
            sql = """INSERT INTO Medico (Nome, CRM, ID_Espec, Dt_Nasc, Foto)
                     VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(sql, (Nome, CRM, Especialidade, DataNasc, foto_bytes))
            db.commit()

        request.session["swal_message"] = {
            "icon": "success",
            "title": "Inclusão de Novo Médico",
            "text": "Registro cadastrado com sucesso!",
            "confirmButtonColor": '#303030'
        }
    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Cadastrar",
            "text": f"Erro ao cadastrar médico: {str(e)}",
            "confirmButtonColor": '#d33'
        }
    finally:
        pass

    return RedirectResponse(url="/medIncluir", status_code=303)

@app.get("/medExcluir", response_class=HTMLResponse)
async def med_excluir(request: Request, id: int, db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para acessar esta página.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    medico = None
    try:
        with db.cursor() as cursor:
            sql = ("SELECT M.ID_Medico, M.Nome, M.CRM, M.Dt_Nasc, E.Nome_Espec "
                   "FROM Medico M JOIN Especialidade E ON M.ID_Espec = E.ID_Espec "
                   "WHERE M.ID_Medico = %s")
            cursor.execute(sql, (id,))
            medico = cursor.fetchone()
    except Exception as e:
        print(f"Erro ao buscar médico para exclusão: {e}")

    if not medico:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Médico Não Encontrado",
            "text": "O médico que você tentou excluir não foi encontrado.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    data_formatada = "N/A"
    data_nasc = medico["Dt_Nasc"]
    if data_nasc:
        if isinstance(data_nasc, (date, datetime)):
            data_formatada = data_nasc.strftime("%d/%m/%Y")
        elif isinstance(data_nasc, str):
            try:
                data_formatada = datetime.strptime(data_nasc, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                pass

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    nome_usuario = request.session.get("nome_usuario", None)
    swal_message = request.session.pop("swal_message", None)

    return templates.TemplateResponse("medExcluir.html", {
        "request": request,
        "med": medico,
        "data_formatada": data_formatada,
        "hoje": hoje,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message
    })

@app.post("/medExcluir_exe")
async def med_excluir_exe(request: Request, id: int = Form(...), db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    try:
        with db.cursor() as cursor:
            sql_delete = "DELETE FROM Medico WHERE ID_Medico = %s"
            cursor.execute(sql_delete, (id,))
            db.commit()

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Exclusão de Médico",
                "text": "Médico excluído com sucesso.",
                "confirmButtonColor": '#303030'
            }

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Excluir",
            "text": f"Erro ao excluir médico: {str(e)}",
            "confirmButtonColor": '#d33'
        }
    finally:
        pass

    return RedirectResponse(url="/", status_code=303)


@app.get("/medAtualizar", response_class=HTMLResponse)
async def med_atualizar(request: Request, id: int, db=Depends(get_db)):

    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para acessar esta página.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    medico = None
    especialidades = []
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM Medico WHERE ID_Medico = %s", (id,))
            medico = cursor.fetchone()
            cursor.execute("SELECT ID_Espec, Nome_Espec FROM Especialidade")
            especialidades = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar médico ou especialidades para atualização: {e}")

    if not medico:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Médico Não Encontrado",
            "text": "O médico que você tentou atualizar não foi encontrado.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    nome_usuario = request.session.get("nome_usuario", None)
    swal_message = request.session.pop("swal_message", None)

    return templates.TemplateResponse("medAtualizar.html", {
        "request": request,
        "med": medico,
        "especialidades": especialidades,
        "hoje": hoje,
        "nome_usuario": nome_usuario,
        "swal_message": swal_message
    })

@app.post("/medAtualizar_exe")
async def med_atualizar_exe(
    request: Request,
    id: int = Form(...),
    Nome: str = Form(...),
    CRM: str = Form(...),
    Especialidade: str = Form(...),
    DataNasc: Optional[str] = Form(None),
    Imagem: UploadFile = File(None),
    db=Depends(get_db)
):
    if not request.session.get("user_logged_in"):
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Login Necessário",
            "text": "Você precisa estar logado para acessar esta página.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)
    if request.session.get("cargo") != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    foto_bytes = None
    if Imagem and Imagem.filename:
        foto_bytes = await Imagem.read()

    try:
        with db.cursor() as cursor:
            if not foto_bytes:
                cursor.execute("SELECT Foto FROM Medico WHERE ID_Medico = %s", (id,))
                result = cursor.fetchone()
                if result:
                    foto_bytes = result['Foto']

            sql = """UPDATE Medico
                     SET Nome=%s, CRM=%s, Dt_Nasc=%s, ID_Espec=%s, Foto=%s
                     WHERE ID_Medico=%s"""
            cursor.execute(sql, (Nome, CRM, DataNasc, Especialidade, foto_bytes, id))
            db.commit()

        request.session["swal_message"] = {
            "icon": "success",
            "title": "Atualização de Médico",
            "text": "Registro atualizado com sucesso!",
            "confirmButtonColor": '#303030'
        }

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Atualizar",
            "text": f"Erro ao atualizar médico: {str(e)}",
            "confirmButtonColor": '#d33'
        }
    finally:
        pass

    return RedirectResponse(url="/", status_code=303)


@app.post("/reset_session")
async def reset_session(request: Request):
    request.session.pop("swal_message", None) # Limpa apenas o swal_message
    return {"status": "ok"}

Mangum(app)