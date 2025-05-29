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
    "password": "PUC@1234",
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

# ... (seus imports e configurações existentes) ...

# Certifique-se de que esta função existe para buscar os cargos
def fetch_all_cargos(db: pymysql.Connection) -> List[Dict[str, Any]]:
    with db.cursor() as cursor:
        # Assumindo que sua tabela de cargos se chama 'cargo' e tem 'id_cargo' e 'nome'
        cursor.execute("SELECT id_cargo, nome FROM cargo ORDER BY nome")
        return cursor.fetchall()

# --- ROTA PARA EXIBIR O FORMULÁRIO DE CADASTRO DE FUNCIONÁRIO (GET) ---
@app.get("/cadastro-funcionario", response_class=HTMLResponse)
async def cadastrar_funcionario_form(request: Request, db: pymysql.Connection = Depends(get_db)):
    # Lógica de autorização: Apenas administradores (cargo_id=1) podem acessar esta página
    logged_in_cargo = request.session.get("cargo")
    if not request.session.get("user_logged_in") or logged_in_cargo != 1:
        request.session["swal_message"] = {
            "icon": "warning",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para cadastrar funcionários.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)

    swal_message = request.session.pop("swal_message", None)

    cargos = []
    try:
        cargos = fetch_all_cargos(db)
        # Filtre os cargos se necessário, por exemplo, não permitir que um admin
        # cadastre um usuário com cargo de cliente por esta tela.
        # Exemplo: cargos = [c for c in cargos if c['id_cargo'] in [1, 2, 3]] # Admin, Gerente, Funcionário
    except Exception as e:
        print(f"Erro ao buscar cargos para cadastro de funcionário: {e}")
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro",
            "text": "Erro ao carregar cargos.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)


    return templates.TemplateResponse("cadastro-funcionario.html", {
        "request": request,
        "nome_usuario": request.session.get("nome_usuario"),
        "user_logged_in": request.session.get("user_logged_in"),
        "cargo": logged_in_cargo,
        "swal_message": swal_message,
        "cargos": cargos # Passa a lista de cargos para o template HTML
    })

