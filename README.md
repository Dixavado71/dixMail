# Projeto: Gmail Manager CLI — Python + IMAP

Crie um gerenciador de e-mail Gmail em **Python**, simples, modular e organizado, usando **IMAP** para acessar e gerenciar a conta.

## 1. Objetivo

Criar uma aplicação CLI que permita:

* Conectar ao Gmail usando IMAP.
* Ler credenciais de um arquivo `.env`.
* Usar e-mail + **Senha de app do Gmail**.
* Listar caixa de entrada.
* Listar pastas/marcadores disponíveis.
* Pesquisar e-mails.
* Abrir e ler e-mails.
* Visualizar remetente, destinatário, assunto, data e conteúdo.
* Identificar anexos.
* Baixar anexos.
* Criar pastas locais para organizar downloads.
* Excluir um ou vários e-mails.
* Selecionar e-mails por remetente.
* Selecionar e-mails por assunto/título.
* Pesquisar por nome, endereço de e-mail ou texto.
* Selecionar múltiplos e-mails.
* Baixar anexos de vários e-mails.
* Marcar e-mails como lidos/não lidos.
* Mover e-mails entre pastas IMAP quando possível.
* Ter uma interface CLI simples e fácil de navegar.

## 2. Tecnologias

Use:

* Python 3.11+
* `imaplib` para IMAP
* `email` para processamento das mensagens
* `python-dotenv` para `.env`
* `pathlib` para arquivos e diretórios
* `getpass` somente se necessário
* `rich` para uma CLI bonita e organizada

Não use OAuth 2.0.

Não use Gmail API.

Não use Selenium.

Não use navegador.

A autenticação deve ser exclusivamente:

```text
GMAIL_EMAIL
GMAIL_APP_PASSWORD
```

através de IMAP.

## 3. Estrutura

Organize o projeto desta forma:

```text
gmail-manager/
│
├── app.py
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── imap/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── folders.py
│   │   ├── messages.py
│   │   └── search.py
│   │
│   ├── email/
│   │   ├── __init__.py
│   │   └── parser.py
│   │
│   ├── attachments/
│   │   ├── __init__.py
│   │   └── downloader.py
│   │
│   └── cli/
│       ├── __init__.py
│       └── menu.py
│
└── downloads/
```

## 4. `.env`

Criar:

```env
GMAIL_EMAIL=seuemail@gmail.com
GMAIL_APP_PASSWORD=sua_senha_de_app
DOWNLOAD_DIR=downloads
```

Nunca imprimir a senha no terminal.

Nunca colocar credenciais diretamente no código.

O `.env` deve estar no `.gitignore`.

Criar também `.env.example` sem credenciais reais.

## 5. `app.py`

O `app.py` deve ser o ponto de entrada.

Fluxo:

```text
Iniciar aplicação
       ↓
Carregar .env
       ↓
Validar configurações
       ↓
Conectar ao Gmail via IMAP
       ↓
Testar INBOX
       ↓
Mostrar Dashboard CLI
```

Se a conexão falhar, mostrar uma mensagem clara e encerrar.

## 6. Dashboard

Depois da conexão mostrar algo semelhante a:

```text
╔════════════════════════════════════════════╗
║              GMAIL MANAGER                 ║
╠════════════════════════════════════════════╣
║ Conta: usuario@gmail.com                   ║
║ Status: ● Conectado                        ║
╚════════════════════════════════════════════╝

1. Caixa de entrada
2. Pastas / Marcadores
3. Pesquisar e-mails
4. Abrir e-mail
5. Selecionar e-mails
6. Baixar anexos
7. Gerenciar e-mails
8. Atualizar
0. Sair
```

Usar `rich` para tabelas, painéis e mensagens.

## 7. Caixa de entrada

Mostrar uma tabela contendo:

```text
ID | Data | Remetente | Assunto | Status | Anexos
```

Exemplo:

```text
1 | 23/08/2026 | empresa@email.com | Nota Fiscal | NOVO | 2
2 | 22/08/2026 | banco@email.com   | Fatura      | LIDO | 1
```

Não carregar todos os conteúdos dos e-mails de uma vez.

Inicialmente carregar apenas metadados.

## 8. Pastas e categorias

Obter dinamicamente as pastas existentes através do IMAP.

Exemplos:

```text
INBOX
Sent
Drafts
Spam
Trash
All Mail
Starred
```

Não assumir nomes fixos.

O Gmail pode retornar nomes diferentes dependendo da conta/configuração.

Permitir selecionar uma pasta e listar seus e-mails.

## 9. Pesquisa

Criar um sistema de pesquisa simples.

Permitir pesquisar por:

```text
Remetente
Destinatário
Assunto
Nome
Data
Texto
```

Exemplos:

```text
from:empresa@email.com
subject:nota fiscal
nome da empresa
```

Também permitir selecionar todos os resultados.

