# CallMed Backend

API REST da CallMed, desenvolvida em Python e Flask. O backend contém as rotas
e regras de negócio e acessa o MongoDB por meio do repository. O projeto de
banco de dados é separado.

## Requisitos

- Python 3.10 ou superior
- Acesso ao MongoDB usado pelo projeto `CallMed-Banco-de-dados`
- `MONGO_URI` e, se diferente do padrão, `DB_NAME`

## Instalação e execução (Windows)

No PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` e preencha `MONGO_URI` com a URI configurada para o MongoDB.
Depois inicie a API:

```powershell
python app.py
```

A API inicia por padrão em `http://localhost:5000`. Verifique se está ativa em
`http://localhost:5000/api/health`.

Em outros sistemas, crie e ative um ambiente virtual com `python -m venv .venv`,
instale `requirements.txt`, copie `.env.example` para `.env` e execute
`python app.py`.

## Configuração

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `API_HOST` | `0.0.0.0` | Interface de rede do servidor Flask local |
| `API_PORT` | `5000` | Porta HTTP |
| `FLASK_DEBUG` | `true` | Depuração do servidor de desenvolvimento; desative fora do ambiente local |
| `CORS_ORIGINS` | `*` | Origens autorizadas; várias origens podem ser separadas por vírgula |
| `MONGO_URI` | obrigatório | URI de conexão ao MongoDB; manter somente em variável de ambiente ou `.env` local |
| `DB_NAME` | `callmed` | Nome do banco MongoDB |

O `.env` é ignorado pelo Git. Não versione credenciais nem as copie para o
código. Se uma credencial real já foi commitada, removê-la do arquivo não a
revoga: troque a credencial no provedor do banco.

## Estrutura e responsabilidades

```text
app.py                 Cria a aplicação, instancia dependências e registra Blueprints
config/                Carrega configuração e variáveis de ambiente
routes/                Define URLs e métodos HTTP com Flask Blueprints
controllers/           Traduz requisições/respostas HTTP e chama services
services/              Regras de negócio, validação e coordenação
repositories/           Contrato de dados e implementação MongoDB/PyMongo
test_backend.py        Testes da API e do repository
```

Fluxo: **cliente → routes → controllers → services → repository → MongoDB**.

O repository mapeia os dados da API para as collections existentes em
`CallMed-Banco-de-dados/database.py`:

| Recurso da API | Collection |
| --- | --- |
| Usuários | `usuarios` |
| Médicos | `medicos` |
| Pacientes | `pacientes` |
| Clínicas | `clinicas` |
| Agenda e agendamentos | `agendamentos` |
| Histórico (`/api/historico`) | `logs` |
| Configuração global (`/api/config`) | `configuracoes` |

Os registros são consultados pelo campo numérico `id`; o `_id` interno do
MongoDB não é retornado pela API. `configuracoes` é tratado como um documento
global. `especialidades` e `configuracoes_usuario` existem no projeto de dados,
mas não são usadas pelas rotas atuais.

Um `db.json` legado que ainda exista na pasta não é lido nem atualizado pelo
backend. Ele não é removido automaticamente.

## Rotas da API