# --- ROTA PARA PROCESSAR O CADASTRO DE FUNCIONÁRIO (POST) ---
@app.post("/cadastro-funcionario", name="criar_funcionario_post") # Nomeando a rota para referência
async def criar_funcionario_post(
    request: Request,
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None), # Recebe como string "YYYY-MM-DD"
    cpf: str = Form(...),
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    cargo: int = Form(...), # O ID do cargo selecionado
    imagem_funcionario: UploadFile = File(None), # Nome do campo no HTML é 'imagem_funcionario'
    db: pymysql.Connection = Depends(get_db)
):
    # Lógica de autorização: Apenas administradores (cargo_id=1) podem cadastrar funcionários
    logged_in_cargo = request.session.get("cargo")
    if not request.session.get("user_logged_in") or logged_in_cargo != 1:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você não tem permissão para cadastrar funcionários.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    try:
        with db.cursor() as cursor:
            # Validação: CPF já cadastrado?
            cursor.execute("SELECT id_usuario FROM usuario WHERE cpf = %s", (cpf,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Funcionário",
                    "text": "Erro: Este CPF já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-funcionario", status_code=303)
            
            # Validação: E-mail já cadastrado?
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s", (email,))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Cadastro de Funcionário",
                    "text": "Erro: Este e-mail já está cadastrado!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/cadastro-funcionario", status_code=303)

            imagem_bytes = None
            if imagem_funcionario and imagem_funcionario.filename and imagem_funcionario.size > 0:
                # Opcional: Validar tamanho do arquivo aqui
                # if imagem_funcionario.size > 5 * 1024 * 1024: # Ex: 5MB
                #    request.session["swal_message"] = {"icon": "error", "title": "Erro", "text": "Imagem muito grande."}
                #    return RedirectResponse(url="/cadastro-funcionario", status_code=303)
                imagem_bytes = await imagem_funcionario.read()

            data_nascimento_sql = None
            if dataNascimento:
                try:
                    data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()
                except ValueError:
                    # Lidar com formato de data inválido, se necessário
                    request.session["swal_message"] = {
                        "icon": "error", "title": "Erro", "text": "Formato de data de nascimento inválido."
                    }
                    return RedirectResponse(url="/cadastro-funcionario", status_code=303)

            # Inserir o novo funcionário (na tabela 'usuario')
            # ATENÇÃO: Seu formulário de funcionário não tem campo de SENHA.
            # Você precisará decidir como a senha será definida para um funcionário.
            # Opções:
            # 1. Gerar uma senha aleatória e enviar por e-mail (complexo).
            # 2. Definir uma senha padrão inicial que o funcionário deve trocar.
            # 3. Adicionar um campo de senha ao formulário de cadastro de funcionário.
            # Por enquanto, vou usar uma senha padrão (ex: "carlink123").
            # Em produção, NUNCA use uma senha padrão como essa.
            
            # Use o nome da coluna 'dataNascimento' como está no seu HTML/DB para a data
            sql = """
                INSERT INTO usuario
                (nome, genero, dataNascimento, cpf, email, telefone, senha, cargo_id, imagemPerfil)
                VALUES (%s, %s, %s, %s, %s, %s, MD5(%s), %s, %s)
            """
            
            # Exemplo de senha padrão (altere conforme sua necessidade)
            # Ou adicione um campo de senha no HTML e receba com Form(...)
            senha_padrao = "carlink123" 

            cursor.execute(sql, (
                nome, genero, data_nascimento_sql, cpf, email,
                telefone, senha_padrao, cargo, imagem_bytes
            ))
            db.commit()

            cursor.execute("SELECT LAST_INSERT_ID() as id_usuario")
            new_funcionario_id = cursor.fetchone()['id_usuario']

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Cadastro de Funcionário",
                "text": f"Funcionário {nome} (ID: {new_funcionario_id}) cadastrado com sucesso!",
                "confirmButtonColor": '#303030'
            }
            return RedirectResponse(url="/cadastro-funcionario", status_code=303)

    except Exception as e:
        # Captura qualquer outro erro que possa ocorrer
        print(f"Erro ao cadastrar funcionário: {e}")
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Cadastrar Funcionário",
            "text": f"Ocorreu um erro: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/cadastro-funcionario", status_code=303)

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
    if request.session.get("user_logged_in"):
        return RedirectResponse(url="/", status_code=303)
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
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

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
    cargo_id: Optional[int] = Form(4), # Defino o default como 2 (usuário comum)
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
            # Use imagemPerfil, que é o nome do parâmetro da função
            if imagemPerfil and imagemPerfil.filename: # <-- CORRIGIDO AQUI!
                imagem_bytes = await imagemPerfil.read() # <-- E AQUI!

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
            final_cargo_id = cargo_id if request.session.get("cargo") == 1 else 4


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
    cargo_id: Optional[int] = Form(4), # Default para usuário comum
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
            final_cargo_id = cargo_id if request.session.get("cargo") == 1 else 4

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
    nome_usuario = request.session.get("nome_usuario")
    if not nome_usuario:
        return RedirectResponse("/login", status_code=303)  # Redireciona para login se não estiver logado
    return templates.TemplateResponse("vender.html", {
        "request": request,
        "nome_usuario": nome_usuario
    })



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


def fetch_all_cargos(db: pymysql.Connection) -> List[Dict[str, Any]]:
    with db.cursor() as cursor:
        cursor.execute("SELECT id_cargo, nome FROM cargo ORDER BY nome")
        return cursor.fetchall()

