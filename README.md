# CallMed Backend 🏥

Backend da **CallMed**, desenvolvido em Python com Flask para gerenciamento de usuários, médicos, pacientes, clínicas e consultas.

O backend contém a API e as regras de negócio. A persistência JSON é apenas um
adaptador local temporário; não representa nem substitui o projeto separado de
banco de dados. A integração com esse projeto será implementada no repository
quando seu protocolo real estiver disponível.

## 🚀 Tecnologias

* Python 3
* Flask
* Flask-CORS
* `db.json` para desenvolvimento local
* unittest

## ✨ Funcionalidades

* Autenticação e cadastro de usuários
* Gerenciamento de médicos e pacientes
* Gerenciamento de clínicas
* Agenda e agendamento de consultas
* Atualização de perfil
* Histórico
* Triagem de pacientes
* Matchmaking entre pacientes e médicos
* Integração com o frontend AgendaMed

## 📦 Instalação

```bash
git clone <URL_DO_REPOSITORIO>
cd CallMed-backend

python -m venv .venv
```

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## ▶️ Executando

Copie `.env.example` para `.env` para personalizar as configurações locais.
O arquivo `.env` não deve ser versionado.

```bash
python app.py
```

A API estará disponível em:

```text
http://localhost:5000
```

### Health Check

```text
http://localhost:5000/api/health
```

## 🌐 Frontend

O frontend AgendaMed deve ser executado separadamente:

```bash
python -m http.server 5500
```

Acesse:

```text
http://localhost:5500/login.html
```

O frontend deve utilizar:

```javascript
const API_URL = 'http://localhost:5000/api';
```

## 🧪 Testes

```bash
python -m unittest test_backend.py
```

Validação da sintaxe:

```bash
python -m py_compile app.py
```

## ⚙️ Configuração

| Variável | Padrão | Uso |
| --- | --- | --- |
| `API_HOST` | `0.0.0.0` | Endereço de escuta do servidor de desenvolvimento |
| `API_PORT` | `5000` | Porta do servidor |
| `FLASK_DEBUG` | `true` | Modo de depuração local |
| `CORS_ORIGINS` | `*` | Origens CORS; múltiplas origens podem ser separadas por vírgula |
| `DATA_FILE` | `db.json` | Caminho do arquivo usado pelo repository JSON local |

Não há configuração de conexão com o banco separado neste projeto: o código
atual não informa protocolo, URL, credenciais ou tecnologia desse serviço.