| Método | Rota | Uso |
| --- | --- | --- |
| `GET` | `/api/health` | Verifica o estado da API |
| `GET` | `/api/healthz` | Verificação alternativa de saúde |
| `POST` | `/api/login` | Login com `email` e `senha` |
| `POST` | `/api/cadastro` | Cadastro; aceita os aliases de perfil |
| `GET`, `POST` | `/api/usuarios` | Lista ou cria usuários |
| `GET` | `/api/usuarios/<id>` | Consulta um usuário |
| `GET`, `POST` | `/api/administradores` | Lista ou cria usuários administradores |
| `GET`, `PUT`, `DELETE` | `/api/administradores/<admin_id>` | Consulta, atualiza ou exclui administrador |
| `GET`, `PUT` | `/api/perfil/<usuario_id>` | Consulta ou atualiza perfil |
| `GET`, `POST` | `/api/medicos` | Lista ou cria médico; POST com `id` atualiza |
| `GET`, `PUT`, `DELETE` | `/api/medicos/<medico_id>` | Consulta, atualiza ou exclui médico |
| `GET` | `/api/medicos/<medico_id>/disponibilidade` | Consulta horários; aceita `data` e parâmetros repetidos `hora` |
| `GET`, `POST` | `/api/pacientes` | Lista ou cria paciente; POST com `id` atualiza |
| `GET`, `PUT`, `DELETE` | `/api/pacientes/<paciente_id>` | Consulta, atualiza ou exclui paciente |
| `GET`, `POST` | `/api/clinicas` | Lista, cria ou atualiza clínicas |
| `DELETE` | `/api/clinicas/<clinica_id>` | Exclui clínica |
| `GET`, `POST` | `/api/agendamentos` | Lista, cria ou atualiza agendamentos |
| `GET`, `PUT`, `DELETE` | `/api/agendamentos/<agendamento_id>` | Consulta, atualiza ou exclui agendamento |
| `GET`, `POST` | `/api/agenda` | Compatibilidade com a agenda legada do frontend |
| `DELETE` | `/api/agenda/<agendamento_id>` | Exclui agendamento |
| `GET`, `POST` | `/api/historico` | Lista ou adiciona histórico em `logs` |
| `GET`, `POST` | `/api/config` | Consulta ou atualiza a configuração global |
| `POST` | `/api/triagem` | Gera triagem e recomendações |
| `POST` | `/api/matchmaking` | Recomenda médicos por necessidade e disponibilidade |

IDs nas rotas são inteiros. `POST /api/matchmaking` aceita `paciente_id` ou
`pacienteId`; `POST /api/triagem` aceita os mesmos aliases. Ambos exigem
`necessidade`. A disponibilidade no matchmaking recebe `data` e `hora`
opcionais. As respostas mantêm os campos e formatos usados pelo frontend,
inclusive os aliases camelCase/snake_case de agendamentos e perfis.

Administradores são registros da collection `usuarios` com `tipoClinica:
admin` (ou `tipo: admin`). A criação por `/api/administradores` define
`tipo: clinica` e `tipoClinica: admin`; respostas de usuário nunca incluem
`senha`. O endpoint `/api/perfil/<usuario_id>` segue disponível para o
contrato existente do frontend.

O cadastro em `/api/cadastro` grava o usuário em `usuarios` e, para contas
`paciente`, cria também o perfil em `pacientes`. O agendamento exige IDs de
paciente e médico existentes, data e horário; os nomes/telefone/especialidade
são preenchidos a partir dos cadastros e o horário ocupado retorna `409`.
Criar ou atualizar usa `/api/agendamentos`; a rota `/api/agenda` permanece
compatível com o frontend legado.

**Atenção:** a API atualmente não possui autenticação/autorização por token.
As rotas CRUD, inclusive as de administrador, não devem ser expostas
publicamente até que uma camada de autenticação e autorização seja adicionada.

### Exemplo de requisição

```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"usuario@exemplo.com\",\"senha\":\"sua-senha\"}"
```

## Frontend

Execute o frontend separadamente e configure sua URL base para:

```javascript
const API_URL = 'http://localhost:5000/api';
```

Para servir arquivos estáticos locais, execute o servidor HTTP na pasta do
frontend, por exemplo `python -m http.server 5500`.

## Testes

Os testes usam um repository em memória e não se conectam ao banco real:

```powershell
python -m unittest -v test_backend
```

Para validar a sintaxe de todos os módulos Python:

```powershell
Get-ChildItem -Recurse -Filter *.py |
  Where-Object { $_.FullName -notmatch '\\.venv\\|__pycache__' } |
  ForEach-Object { python -m py_compile $_.FullName }
```

## Notas de operação

- `python app.py` usa o servidor de desenvolvimento do Flask. Desative
  `FLASK_DEBUG` fora do ambiente local e use um servidor WSGI apropriado para
  implantação.
- CORS está aberto por padrão para facilitar desenvolvimento. Defina
  `CORS_ORIGINS` com as origens necessárias no ambiente publicado.
- O login preserva o contrato atual da API; esta refatoração não implementa
  autenticação por token nem hashing/migração de senhas existentes. O formato
  atual armazena e compara a senha diretamente; não o exponha em produção sem
  implementar armazenamento seguro de senhas.
- O repository não contém dados de demonstração nem cria um banco local. Os
  testes mantêm seus dados isolados em memória.