@app.get("/usuariosListar", name="usuariosListar", response_class=HTMLResponse)
async def listar_usuarios(request: Request, db: pymysql.Connection = Depends(get_db)):
    if not request.session.get("user_logged_in"): # Basic login check
        request.session["swal_message"] = {"icon": "warning", "title": "Acesso Negado", "text": "Você precisa estar logado."}
        return RedirectResponse(url="/login", status_code=303)

    # Admin or Gerente can view this list (as per original code cargo 1 or 2)
    # However, the original SQL filters for cargo_id = 4 (Usuários/Clientes)
    # And edit/delete buttons are only for cargo == 1 (Admin)
    logged_in_cargo = request.session.get("cargo")
    if logged_in_cargo not in (1, 2): # Assuming Admin (1) or Gerente (2) can access list pages
        request.session["swal_message"] = {"icon": "error", "title": "Acesso Negado", "text": "Você não tem permissão para ver esta lista."}
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        # This query specifically lists "Usuários" (Clientes) with cargo_id = 4
        sql = """
                SELECT U.id_usuario, U.nome, U.genero, U.dataNascimento, U.cpf,
                U.email, U.telefone, U.imagemPerfil, U.cargo_id, C.nome AS cargo_nome
                FROM usuario AS U
                LEFT JOIN cargo AS C ON U.cargo_id = C.id_cargo
                WHERE U.cargo_id = 4
                ORDER BY U.nome
                """
        cursor.execute(sql)
        usuarios = cursor.fetchall()

    # Fetch all cargos for the edit modal dropdown
    todos_os_cargos = fetch_all_cargos(db) # You'll need this for the edit modal

    hoje = date.today()
    for usuario in usuarios:
        # ... (your existing age and image processing logic for usuarios) ...
        dt_nasc = usuario["dataNascimento"]
        if dt_nasc:
            if isinstance(dt_nasc, str): # Should be date object from DB
                try:
                    dt_nasc = datetime.strptime(dt_nasc, "%Y-%m-%d").date()
                    usuario["dataNascimento"] = dt_nasc # Ensure it's a date object
                except ValueError:
                    pass # Keep original if format is unexpected

            if isinstance(dt_nasc, date): # Check if it's a date object
                idade = hoje.year - dt_nasc.year
                if (dt_nasc.month, dt_nasc.day) > (hoje.month, hoje.day):
                    idade -= 1
                usuario["idade"] = idade # This was missing, add if needed in template
            else:
                usuario["idade"] = "N/A"
        else:
            usuario["idade"] = "N/A"

        if usuario["imagemPerfil"]:
            if isinstance(usuario["imagemPerfil"], bytearray):
                usuario["imagemPerfil"] = bytes(usuario["imagemPerfil"])
            usuario["imagemPerfil_base64"] = "data:image/jpeg;base64," + base64.b64encode(usuario["imagemPerfil"]).decode('utf-8')
        else:
            usuario["imagemPerfil_base64"] = None


    nome_usuario_sessao = request.session.get("nome_usuario", "Visitante")
    swal_message = request.session.pop("swal_message", None)
    agora_formatado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return templates.TemplateResponse("usuariosListar.html", {
        "request": request,
        "usuarios": usuarios,
        "todos_os_cargos": todos_os_cargos, # Pass cargos to the template
        "hoje": agora_formatado,
        "nome_usuario": nome_usuario_sessao, # Ensure this is what you want for 'nome_usuario' in template
        "user_logged_in": request.session.get("user_logged_in", False), # Pass login status
        "cargo": logged_in_cargo, # Pass user's own cargo
        "swal_message": swal_message
    })


