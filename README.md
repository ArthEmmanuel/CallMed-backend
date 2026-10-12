# CallMed Backend

API REST da CallMed, construída com Python e Flask. Este repositório contém
as rotas HTTP, autenticação, validações e regras de negócio. Em produção, a
API conecta diretamente ao MongoDB Atlas por variáveis seguras no Render; o
projeto separado `CallMed-Banco-de-dados` é opcional e serve apenas à
configuração local legada.

> **GitHub não executa esta API.** GitHub armazena o código e pode automatizar
> o deploy com Actions; para executar Flask é necessário um host com suporte
> a Python/WSGI. GitHub Pages serve conteúdo estático e não hospeda este backend.

## Conteúdo

- [Tutorial rápido](#tutorial-rápido)
- [Requisitos](#requisitos)
- [Instalação e execução local](#instalação-e-execução-local)
- [Configuração de ambiente](#configuração-de-ambiente)
- [Banco de dados separado](#banco-de-dados-separado)
- [Arquitetura](#arquitetura)
- [Autenticação e autorização](#autenticação-e-autorização)
- [Rotas da API](#rotas-da-api)
- [Exemplos de uso](#exemplos-de-uso)
- [Publicação em produção](#publicação-em-produção-netlify-render-e-mongodb-atlas)
- [Segurança e publicação no GitHub](#segurança-e-publicação-no-github)
- [Testes](#testes)
- [Resolução de problemas](#resolução-de-problemas)

## Requisitos

- Python 3.10 ou superior instalado.
- Para desenvolvimento local, Python, o backend e uma instância MongoDB
  acessível. O projeto `CallMed-Banco-de-dados` ao lado do backend é opcional
  quando `MONGO_URI` está configurada diretamente.
- Para produção, contas nos serviços Netlify, Render e MongoDB Atlas; a
  publicação e os endereços públicos ainda precisam ser criados.

## Tutorial rápido

Para executar localmente, tenha o backend e o frontend disponíveis. O módulo
`CallMed-Banco-de-dados` pode ser usado para carregar a conexão existente;
como alternativa, configure `MONGO_URI` e `DB_NAME` no ambiente do backend.
Crie `.env` a partir do exemplo e defina uma `SECRET_KEY` própria.
Gere uma chave com `py -c "import secrets; print(secrets.token_hex(32))"` no
Windows ou `python3 -c "import secrets; print(secrets.token_hex(32))"` no
Linux. Não compartilhe nem publique os arquivos `.env`.

### Windows (PowerShell)

Na primeira execução, abra um terminal na pasta `CallMed-backend`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edite `.env` para configurar a `SECRET_KEY`. Depois, inicie o backend:

```powershell
.\.venv\Scripts\python.exe app.py
```

Para iniciar o frontend, abra um **segundo terminal** na pasta `CallMed`:

```powershell
..\CallMed-backend\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

### Linux

Na primeira execução, abra um terminal na pasta `CallMed-backend`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp -n .env.example .env
```

Edite `.env` para configurar a `SECRET_KEY`. Depois, inicie o backend:

```bash
.venv/bin/python app.py
```

Para iniciar o frontend, abra um **segundo terminal** na pasta `CallMed`:

```bash
../CallMed-backend/.venv/bin/python -m http.server 5500 --bind 127.0.0.1
```

Abra `http://127.0.0.1:5500/login.html`. Mantenha os dois terminais abertos
enquanto usa o sistema e pressione `Ctrl+C` em cada um para encerrar. Na
próxima execução, pule a criação do ambiente e a instalação das dependências:
inicie apenas o backend e, em outro terminal, o frontend.

## Instalação e execução local

### 1. Configure o banco e os arquivos de ambiente

O backend usa `CallMed-Banco-de-dados` para conectar ao MongoDB. Configure
`MONGO_URI` e `DB_NAME` no `.env` desse projeto, que deve ficar ao lado do
backend:

```text
CallMed/
├── CallMed-backend/
└── CallMed-Banco-de-dados/
```

Na pasta `CallMed-backend`, copie `.env.example` para `.env` somente se o
arquivo ainda não existir e substitua `SECRET_KEY=replace-with-a-random-secret`
por uma chave aleatória. Para gerar uma, use
`py -c "import secrets; print(secrets.token_hex(32))"` no Windows ou
`python3 -c "import secrets; print(secrets.token_hex(32))"` no Linux. Nunca
publique o `.env`.

### 2. Instale as dependências e inicie a API

Execute os comandos a partir da pasta `CallMed-backend`. O ambiente virtual
isola as dependências do projeto e não precisa ser ativado.

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe app.py
```

**Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp -n .env.example .env
.venv/bin/python app.py
```

Antes de iniciar, confirme que `.env` existe e contém sua `SECRET_KEY`.
Os comandos de cópia preservam um `.env` já configurado. A API estará em
`http://127.0.0.1:5000`; confira se iniciou em
`http://127.0.0.1:5000/api/health` e encerre com `Ctrl+C`.

> No Windows, se `py` não estiver disponível, use `python` no lugar. Para
> desenvolvimento local, execute `app.py` com o Python do ambiente virtual,
> como nos comandos acima. O Gunicorn é instalado apenas fora do Windows e
> destina-se ao deploy.

### 3. (Opcional) Inicie o frontend

Com a API rodando, abra **outro terminal** na pasta `CallMed` (irmã de
`CallMed-backend`) e inicie o servidor local:

**Windows (PowerShell):**

```powershell
..\CallMed-backend\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1
```

**Linux:**

```bash
../CallMed-backend/.venv/bin/python -m http.server 5500 --bind 127.0.0.1
```

Abra `http://127.0.0.1:5500/login.html`. Mantenha os dois terminais abertos
enquanto usa o sistema; pressione `Ctrl+C` em cada um para encerrar os
servidores. A configuração padrão de CORS da API já permite essa origem local.

## Configuração de ambiente

O arquivo [.env.example](.env.example) contém valores de exemplo, sem
credenciais reais. Use-o como ponto de partida para o `.env` local, que é
ignorado pelo Git.

| Variável | Padrão | Onde configurar | Descrição |
| --- | --- | --- | --- |
| `API_HOST` | `127.0.0.1` | Backend local | Interface de rede usada pela API. |
| `API_PORT` | `5000` | Backend local | Porta usada pela API; deve ser um inteiro entre 1 e 65535. |
| `FLASK_DEBUG` | `false` | Backend | Ativa o debugger do Flask. Mantenha desativado fora do desenvolvimento local. |
| `CORS_ORIGINS` | `http://localhost:5500,http://127.0.0.1:5500` | Backend/host | Origens autorizadas, separadas por vírgula. Em produção, informe a origem HTTPS exata do frontend. |
| `SECRET_KEY` | Obrigatória | Backend/host | Chave aleatória privada usada para assinar os tokens de autenticação. Não reutilize senha ou URI MongoDB. |
| `TOKEN_MAX_AGE_SECONDS` | `3600` | Backend/host | Validade do token em segundos; permitido de 60 a 604800. |
| `DATABASE_PROJECT_PATH` | Vazio | Backend local (opcional) | Caminho para o projeto de dados legado, usado somente quando `MONGO_URI` não está definido. Em produção não é necessário. |
| `MONGO_URI` | Obrigatória | Backend/host | URI privada do MongoDB Atlas (ou outro servidor MongoDB acessível pelo host). |
| `DB_NAME` | `callmed` | Backend/host | Nome do banco MongoDB. |
| `PORT` | Fornecida pelo host, quando aplicável | Host de deploy | Porta pública interna do processo Gunicorn. Não é a variável usada pelo `python app.py`. |

Gere `SECRET_KEY` com `python -c "import secrets; print(secrets.token_hex(32))"`
e configure-a somente no `.env` local ou no gerenciador de variáveis/segredos
do host.

## Banco de dados separado

O backend **não usa `db.json` como persistência**. Em produção ele conecta
diretamente ao MongoDB usando `MONGO_URI` e `DB_NAME` do ambiente do host; não
precisa que o repositório `CallMed-Banco-de-dados` esteja instalado junto.
Localmente, ainda pode carregar o `database.py` desse projeto para reutilizar
a configuração existente.

| Dados | Collection |
| --- | --- |
| Usuários | `usuarios` |
| Pacientes | `pacientes` |
| Médicos | `medicos` |
| Clínicas | `clinicas` |
| Agendamentos | `agendamentos` |
| Histórico da API | `logs` |
| Configuração global | `configuracoes` |
| Especialidades | `especialidades` |
| Configurações por usuário | `configuracoes_usuario` |
| Conversas de triagem | `triagens` |

O projeto de dados também expõe `especialidades` e `configuracoes_usuario`;
as rotas atuais do backend não as utilizam. O `_id` MongoDB é convertido para
um ID serializável quando necessário. Os documentos legados com campo `id`
continuam sendo consultados por esse campo.

Se `MONGO_URI` estiver definido, o backend cria a conexão MongoDB diretamente
e ignora `DATABASE_PROJECT_PATH`. Sem essa variável, tenta carregar o
`CallMed-Banco-de-dados/database.py` ao lado do backend, que pode ler seu
próprio `.env`. `DATABASE_PROJECT_PATH` permite apontar explicitamente a esse
módulo legado.

O `db.json` legado pode existir localmente, mas não é lido, atualizado ou
utilizado como banco pelo backend.

## Arquitetura

```text
CallMed-backend/
├── app.py
├── config/          Configuração e carregamento de variáveis de ambiente
├── auth/            Decorators de autenticação e autorização
├── routes/          URLs, métodos HTTP e Flask Blueprints
├── controllers/     Conversão entre HTTP/JSON e chamadas dos services
├── services/        Regras de negócio, validações e coordenação
├── repositories/    Contrato de dados e integração com collections externas
├── models/          Representações simples de entidades
├── test_backend.py  Testes da API e do repository
├── requirements.txt
└── .env.example
```

Fluxo principal: **cliente → route → controller → service → repository →
collections MongoDB do projeto separado**.

`app.py` cria a aplicação Flask, configura CORS, compõe as dependências e
registra os Blueprints. Não contém operações CRUD nem consultas MongoDB.

## Autenticação e autorização

- `POST /api/login` recebe `email` e `senha` e retorna um token Bearer
  temporizado e dados públicos do usuário.
- Senhas novas são armazenadas com hash. Quando uma senha antiga em texto
  simples é validada com sucesso, ela é substituída por hash.
- Respostas de usuário não devem incluir senha, hash ou configuração secreta.
- Rotas protegidas exigem `Authorization: Bearer <token>`.
- Tokens expiram após `TOKEN_MAX_AGE_SECONDS`; não há endpoint de refresh ou
  logout no momento.
- Usuários podem acessar os próprios recursos conforme o perfil. Operações
  administrativas requerem um usuário com perfil `admin`.
- Administradores são usuários em `usuarios` com `tipoClinica: "admin"` ou
  `tipo: "admin"`. O cadastro público não permite criar administradores.
- A API não fornece um fluxo público para criar a primeira conta administradora;
  essa conta deve ser provisionada de forma controlada no sistema de dados.
- O frontend deve guardar o token de forma segura e enviá-lo nas chamadas
  autenticadas. O token não deve ser colocado no código-fonte nem em URLs.

## Rotas da API

`Público` não exige token. `Token` exige um Bearer válido. `Admin` exige token
de usuário administrador. As restrições por proprietário/perfil também se
aplicam às rotas indicadas como `Token`.

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Público | Verificação de vida da API. |
| `GET` | `/api/healthz` | Público | Verificação alternativa de vida. |
| `POST` | `/api/login` | Público | Login com `email` e `senha`. |
| `POST` | `/api/cadastro` | Público | Cadastro de usuário; não permite criar admin. |
| `GET`, `POST` | `/api/usuarios` | Admin | Lista ou cria usuários. |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/usuarios/<id>` | Token | Consulta, atualiza ou exclui o próprio usuário; admin pode administrar outros. |
| `GET`, `POST` | `/api/administradores` | Admin | Lista ou cria usuários administradores. |
| `GET`, `PUT`, `DELETE` | `/api/administradores/<admin_id>` | Admin | Consulta, atualiza ou exclui um administrador. |
| `GET`, `PUT` | `/api/perfil/<usuario_id>` | Token | Consulta ou atualiza o próprio perfil; admin pode acessar outros. |
| `GET`, `POST` | `/api/medicos` | Token | Lista médicos ou cria/atualiza perfil permitido. |
| `GET`, `PUT`, `DELETE` | `/api/medicos/<medico_id>` | Token | Consulta, atualiza ou exclui médico segundo perfil/permissão. |
| `GET` | `/api/medicos/<medico_id>/disponibilidade` | Token | Consulta horários; aceita `data` e parâmetros `hora` repetidos. |
| `GET`, `POST` | `/api/pacientes` | Token | Lista (admin) ou cria/atualiza perfil permitido. |
| `GET`, `PUT`, `DELETE` | `/api/pacientes/<paciente_id>` | Token | Consulta, atualiza ou exclui paciente segundo perfil/permissão. |
| `GET`, `POST` | `/api/clinicas` | Admin | Lista, cria ou atualiza clínicas. |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/clinicas/<clinica_id>` | Admin | Consulta, atualiza ou exclui clínica. |
| `GET`, `POST` | `/api/especialidades` | Token para leitura; Admin para criação | Lista ou cria especialidades. |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/especialidades/<especialidade_id>` | Token para leitura; Admin para alteração/exclusão | Consulta, atualiza ou exclui especialidade. |
| `GET`, `POST` | `/api/agendamentos` | Token | Lista agendamentos permitidos ou cria/atualiza agendamento. |
| `GET`, `PUT`, `DELETE` | `/api/agendamentos/<agendamento_id>` | Token | Consulta, atualiza ou exclui agendamento permitido. |
| `GET`, `POST` | `/api/agenda` | Token | Compatibilidade com o contrato legado da agenda. |
| `DELETE` | `/api/agenda/<agendamento_id>` | Token | Exclui agendamento legado permitido. |
| `GET`, `POST` | `/api/historico` | Admin | Lista ou cria registros em `logs`. |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/historico/<historico_id>` | Admin | Consulta, atualiza ou exclui um registro do histórico. |
| `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | `/api/config` | Admin | Lê, cria/mescla, substitui, mescla parcialmente ou exclui a configuração global. |
| `GET`, `POST` | `/api/configuracoes-usuario` | Token | Lista as próprias configurações (admin lista todas) ou cria uma configuração vinculada ao usuário autenticado. |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/configuracoes-usuario/<configuracao_id>` | Token | Consulta, atualiza ou exclui configuração própria; admin pode administrar todas. |
| `POST` | `/api/triagem` | Token | Gera triagem e recomendações. |
| `POST` | `/api/matchmaking` | Token | Recomenda médicos por necessidade e disponibilidade. |
| `GET`, `POST` | `/api/triagem/conversas` | Token | Lista conversas próprias ou inicia uma nova triagem conversacional. |
| `GET`, `PATCH`, `DELETE` | `/api/triagem/conversas/<conversa_id>` | Token | Consulta, corrige os campos estruturados ou exclui conversa própria. |
| `POST` | `/api/triagem/conversas/<conversa_id>/mensagens` | Token | Envia uma resposta e continua a conversa do estado salvo. |

O cadastro de paciente cria o usuário e seu perfil vinculado. O agendamento
exige paciente e médico existentes, data e horário válidos; nomes, telefone e
especialidade são preenchidos com os dados disponíveis. Um horário ocupado
retorna conflito. As respostas mantêm aliases camelCase/snake_case legados
quando aplicável.

Clínicas, especialidades e registros de histórico usam documentos JSON com ID
gerenciado pela API; suas propriedades seguem os documentos já armazenados nas
collections. As configurações globais são tratadas como documento singleton:
`POST` mescla os campos enviados, `PUT` substitui os campos configurados,
`PATCH` mescla parcialmente e `DELETE` remove o documento atual. Configurações
por usuário aceitam propriedades JSON do cliente, mas o vínculo `usuarioId` é
definido e protegido pela API; usuários só acessam as próprias configurações.

Triagem e matchmaking permanecem operações (`POST /api/triagem` e
`POST /api/matchmaking`), não recursos com CRUD. CRUD de triagem/matchmaking
fica fora do escopo atual.

### Triagem conversacional

O fluxo conversacional novo é separado da rota legada `POST /api/triagem`. Ele
usa `triagens` para salvar o estado da conversa e funciona sem serviço externo
de IA: classifica palavras/expressões conhecidas, reconhece algumas dúvidas
frequentes, guarda as mensagens, pergunta um dado por vez e permite correções
estruturadas usando `PATCH`. As respostas são regras do sistema, não texto
gerado por um profissional ou por um modelo de linguagem. A interpretação é
limitada; erros de digitação ou descrições ambíguas podem não ser reconhecidos
corretamente.

O chatbot aceita saudações, explica suas limitações, pode repetir perguntas e
responde dúvidas sobre triagem, agendamento, diagnóstico e medicamentos sem
interromper o estado da conversa. Usa linguagem acolhedora, mas não substitui
avaliação profissional, não diagnostica e não recomenda remédios. Na área da
clínica, o assistente também responde dúvidas simples usando a quantidade de
médicos e agendamentos carregados, sem exibir dados pessoais de pacientes no
chat.

Estados atuais: `collecting_symptoms`, `safety_review`, `asking_followup`,
`triage_summary`, `collecting_preferences`, `pending_matchmaking` e
`urgent_referral`. As respostas estruturadas e mensagens ficam ligadas ao ID do
usuário autenticado; o acesso de outro usuário retorna `403`. O paciente pode
excluir a sessão. O histórico não tem expiração automática configurada.

Para iniciar, um paciente autenticado envia `POST /api/triagem/conversas` com
corpo `{}`. Um administrador deve fornecer `{"pacienteId": 123}`. A API retorna
o ID e a primeira mensagem. Para responder, use
`POST /api/triagem/conversas/<conversa_id>/mensagens` com
`{"mensagem":"texto livre"}`. A resposta traz o novo estado, os campos
estruturados e a próxima mensagem. `PATCH` aceita um objeto `correcoes` com
campos permitidos como `queixa_principal`, `localizacao`, `duracao`,
`intensidade`, `evolucao`, `sintomas_associados` ou `impacto`; não permite
apagar um estado `urgent_referral`.

A triagem apresenta um aviso não diagnóstico e procura apenas sinais de alerta
explícitos e combinações conservadoras. Quando um alerta é detectado, interrompe
as perguntas e recomenda atendimento de emergência/SAMU 192 no Brasil. Para
risco imediato de autoagressão também informa o CVV 188 como apoio emocional,
sem substituir emergência. Uma detecção automática não diagnostica nem exclui
emergências: se houver preocupação, procure avaliação profissional mesmo que
o sistema não tenha identificado alerta.

As regras de segurança atuais são versionadas (`draft-1`) e apontam para
referências públicas:

- Ministério da Saúde — [SAMU 192](https://www.gov.br/saude/pt-br/composicao/saes/samu-192),
  orientação brasileira de acionamento do serviço de emergência.
- CDC — [Signs and Symptoms of Stroke](https://www.cdc.gov/stroke/signs-symptoms/index.html),
  sinais súbitos de AVC.
- NHS — [Chest pain](https://www.nhs.uk/symptoms/chest-pain/) e
  [Anaphylaxis](https://www.nhs.uk/conditions/anaphylaxis/), sinais associados
  a urgência.
- CVV — [apoio emocional pelo 188](https://cvv.org.br/).

As associações sintoma/categoria → especialidade são preliminares, baseadas
nos exemplos deste requisito, não constituem protocolo clínico e ainda exigem
revisão/aprovação de profissional de saúde. O sistema só mostra uma sugestão
se encontrar a especialidade nas collections cadastradas de especialidades ou
de médicos. Não apresenta médicos, não consulta disponibilidade, não confirma
matchmaking e não agenda. A entrada para a integração futura fica no estado
`pending_matchmaking`, com os indicadores de disponibilidade e agendamento
explicitamente falsos. A rota de matchmaking existente e o frontend não são
alterados por esta feature.

Conversas contêm informação de saúde e devem ser tratadas como dados pessoais
sensíveis. O deploy deve usar HTTPS, controles de acesso restritos, usuário
MongoDB com permissões mínimas e política de retenção/eliminação definida pelo
responsável pelo serviço. A exclusão pela API não substitui uma política de
retenção nem a gestão de backups.

Erros da API são JSON. Códigos relevantes: `400` entrada inválida, `401`
credenciais/token inválidos ou ausentes, `403` sem permissão, `404` recurso
inexistente, `409` conflito/duplicidade e `500` erro interno. Stack traces e
segredos não são enviados na resposta.

## Exemplos de uso

### Login

```bash
curl -X POST "http://127.0.0.1:5000/api/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@exemplo.com","senha":"sua-senha"}'
```

A resposta inclui `token`, `tipo_token`, `expires_in` e `usuario`, sem senha.
Use o token retornado nas rotas protegidas:

```bash
curl "http://127.0.0.1:5000/api/medicos" \
  -H "Authorization: Bearer <TOKEN_RECEBIDO_NO_LOGIN>"
```

### Cadastro

```bash
curl -X POST "http://127.0.0.1:5000/api/cadastro" \
  -H "Content-Type: application/json" \
  -d '{"nome":"Paciente Exemplo","email":"paciente@example.com","senha":"senha-forte","tipo":"paciente"}'
```

### Agendamento

```bash
curl -X POST "http://127.0.0.1:5000/api/agendamentos" \
  -H "Authorization: Bearer <TOKEN_RECEBIDO_NO_LOGIN>" \
  -H "Content-Type: application/json" \
  -d '{"pacienteId":1,"medicoId":2,"data":"2030-01-15","hora":"10:00"}'
```

Os IDs, data, horário e relações devem corresponder a registros existentes e
às permissões do usuário autenticado.

## Publicação em produção: Netlify, Render e MongoDB Atlas

O plano é publicar o frontend estático no Netlify, a API Python no Render e
usar MongoDB Atlas como banco gerenciado. **Esses serviços e endereços ainda
não foram criados**; portanto, domínios e URLs nesta seção são valores a
substituir durante a configuração, não endereços publicados. O arquivo
`render.yaml` prepara o backend do Render como Blueprint.

### 1. Criar o cluster MongoDB Atlas

1. Crie um projeto e cluster no MongoDB Atlas.
2. Crie um usuário de banco com a função `readWrite` somente no banco
   `callmed`.
   Gere a URI de conexão do driver Python e guarde-a como segredo; não a
   publique nem envie em mensagens. Se a senha tiver caracteres especiais,
   codifique-os conforme instruído pelo Atlas.

### 2. Publicar o frontend no Netlify

1. Publique o repositório do frontend no GitHub e crie um site Netlify
   conectado a esse repositório. `netlify.toml` configura a publicação da
   raiz como site estático.
2. Anote a URL HTTPS que o Netlify gerar. Ela ainda não existe antes da
   criação do site.

### 3. Publicar a API no Render

1. Publique `CallMed-backend` no GitHub e crie um Blueprint no Render usando
   o `render.yaml`. Não publique arquivos `.env` nem credenciais.
2. No Blueprint, configure `MONGO_URI` com a URI privada do Atlas e
   `CORS_ORIGINS` com a origem HTTPS gerada pelo Netlify, sem caminho e sem
   barra final. Se tiver domínio próprio, inclua as origens efetivamente
   usadas, separadas por vírgula.
3. O Blueprint gera `SECRET_KEY`, define `DB_NAME=callmed`, desativa o debug,
   instala as dependências e inicia Gunicorn na porta do Render. Não configure
   `DATABASE_PROJECT_PATH`: o projeto de dados separado não é necessário em
   produção.
4. Após criar o serviço, abra **Connect → Outbound** no painel do Render.
   Copie os IPs/CIDRs de saída mostrados para a região do serviço e permita-os
   na **Network Access** do Atlas. Os CIDRs do Render podem ser compartilhados
   com outros serviços; confirme a política de rede exigida pelo projeto. Se
   mudar a região do Render, confira e atualize a allowlist. Não mantenha
   `0.0.0.0/0` como regra permanente.
5. Anote a URL HTTPS pública atribuída pelo Render. Ela ainda não existe antes
   da criação do serviço.
6. Atualize `CallMed/js/config.js` para usar `<URL_DO_RENDER>/api` e publique
   a alteração no repositório do frontend para o Netlify fazer novo deploy.
   O endereço `callmed-backend.onrender.com` no arquivo é apenas um valor
   inicial: use o domínio que aparecer no painel do serviço.
7. Teste `/api/health` na URL pública. Depois, teste login e uma rota
   autenticada pela página do Netlify para confirmar também a conexão ao Atlas.

**Estado atual:** Netlify, Render e Atlas ainda não foram configurados; o
repositório contém apenas a preparação para o deploy. Os domínios, as
credenciais do Atlas, a allowlist de rede e as origens CORS devem ser
preenchidos quando os serviços forem criados.

Os segredos devem ser configurados no painel do provedor que executa a API.
GitHub Actions Secrets não se tornam automaticamente variáveis de ambiente do
Render e não devem ser impressos nos logs.

O modo de produção abre a conexão usando `MONGO_URI` e `DB_NAME`, portanto
funciona mesmo quando somente o repositório do backend é implantado. Se
`MONGO_URI` estiver ausente, o modo legado tenta encontrar
`CallMed-Banco-de-dados/database.py` localmente e falha com uma mensagem clara
se nenhum dos dois meios de conexão estiver configurado.

## Segurança e publicação no GitHub

- Nunca faça commit de `.env`, URI MongoDB, senha, `SECRET_KEY`, token ou
  qualquer outro segredo.
- `.gitignore` exclui `.env` e arquivos `.env.*`, mantendo
  `.env.example` versionável. Antes de commit, confirme:

  ```bash
  git check-ignore -v .env
  git status --short
  ```

- Use somente placeholders em `.env.example`; não cole nele valores reais.
- Se um segredo já foi enviado ao GitHub, **revogue/rotacione-o imediatamente**.
  Apagar o arquivo em um commit posterior não remove o segredo do histórico.
  Antes de tornar público, remova o segredo do histórico Git com um processo
  seguro de reescrita, coordene o force-push com colaboradores e confirme que
  forks, caches, logs e releases não preservam cópias. Rotacionar continua
  obrigatório mesmo depois da limpeza do histórico.
- Não reutilize a mesma `SECRET_KEY` entre desenvolvimento, testes e produção.
- Mantenha `FLASK_DEBUG=false` e use HTTPS no frontend e na API em produção.
- Restrinja CORS aos domínios realmente usados; CORS não substitui autenticação.
- Não use contas reais de pacientes em testes nem em exemplos públicos.
- A API de health verifica que o Flask responde; não é uma verificação completa
  da disponibilidade do MongoDB.

## Frontend

Em produção, configure o frontend para usar o endereço HTTPS público da API e
enviar o token de login no cabeçalho `Authorization` das rotas protegidas.

## Testes

Os testes usam um repository em memória e não conectam nem gravam no MongoDB
real. Com o ambiente virtual ativado:

```bash
python -m unittest -v test_backend
```

No PowerShell, para verificar a sintaxe dos arquivos Python:

```powershell
Get-ChildItem -Recurse -Filter *.py |
  Where-Object { $_.FullName -notmatch '\\.venv\\|__pycache__' } |
  ForEach-Object { python -m py_compile $_.FullName }
```

Execute os testes antes de abrir um pull request e depois de alterar serviços,
rotas, autenticação ou repository.

## Resolução de problemas

| Sintoma | O que verificar |
| --- | --- |
| `SECRET_KEY não definida` | Configure `SECRET_KEY` no `.env` local ou no ambiente do host e reinicie o processo. |
| O frontend Netlify chama `localhost` | Confirme `CallMed/js/config.js`: em produção `CALLMED_API_URL` deve apontar para a URL HTTPS pública efetivamente atribuída pelo Render, terminada em `/api`. |
| Erro de CORS vindo do Netlify | Configure `CORS_ORIGINS` no Render com a origem HTTPS exata do site Netlify, sem caminho nem barra final, e redeploy/reinicie a API. |
| Não foi possível localizar `database.py` | Para produção, configure `MONGO_URI` no ambiente do host; para o modo legado, confirme `DATABASE_PROJECT_PATH` ou disponibilize o projeto de dados ao lado do backend. |
| `MONGO_URI não definida` | Configure-a no ambiente do host ou no `.env` local. Nunca a coloque no código. |
| Falha ao conectar ao MongoDB | Verifique URI, usuário/senha do banco, `DB_NAME`, regras de rede/allowlist do Atlas e acesso de saída do host. Erros TLS/SSL durante o handshake ocorrem antes da autenticação do app; confirme o cluster/URI e conectividade TLS com o Atlas. |
| `401` em rota protegida | Faça login novamente, envie `Authorization: Bearer <token>` e confirme que o token não expirou. |
| `403` | Confirme o perfil do usuário e se ele é proprietário do recurso ou administrador conforme a operação. |
| Erro de CORS no navegador | Configure `CORS_ORIGINS` com a origem exata do frontend, incluindo esquema e domínio, sem caminho de página. |
| O health responde, mas os dados não carregam | Health é liveness; verifique as configurações do MongoDB e o log do processo no host. |

## Limites conhecidos da integração

- O projeto de dados separado é opcional no deploy: o backend conecta
  diretamente ao serviço MongoDB remoto configurado em `MONGO_URI`.
- O primeiro administrador precisa ser provisionado de forma segura fora do
  cadastro público.
- O frontend precisa persistir e enviar o token Bearer para usar as rotas
  protegidas.
- `python app.py` é apenas para desenvolvimento local; produção deve usar um
  servidor WSGI.
