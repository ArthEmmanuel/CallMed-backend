# Log do projeto CallMed / AgendaMed

## 2026-09-21 a 2026-09-22



### Backend criado

- Criada uma API em Flask no arquivo `app.py`.
- Habilitado CORS para permitir que o frontend seja executado em outra pasta.
- Configurada persistência local em `db.json`.
- Adicionados dados iniciais de usuários, médicos, pacientes, agendamentos e histórico.
- Implementada lógica para mesclar dados padrão sem sobrescrever registros existentes.

### Ambiente e limpeza

- Mantido apenas um ambiente virtual Python em `.venv`.
- Removido o cache gerado `__pycache__/` durante a limpeza.
- Criado `.gitignore` para ignorar `.venv`, caches Python, arquivos compilados e o banco local `db.json`.

### Rotas principais

- `GET /api/health`
- `GET /api/healthz`
- `POST /api/login`
- `POST /api/cadastro`
- `GET/POST /api/usuarios`
- `GET /api/usuarios/<id>`
- `GET/POST /api/medicos`
- `GET/DELETE /api/medicos/<id>`
- `GET/POST /api/pacientes`
- `GET/DELETE /api/pacientes/<id>`
- `GET/POST /api/agendamentos`
- `GET/POST /api/agenda`
- `DELETE /api/agenda/<id>`
- `GET/PUT /api/perfil/<id>`
- `GET/POST /api/clinicas`
- `GET/POST /api/historico`
- `GET/POST /api/config`
- `POST /api/triagem`
- `POST /api/matchmaking`

### Compatibilidade com o frontend AgendaMed

- Analisado o frontend atualizado em `C:\Users\arthu\Downloads\AgendaMed`.
- Confirmado o uso de `api.js`, `storage.js`, login, cadastro, agenda, perfil e configurações.
- Criada a compatibilidade com campos em camelCase, como:
  - `pacienteId`
  - `medicoId`
  - `dataNascimento`
  - `pacienteNome`
  - `medicoNome`
  - `medicoEspecialidade`
- Mantida compatibilidade com registros antigos em snake_case, como `paciente_id` e `medico_id`.
- Implementada resposta sem senha no login, cadastro e consultas de usuário.
- Adicionada normalização de agendamentos antigos e novos.
- Corrigidas as rotas de exclusão usadas pelo frontend.
- Adicionada atualização de perfil por usuário.
- Adicionada lógica de triagem e recomendação de médicos por especialidade.

### Testes e validações

- Criado e atualizado `test_backend.py`.
- Testados health check, login, médicos, triagem, matchmaking, histórico, cadastro, agenda, perfil e exclusões.
- Última execução registrada:

```text
Ran 7 tests
OK
```

- `app.py` validado com `py_compile`.
- `api.js`, `storage.js` e `main.js` validados com `node --check`.

## Como executar

### Backend

```powershell
cd C:\Users\arthu\Downloads\CallMed-backend
.\.venv\Scripts\python.exe app.py
```

API disponível em:

```text
http://localhost:5000
```

### Frontend

```powershell
cd C:\Users\arthu\Downloads\AgendaMed
python -m http.server 5500
```

Frontend disponível em:

```text
http://localhost:5500/login.html
```

## Observações atuais

- O backend usa JSON local e ainda não possui autenticação por token.
- Fotos e algumas funções específicas de clínicas continuam locais no frontend.
- Antes de produção, será necessário trocar o banco JSON por um banco real e configurar variáveis de ambiente.