@app.post("/usuario/atualizar_perfil_admin", name="atualizar_usuario_admin")
async def atualizar_usuario_admin(
    request: Request,
    id_usuario: int = Form(...),
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None), # Expected as YYYY-MM-DD string
    # cpf: str = Form(...), # CPF should generally not be updatable this way. If needed, add it.
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    cargo_id: int = Form(...),
    imagemPerfil: Optional[UploadFile] = File(None),
    remover_imagem_perfil: Optional[bool] = Form(False), # Checkbox value
    db: pymysql.Connection = Depends(get_db)
):
    if request.session.get("cargo") != 1: # Only Admin
        request.session["swal_message"] = {
            "icon": "error", "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação."
        }
        return RedirectResponse(url="/usuariosListar", status_code=303)

    try:
        with db.cursor() as cursor:
            # Check if email (if changed) is already in use by another user
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s AND id_usuario != %s", (email, id_usuario))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error", "title": "Erro na Atualização",
                    "text": "Este e-mail já está em uso por outro usuário.",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/usuariosListar", status_code=303)

            data_nascimento_sql = None
            if dataNascimento:
                try:
                    data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()
                except ValueError:
                    # Handle invalid date format if necessary, or let DB handle it
                    pass
            
            imagem_bytes_db = None
            update_image_sql_part = ""

            if remover_imagem_perfil:
                imagem_bytes_db = None
                update_image_sql_part = ", imagemPerfil = %s"
            elif imagemPerfil and imagemPerfil.filename:
                # Check file size (example: max 5MB)
                if imagemPerfil.size > 5 * 1024 * 1024:
                    request.session["swal_message"] = {
                        "icon": "error", "title": "Erro na Atualização",
                        "text": "A imagem é muito grande (máximo 5MB).",
                        "confirmButtonColor": '#d33'}
                    return RedirectResponse(url="/usuariosListar", status_code=303)
                
                imagem_bytes_db = await imagemPerfil.read()
                update_image_sql_part = ", imagemPerfil = %s"
            
            # Construct SQL query
            # Note: CPF is not included in this update for safety. If it must be updatable, add it carefully.
            sql_base = """
                UPDATE usuario SET
                nome = %s, genero = %s, dataNascimento = %s, email = %s,
                telefone = %s, cargo_id = %s
            """
            params = [nome, genero, data_nascimento_sql, email, telefone, cargo_id]

            if update_image_sql_part: # If image is being updated or removed
                sql_base += update_image_sql_part
                params.append(imagem_bytes_db)
            
            sql_base += " WHERE id_usuario = %s"
            params.append(id_usuario)
            
            cursor.execute(sql_base, tuple(params))
            db.commit()

            request.session["swal_message"] = {
                "icon": "success", "title": "Atualização de Usuário",
                "text": f"Usuário '{nome}' (ID: {id_usuario}) atualizado com sucesso!",
                "confirmButtonColor": '#303030'
            }
    except pymysql.MySQLError as db_err:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro de Banco de Dados",
            "text": f"Erro ao atualizar usuário: {db_err}",
            "confirmButtonColor": '#d33'}
    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro na Atualização",
            "text": f"Erro ao atualizar usuário: {str(e)}",
            "confirmButtonColor": '#d33'}
    
    return RedirectResponse(url="/usuariosListar", status_code=303)


@app.post("/usuario/excluir_perfil_admin", name="excluir_usuario_admin")
async def excluir_usuario_admin(
    request: Request,
    id_usuario: int = Form(...),
    db: pymysql.Connection = Depends(get_db)
):
    if request.session.get("cargo") != 1: # Only Admin
        request.session["swal_message"] = {
            "icon": "error", "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação."
        }
        return RedirectResponse(url="/usuariosListar", status_code=303)

    # Prevent admin from deleting themselves (optional safeguard)
    # current_user_id = request.session.get("id_usuario") # You'd need to store id_usuario in session at login
    # if current_user_id == id_usuario:
    #     request.session["swal_message"] = {"icon": "error", "title": "Operação Inválida", "text": "Você não pode excluir sua própria conta."}
    #     return RedirectResponse(url="/usuariosListar", status_code=303)

    try:
        with db.cursor() as cursor:
            # You might want to check for related data before deleting (e.g., if user has cars listed)
            # For now, direct delete:
            cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
            db.commit()

            if cursor.rowcount > 0:
                request.session["swal_message"] = {
                    "icon": "success", "title": "Exclusão de Usuário",
                    "text": f"Usuário ID: {id_usuario} excluído com sucesso.",
                    "confirmButtonColor": '#303030'
                }
            else:
                request.session["swal_message"] = {
                    "icon": "warning", "title": "Exclusão de Usuário",
                    "text": f"Usuário ID: {id_usuario} não encontrado ou já excluído.",
                    "confirmButtonColor": '#d33'
                }
    except pymysql.MySQLError as db_err: # Catch potential foreign key constraint errors, etc.
        error_text = f"Erro ao excluir usuário: {db_err}"
        if db_err.args[0] == 1451: # Cannot delete or update a parent row: a foreign key constraint fails
             error_text = "Não é possível excluir este usuário pois ele possui registros associados (ex: carros cadastrados). Remova os registros associados primeiro."
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro de Banco de Dados",
            "text": error_text,
            "confirmButtonColor": '#d33'}

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro na Exclusão",
            "text": f"Erro ao excluir usuário: {str(e)}",
            "confirmButtonColor": '#d33'}
            
    return RedirectResponse(url="/usuariosListar", status_code=303)