Sempre que possível, utilizar os recursos de busca do próprio IMAP (`SEARCH`) em vez de baixar todas as mensagens para Python.

## 10. Seleção de múltiplos e-mails

Permitir:

```text
Selecionar 1
Selecionar vários
Selecionar todos
Cancelar seleção
```

Exemplo:

```text
Digite os IDs:

1,3,5
```

ou:

```text
all
```

## 11. Manipulação

Implementar:

```text
Abrir
Marcar como lido
Marcar como não lido
Excluir
Mover
Baixar anexos
```

Para ações destrutivas, pedir confirmação:

```text
Tem certeza que deseja excluir 15 e-mails? [s/N]
```

Nunca excluir automaticamente.

## 12. Leitura de e-mail

Ao abrir uma mensagem mostrar:

```text
De:
Para:
Data:
Assunto:

------------------------------------
CONTEÚDO
------------------------------------

...
```

Suportar mensagens:

* `text/plain`
* `text/html`

Para HTML, converter para uma visualização segura em texto sempre que possível.

Não executar JavaScript ou conteúdo ativo recebido por e-mail.

## 13. Anexos

Detectar automaticamente anexos.

Mostrar:

```text
Anexos:

1. documento.pdf       2.4 MB
2. imagem.png          850 KB
3. contrato.docx       120 KB
```

Permitir:

```text
Baixar 1
Baixar vários
Baixar todos
```

Salvar em:

```text
downloads/
```

Organizar opcionalmente:

```text
downloads/
├── remetente/
├── assunto/
└── data/
```

Evitar sobrescrever arquivos existentes.

Se existir:

```text
documento.pdf
```

usar:

```text
documento_1.pdf
documento_2.pdf
```

## 14. Download de anexos em massa

Permitir selecionar vários e-mails e executar:

```text
Baixar todos os anexos
```

Exemplo:

```text
Selecionados: 25 e-mails
Anexos encontrados: 18
Downloads realizados: 18
```

Mostrar progresso com `rich`.

## 15. Segurança

Nunca:

* salvar senha em código;
* imprimir senha;
* colocar `.env` no Git;
* executar conteúdo HTML recebido;
* executar anexos;
* sobrescrever arquivos silenciosamente.

Adicionar ao `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
downloads/
.venv/
```

## 16. Tratamento de erros

Tratar claramente:

* credenciais inválidas;
* falha de conexão;
* timeout;
* pasta inexistente;
* e-mail inexistente;
* mensagem inválida;
* anexo inválido;
* erro de download;
* conexão IMAP perdida.

Mostrar mensagens amigáveis em vez de traceback para o usuário final.

## 17. Reconexão

Criar uma camada `IMAPClient` responsável pela conexão.

Ela deve permitir:

```python
connect()
disconnect()
reconnect()
select_folder()
search()
fetch()
delete()
move()
mark_read()
mark_unread()
```

Evitar criar várias conexões IMAP desnecessariamente.

Manter uma conexão ativa durante a utilização do programa e reconectar quando necessário.

## 18. Código inicial

O projeto deve partir deste conceito:

```python
import imaplib

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(email, senha)
```

Porém, refatore para uma arquitetura modular e obtenha:

```python
email = settings.gmail_email
senha = settings.gmail_app_password
```

a partir do `.env`.

## 19. Dependências

Criar `requirements.txt` contendo somente as dependências realmente utilizadas.

Preferir bibliotecas da biblioteca padrão Python quando possível.

Adicionar inicialmente:

```text
python-dotenv
rich
```

Não adicionar frameworks desnecessários.

## 20. Qualidade

O código deve ser:

* modular;
* simples;
* legível;
* tipado quando fizer sentido;
* com funções pequenas;
* sem código duplicado;
* sem arquivos gigantes;
* sem lógica de negócio dentro de `app.py`.

Não criar complexidade desnecessária.

## 21. README

Criar README explicando:

1. Requisitos.
2. Instalação.
3. Criação do `.env`.
4. Como obter a Senha de app do Google.
5. Como executar.
6. Estrutura do projeto.
7. Funcionalidades.
8. Limitações do IMAP/Gmail.

## 22. Regra importante

Antes de criar qualquer arquivo, analise o projeto atual.

Se os arquivos já existirem, **não sobrescreva funcionalidades existentes sem necessidade**.

Implemente incrementalmente.

Ao finalizar, execute testes básicos:

```text
python app.py
```

e valide:

* carregamento do `.env`;
* conexão IMAP;
* autenticação;
* acesso à INBOX;
* listagem de pastas;
* listagem de mensagens;
* pesquisa;
* leitura;
* identificação de anexos.

O resultado deve ser um **gerenciador Gmail CLI funcional, simples e prático**, focado principalmente em facilitar a localização, leitura, organização e **download de arquivos/anexos recebidos por e-mail**.
