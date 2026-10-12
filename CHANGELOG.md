# Log do projeto CallMed / AgendaMed

## 2026-10-11 — Preparação para publicação em nuvem

- Definida a arquitetura de produção: frontend no Netlify, API no Render e
  MongoDB Atlas como banco gerenciado.
- Preparado o backend para conectar diretamente ao MongoDB Atlas com
  `MONGO_URI` e `DB_NAME` fornecidos como variáveis do ambiente do Render; o
  repositório local `CallMed-Banco-de-dados` não é necessário em produção.
- Adicionado `render.yaml` para criar o serviço WSGI do backend no Render,
  usando Gunicorn e `/api/health` como health check.
- Preparado `netlify.toml` para publicação do frontend estático.
- Configurado o frontend para escolher a API local no desenvolvimento e a URL
  HTTPS do Render em produção; a URL final deve ser confirmada após criar o
  serviço.
- Documentados os passos para configurar `CORS_ORIGINS`, restringir o acesso
  do Atlas aos IPs/CIDRs de saída do Render e guardar credenciais nos painéis
  dos provedores.
- **Estado:** os sites/serviços ainda não foram publicados; URLs finais,
  URI do Atlas e regras de rede continuam pendentes de configuração.
- Validação do backend: 34 testes passaram. Sintaxe dos scripts do frontend
  validada com `node --check`.

## 2026-10-11 — Conversa mais acolhedora e funcional

- Conectado o chat das páginas de paciente à triagem conversacional salva no
  backend, com recuperação e início de conversas e atalhos para dúvidas comuns.
- Adicionadas respostas para saudações, pedidos de esclarecimento e dúvidas
  sobre diagnóstico, medicamentos, triagem e agendamento, sem interromper a
  checagem de sinais de urgência.
- Mantida a proteção: o assistente informa que não é profissional de saúde,
  não diagnostica nem recomenda medicamentos; sinais urgentes continuam
  direcionados ao atendimento de emergência.
- Criado um modo de ajuda para a área da clínica, com consultas simples ao
  cadastro de médicos e à quantidade de agendamentos, sem expor detalhes
  pessoais de pacientes na conversa.
- Corrigido o envio do token de autenticação do frontend para as rotas
  protegidas da API.
- Validação do backend e do fluxo de conversa registrados nos testes
  automatizados.

> As anotações abaixo registram o histórico inicial do projeto e descrevem a
> configuração daquela época. Para o estado atual e o deploy, consulte o
> README; as referências antigas a banco JSON local não descrevem a
> arquitetura planejada para produção.

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

### Trabalho realizado em 2026-09-22

#### Limpeza do banco local

- Mantidos somente três logins essenciais:
  - `admin@AgendaMed.com`
  - `altemar@clinica.com`
  - `sabrina@AgendaMed.com`
- Removidos usuários duplicados criados durante os testes.
- Removidos pacientes duplicados e agendamentos repetidos.
- Mantidos dois médicos demo, um paciente, um agendamento e um histórico base.
- Padronizados os campos do banco para o formato usado pelo frontend, como `pacienteId` e `medicoId`.

#### Matchmaking prioritário

- O fluxo principal passou a priorizar especialidade compatível e disponibilidade real:

```text
Necessidade -> Triagem -> Matchmaking -> Disponibilidade -> Agendamento
```

- Médicos com horário ocupado não são recomendados para aquele horário.
- Médicos ativos recebem prioridade adicional.
- O retorno informa a prioridade aplicada, como `especialidade_e_disponibilidade`.
- Ampliado o reconhecimento de necessidades para Urologia, Alergologia, Nutrologia e Geriatria.
- Matchmaking passou a aceitar `pacienteId` e `paciente_id`.
- Triagem passou a aceitar os mesmos formatos de identificação.
- Corrigido erro 500 causado por uma referência antiga à lista de horários ocupados.

#### Disponibilidade e clínicas

- Criada a rota `GET /api/medicos/<id>/disponibilidade`.
- A rota informa horários disponíveis e ocupados por data.
- Implementada atualização de clínicas existentes.
- Criada a exclusão de clínicas com `DELETE /api/clinicas/<id>`.
- Conectado o CRUD de clínicas do frontend à API.

#### Limpeza e conexão do frontend

- Removido código demo desativado do `js/app.js`.
- Corrigido o CRUD de clínicas para aguardar operações assíncronas.
- Criado `Storage.buscarTriagem()`.
- Criado `Storage.buscarMatchmakingPrioritario()`.
- A agenda passou a enviar nomes e especialidades do paciente e do médico.
- O frontend passou a disparar `storageReady` após carregar os dados da API.

#### Validação realizada hoje

- Banco validado com 3 usuários, 1 paciente e 1 agendamento.
- Login do paciente validado com status `200`.
- Matchmaking validado com status `200`, retornando Cardiologia para dor no peito e falta de ar.
- `app.py` validado com `py_compile`.
- Frontend validado com `node --check`.
- Suíte atualizada para 9 testes e resultado final:

```text
Ran 9 tests
OK
```

### Testes e validações

- Criado e atualizado `test_backend.py`.
- Testados health check, login, médicos, triagem, matchmaking, histórico, cadastro, agenda, perfil e exclusões.
- Última execução registrada:

```text
Ran 9 tests
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