@app.get("/funcionariosListar", name="funcionariosListar", response_class=HTMLResponse)
async def listar_usuarios(request: Request, db: pymysql.Connection = Depends(get_db)):
    if not request.session.get("user_logged_in"): # Basic login check
        request.session["swal_message"] = {"icon": "warning", "title": "Acesso Negado", "text": "Você precisa estar logado."}
        return RedirectResponse(url="/login", status_code=303)

    # Admin or Gerente can view this list (as per original code cargo 1 or 2)
    # However, the original SQL filters for cargo_id = 4 (Usuários/Clientes)
    # And edit/delete buttons are only for cargo == 1 (Admin)
    logged_in_cargo = request.session.get("cargo")
    if logged_in_cargo not in (1, 2): # Assuming Admin (1) or Gerente (2) can access list pages
        request.session["swal_message"] = {"icon": "error", "title": "Acesso Negado", "text": "Você não tem permissão para ver esta lista."}
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        # This query specifically lists "Usuários" (Clientes) with cargo_id = 4
        sql = """
                SELECT U.id_usuario, U.nome, U.genero, U.dataNascimento, U.cpf,
                U.email, U.telefone, U.imagemPerfil, U.cargo_id, C.nome AS cargo_nome
                FROM usuario AS U
                LEFT JOIN cargo AS C ON U.cargo_id = C.id_cargo
                WHERE U.cargo_id IN (1, 2, 3)
                ORDER BY U.nome
                """
        cursor.execute(sql)
        usuarios = cursor.fetchall()

    # Fetch all cargos for the edit modal dropdown
    todos_os_cargos = fetch_all_cargos(db) # You'll need this for the edit modal

    hoje = date.today()
    for usuario in usuarios:
        # ... (your existing age and image processing logic for usuarios) ...
        dt_nasc = usuario["dataNascimento"]
        if dt_nasc:
            if isinstance(dt_nasc, str): # Should be date object from DB
                try:
                    dt_nasc = datetime.strptime(dt_nasc, "%Y-%m-%d").date()
                    usuario["dataNascimento"] = dt_nasc # Ensure it's a date object
                except ValueError:
                    pass # Keep original if format is unexpected

            if isinstance(dt_nasc, date): # Check if it's a date object
                idade = hoje.year - dt_nasc.year
                if (dt_nasc.month, dt_nasc.day) > (hoje.month, hoje.day):
                    idade -= 1
                usuario["idade"] = idade # This was missing, add if needed in template
            else:
                usuario["idade"] = "N/A"
        else:
            usuario["idade"] = "N/A"

        if usuario["imagemPerfil"]:
            if isinstance(usuario["imagemPerfil"], bytearray):
                usuario["imagemPerfil"] = bytes(usuario["imagemPerfil"])
            usuario["imagemPerfil_base64"] = "data:image/jpeg;base64," + base64.b64encode(usuario["imagemPerfil"]).decode('utf-8')
        else:
            usuario["imagemPerfil_base64"] = None


    nome_usuario_sessao = request.session.get("nome_usuario", "Visitante")
    swal_message = request.session.pop("swal_message", None)
    agora_formatado = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return templates.TemplateResponse("funcionariosListar.html", {
        "request": request,
        "usuarios": usuarios,
        "todos_os_cargos": todos_os_cargos, # Pass cargos to the template
        "hoje": agora_formatado,
        "nome_usuario": nome_usuario_sessao, # Ensure this is what you want for 'nome_usuario' in template
        "user_logged_in": request.session.get("user_logged_in", False), # Pass login status
        "cargo": logged_in_cargo, # Pass user's own cargo
        "swal_message": swal_message
    })


