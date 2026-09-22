# CallMed Backend 🏥

Backend da **CallMed**, desenvolvido em Python com Flask para gerenciamento de usuários, médicos, pacientes, clínicas e consultas.

## 🚀 Tecnologias

* Python 3
* Flask
* Flask-CORS
* JSON
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

## 📌 Status

Backend funcional para integração local com o Callmed(front).

> Atualmente utiliza `db.json` para persistência local. Para produção, recomenda-se utilizar um banco de dados real e autenticação por token.