@app.post("/funcionarios/atualizar_perfil_admin", name="atualizar_funcionario_admin")
async def atualizar_usuario_admin(
    request: Request,
    id_usuario: int = Form(...),
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None), # Expected as YYYY-MM-DD string
    # cpf: str = Form(...), # CPF should generally not be updatable this way. If needed, add it.
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    cargo_id: int = Form(...),
    imagemPerfil: Optional[UploadFile] = File(None),
    remover_imagem_perfil: Optional[bool] = Form(False), # Checkbox value
    db: pymysql.Connection = Depends(get_db)
):
    if request.session.get("cargo") != 1: # Only Admin
        request.session["swal_message"] = {
            "icon": "error", "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação."
        }
        return RedirectResponse(url="/funcionariosListar", status_code=303)

    try:
        with db.cursor() as cursor:
            # Check if email (if changed) is already in use by another user
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s AND id_usuario != %s", (email, id_usuario))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error", "title": "Erro na Atualização",
                    "text": "Este e-mail já está em uso por outro usuário.",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/funcionariosListar", status_code=303)

            data_nascimento_sql = None
            if dataNascimento:
                try:
                    data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()
                except ValueError:
                    # Handle invalid date format if necessary, or let DB handle it
                    pass
            
            imagem_bytes_db = None
            update_image_sql_part = ""

            if remover_imagem_perfil:
                imagem_bytes_db = None
                update_image_sql_part = ", imagemPerfil = %s"
            elif imagemPerfil and imagemPerfil.filename:
                # Check file size (example: max 5MB)
                if imagemPerfil.size > 5 * 1024 * 1024:
                    request.session["swal_message"] = {
                        "icon": "error", "title": "Erro na Atualização",
                        "text": "A imagem é muito grande (máximo 5MB).",
                        "confirmButtonColor": '#d33'}
                    return RedirectResponse(url="/funcionariosListar", status_code=303)
                
                imagem_bytes_db = await imagemPerfil.read()
                update_image_sql_part = ", imagemPerfil = %s"
            
            # Construct SQL query
            # Note: CPF is not included in this update for safety. If it must be updatable, add it carefully.
            sql_base = """
                UPDATE usuario SET
                nome = %s, genero = %s, dataNascimento = %s, email = %s,
                telefone = %s, cargo_id = %s
            """
            params = [nome, genero, data_nascimento_sql, email, telefone, cargo_id]

            if update_image_sql_part: # If image is being updated or removed
                sql_base += update_image_sql_part
                params.append(imagem_bytes_db)
            
            sql_base += " WHERE id_usuario = %s"
            params.append(id_usuario)
            
            cursor.execute(sql_base, tuple(params))
            db.commit()

            request.session["swal_message"] = {
                "icon": "success", "title": "Atualização de Usuário",
                "text": f"Usuário '{nome}' (ID: {id_usuario}) atualizado com sucesso!",
                "confirmButtonColor": '#303030'
            }
    except pymysql.MySQLError as db_err:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro de Banco de Dados",
            "text": f"Erro ao atualizar usuário: {db_err}",
            "confirmButtonColor": '#d33'}
    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro na Atualização",
            "text": f"Erro ao atualizar usuário: {str(e)}",
            "confirmButtonColor": '#d33'}
    
    return RedirectResponse(url="/funcionariosListar", status_code=303)


@app.post("/funcionarios/excluir_perfil_admin", name="excluir_funcionarios_admin")
async def excluir_usuario_admin(
    request: Request,
    id_usuario: int = Form(...),
    db: pymysql.Connection = Depends(get_db)
):
    if request.session.get("cargo") != 1: # Only Admin
        request.session["swal_message"] = {
            "icon": "error", "title": "Acesso Negado",
            "text": "Você não tem permissão para realizar esta operação."
        }
        return RedirectResponse(url="/funcionariosListar", status_code=303)

    # Prevent admin from deleting themselves (optional safeguard)
    # current_user_id = request.session.get("id_usuario") # You'd need to store id_usuario in session at login
    # if current_user_id == id_usuario:
    #     request.session["swal_message"] = {"icon": "error", "title": "Operação Inválida", "text": "Você não pode excluir sua própria conta."}
    #     return RedirectResponse(url="/usuariosListar", status_code=303)

    try:
        with db.cursor() as cursor:
            # You might want to check for related data before deleting (e.g., if user has cars listed)
            # For now, direct delete:
            cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
            db.commit()

            if cursor.rowcount > 0:
                request.session["swal_message"] = {
                    "icon": "success", "title": "Exclusão de Usuário",
                    "text": f"Usuário ID: {id_usuario} excluído com sucesso.",
                    "confirmButtonColor": '#303030'
                }
            else:
                request.session["swal_message"] = {
                    "icon": "warning", "title": "Exclusão de Usuário",
                    "text": f"Usuário ID: {id_usuario} não encontrado ou já excluído.",
                    "confirmButtonColor": '#d33'
                }
    except pymysql.MySQLError as db_err: # Catch potential foreign key constraint errors, etc.
        error_text = f"Erro ao excluir usuário: {db_err}"
        if db_err.args[0] == 1451: # Cannot delete or update a parent row: a foreign key constraint fails
             error_text = "Não é possível excluir este usuário pois ele possui registros associados (ex: carros cadastrados). Remova os registros associados primeiro."
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro de Banco de Dados",
            "text": error_text,
            "confirmButtonColor": '#d33'}

    except Exception as e:
        request.session["swal_message"] = {
            "icon": "error", "title": "Erro na Exclusão",
            "text": f"Erro ao excluir usuário: {str(e)}",
            "confirmButtonColor": '#d33'}
            
    return RedirectResponse(url="/funcionariosListar", status_code=303)

@app.get("/carrosListar", name="carrosListar", response_class=HTMLResponse)
async def listar_carros(request: Request, db=Depends(get_db)):
    if not request.session.get("user_logged_in") or request.session.get("cargo") != 1:
        return RedirectResponse(url="/", status_code=303)

    with db.cursor() as cursor:
        sql = """
            SELECT C.id_carro, C.ano, C.placa, C.cor, C.renavam, C.chassi,
                   C.motor, C.potencia, C.preco, C.imagem, C.descricao,
                   M.nome AS nome_modelo, U.nome AS nome_usuario
            FROM carro AS C
            LEFT JOIN modelo AS M ON C.fk_id_modelo = M.id_modelo
            LEFT JOIN usuario AS U ON C.fk_id_usuario = U.id_usuario
            ORDER BY C.id_carro DESC
        """
        cursor.execute(sql)
        carros = cursor.fetchall()

    for carro in carros:
        carro["ano"] = carro["ano"].strftime("%Y") if carro["ano"] else "N/A"
        carro["preco"] = f"R$ {carro['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return templates.TemplateResponse("carrosListar.html", {
        "request": request,
        "carros": carros,
        "hoje": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nome_usuario": request.session.get("nome_usuario", "Visitante"),
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

@app.get("/perfil", response_class=HTMLResponse)
async def perfil_usuario(request: Request, db=Depends(get_db)):
    id_usuario = request.session.get("id_usuario")
    if not id_usuario:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você precisa estar logado para acessar seu perfil.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/login", status_code=303) # Redireciona para o login se não estiver logado

    usuario_data = None
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id_usuario, nome, genero, dataNascimento, cpf, email, telefone, imagemPerfil, cargo_id
                FROM usuario
                WHERE id_usuario = %s
            """, (id_usuario,))
            usuario_data = cursor.fetchone()

            if usuario_data:
                # Converte o campo BLOB (imagemPerfil) para base64 para exibição no HTML
                if usuario_data.get("imagemPerfil"):
                    if isinstance(usuario_data["imagemPerfil"], bytes):
                        usuario_data["imagem_url"] = "data:image/jpeg;base64," + base64.b64encode(usuario_data["imagemPerfil"]).decode('utf-8')
                    else:
                        usuario_data["imagem_url"] = usuario_data["imagemPerfil"]
                else:
                    usuario_data["imagem_url"] = "/static/imagens/default_profile.png" # Imagem padrão se não houver

                # Formata a data de nascimento para o formato YYYY-MM-DD para o input type="date"
                if usuario_data.get("dataNascimento"):
                    usuario_data["dataNascimento"] = usuario_data["dataNascimento"].strftime("%Y-%m-%d")
            else:
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Erro",
                    "text": "Dados do perfil não encontrados. Por favor, faça login novamente.",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/logout", status_code=303)

    except Exception as e:
        print(f"Erro ao carregar perfil do usuário {id_usuario}: {e}")
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro",
            "text": f"Erro ao carregar dados do perfil: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/", status_code=303)

    swal_message = request.session.pop("swal_message", None)
    nome_usuario = request.session.get("nome_usuario")

    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "usuario": usuario_data,
        "swal_message": swal_message,
        "nome_usuario": nome_usuario
    })

# Rota POST para processar as edições do perfil do usuário
@app.post("/perfil/editar", name="editar_perfil")
async def editar_perfil(
    request: Request,
    nome: str = Form(...),
    genero: Optional[str] = Form(None),
    dataNascimento: Optional[str] = Form(None),
    email: str = Form(...),
    telefone: Optional[str] = Form(None),
    senha: Optional[str] = Form(None), # Senha é opcional
    imagemPerfil: UploadFile = File(None), # Imagem também é opcional
    db = Depends(get_db)
):
    id_usuario = request.session.get("id_usuario")
    if not id_usuario:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você precisa estar logado para editar seu perfil.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/login", status_code=303)

    try:
        with db.cursor() as cursor:
            # 1. Validação de E-mail: Verificar se o novo e-mail já não está em uso por OUTRO usuário
            cursor.execute("SELECT id_usuario FROM usuario WHERE email = %s AND id_usuario != %s", (email, id_usuario))
            if cursor.fetchone():
                request.session["swal_message"] = {
                    "icon": "error",
                    "title": "Edição de Perfil",
                    "text": "Erro: Este e-mail já está cadastrado por outro usuário!",
                    "confirmButtonColor": '#d33'
                }
                return RedirectResponse(url="/perfil", status_code=303)

            # 2. Processar a imagem de perfil
            imagem_bytes = None
            if imagemPerfil and imagemPerfil.filename and imagemPerfil.size > 0:
                imagem_bytes = await imagemPerfil.read()
            else: # Se nenhuma nova imagem foi enviada ou o campo estava vazio, tenta manter a existente
                cursor.execute("SELECT imagemPerfil FROM usuario WHERE id_usuario = %s", (id_usuario,))
                current_image_data = cursor.fetchone()
                if current_image_data and current_image_data["imagemPerfil"]:
                    imagem_bytes = current_image_data["imagemPerfil"]

            # 3. Converter data de nascimento
            data_nascimento_sql = None
            if dataNascimento:
                data_nascimento_sql = datetime.strptime(dataNascimento, "%Y-%m-%d").date()

            # 4. Preparar a atualização da senha
            update_senha_sql = ""
            senha_param = None
            if senha:
                update_senha_sql = ", senha = MD5(%s)"
                senha_param = senha

            # 5. Construir e executar a query de atualização
            sql = f"""
                UPDATE usuario
                SET nome = %s, genero = %s, dataNascimento = %s, email = %s, telefone = %s, imagemPerfil = %s
                {update_senha_sql}
                WHERE id_usuario = %s
            """

            params = [nome, genero, data_nascimento_sql, email, telefone, imagem_bytes]
            if senha_param:
                params.append(senha_param)
            params.append(id_usuario)

            cursor.execute(sql, tuple(params))
            db.commit()

            # Atualizar o nome do usuário na sessão, se for o caso
            request.session["nome_usuario"] = nome

            request.session["swal_message"] = {
                "icon": "success",
                "title": "Perfil Atualizado",
                "text": "Seu perfil foi atualizado com sucesso!",
                "confirmButtonColor": '#303030'
            }
            return RedirectResponse(url="/perfil", status_code=303)

    except Exception as e:
        print(f"Erro ao editar perfil do usuário {id_usuario}: {e}")
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro na Edição",
            "text": f"Erro ao atualizar perfil: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/perfil", status_code=303)

# Rota para exclusão de conta (implementação básica)
@app.get("/perfil/excluir")
async def excluir_perfil(request: Request, db=Depends(get_db)):
    id_usuario = request.session.get("id_usuario")
    if not id_usuario:
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Acesso Negado",
            "text": "Você precisa estar logado para excluir seu perfil.",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/login", status_code=303)

    try:
        with db.cursor() as cursor:
            # Você pode querer uma confirmação mais robusta aqui (senha, etc.)
            cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
            db.commit()

        request.session.clear()
        request.session["swal_message"] = {
            "icon": "success",
            "title": "Conta Excluída",
            "text": "Sua conta foi excluída com sucesso.",
            "confirmButtonColor": '#303030'
        }
        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        print(f"Erro ao excluir perfil do usuário {id_usuario}: {e}")
        request.session["swal_message"] = {
            "icon": "error",
            "title": "Erro ao Excluir",
            "text": f"Erro ao excluir conta: {str(e)}",
            "confirmButtonColor": '#d33'
        }
        return RedirectResponse(url="/perfil", status_code=303)

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