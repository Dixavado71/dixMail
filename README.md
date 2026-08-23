# Gmail Manager CLI

Gerenciador de e-mail Gmail via linha de comando (CLI) usando Python e IMAP.

## 📋 Requisitos

- Python 3.11 ou superior
- Conta Gmail com **Senha de App** configurada
- Conexão com a internet

## 🚀 Instalação

1. Clone o repositório ou baixe os arquivos:

```bash
cd gmail-manager
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

### 1. Criar arquivo `.env`

Copie o arquivo de exemplo e edite com suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
GMAIL_EMAIL=seuemail@gmail.com
GMAIL_APP_PASSWORD=sua_senha_de_app
DOWNLOAD_DIR=downloads
```

### 2. Obter Senha de App do Google

O Gmail não permite mais usar sua senha normal para aplicações de terceiros. Você precisa gerar uma **Senha de App**:

1. Acesse sua [Conta Google](https://myaccount.google.com/)
2. Vá em **Segurança**
3. Em "Como fazer login no Google", ative a **Verificação em duas etapas** (se ainda não estiver ativa)
4. Volte para **Segurança** e procure por **Senhas de app**
5. Selecione "Mail" e seu dispositivo
6. Clique em **Gerar**
7. Copie a senha de 16 caracteres e cole no arquivo `.env`

⚠️ **Importante:** Nunca compartilhe sua Senha de App e nunca a coloque diretamente no código.

## ▶️ Como Executar

```bash
python app.py
```

O aplicativo irá:
1. Carregar as configurações do `.env`
2. Conectar ao Gmail via IMAP
3. Mostrar o menu principal

## 📁 Estrutura do Projeto

```
gmail-manager/
│
├── app.py                 # Ponto de entrada da aplicação
├── .env                   # Configurações (NÃO commitar)
├── .env.example           # Exemplo de configuração
├── .gitignore             # Arquivos ignorados pelo Git
├── requirements.txt       # Dependências Python
├── README.md              # Este arquivo
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py    # Carregamento de configurações
│   │
│   ├── imap/
│   │   ├── __init__.py
│   │   ├── client.py      # Cliente IMAP
│   │   ├── folders.py     # Gerenciamento de pastas
│   │   ├── messages.py    # Gerenciamento de mensagens
│   │   └── search.py      # Busca de e-mails
│   │
│   ├── email_parser/
│   │   ├── __init__.py
│   │   └── parser.py      # Parser de e-mails
│   │
│   ├── attachments/
│   │   ├── __init__.py
│   │   └── downloader.py  # Download de anexos
│   │
│   └── cli/
│       ├── __init__.py
│       └── menu.py        # Interface CLI
│
└── downloads/             # Pasta para anexos baixados
```

## ✨ Funcionalidades

### Menu Principal

```
1. Caixa de entrada      - Lista e-mails da pasta atual
2. Pastas / Marcadores   - Mostra todas as pastas disponíveis
3. Pesquisar e-mails     - Busca por remetente, assunto, etc.
4. Abrir e-mail          - Lê o conteúdo completo de um e-mail
5. Selecionar e-mails    - Seleciona múltiplos e-mails por ID
6. Baixar anexos         - Downloads dos anexos dos e-mails selecionados
7. Gerenciar e-mails     - Marcar como lido/não lido, excluir, mover
8. Atualizar             - Reconecta ao servidor
0. Sair                  - Encerra a aplicação
```

### Pesquisa de E-mails

Formatos suportados:

| Formato | Descrição | Exemplo |
|---------|-----------|---------|
| `from:` | Buscar por remetente | `from:empresa@email.com` |
| `to:` | Buscar por destinatário | `to:cliente@email.com` |
| `subject:` | Buscar no assunto | `subject:nota fiscal` |
| `unread` | E-mails não lidos | `unread` |
| Texto livre | Busca em assunto e corpo | `relatório mensal` |

### Seleção Múltipla

Para selecionar e-mails:
- IDs separados por vírgula: `1,3,5`
- Todos os e-mails: `all`

### Anexos

Os anexos são salvos na pasta `downloads/`. O sistema:
- Detecta automaticamente anexos em cada e-mail
- Evita sobrescrever arquivos existentes (adiciona `_1`, `_2`, etc.)
- Mostra progresso durante o download
- Suporta download em massa de múltiplos e-mails

### Gerenciamento de E-mails

Ações disponíveis para e-mails selecionados:
- **Marcar como lido** - Remove a marcação de não lido
- **Marcar como não lido** - Adiciona marcação de não lido
- **Excluir** - Move e-mails para a Lixeira do Gmail
- **Mover** - Copia e-mails para outra pasta

⚠️ **Atenção:** Ações destrutivas pedem confirmação antes de executar.

## 🔒 Segurança

O projeto segue boas práticas de segurança:

- ✅ Credenciais armazenadas apenas no `.env`
- ✅ `.env` ignorado pelo Git (`.gitignore`)
- ✅ Senha nunca impressa no terminal
- ✅ Conteúdo HTML convertido para texto seguro
- ✅ Nenhum JavaScript executado
- ✅ Confirmação para ações destrutivas
- ✅ Números sequenciais para evitar sobrescrita de arquivos

## ⚠️ Limitações do IMAP/Gmail

1. **Autenticação**: Requer Senha de App (não funciona com senha normal)
2. **HTTPS Only**: Conexão apenas via SSL/TLS (porta 993)
3. **Rate Limiting**: Google pode limitar conexões frequentes
4. **Pastas do Gmail**: Algumas pastas são especiais (`[Gmail]/All Mail`, etc.)
5. **Exclusão**: E-mails "excluídos" vão para a Lixeira, não são removidos permanentemente
6. **Movimentação**: Gmail usa COPY + DELETE para mover e-mails entre pastas

## 🛠️ Solução de Problemas

### Erro: "Invalid credentials"

- Verifique se o e-mail está correto no `.env`
- Gere uma nova Senha de App no Google
- Certifique-se de que a Verificação em Duas Etapas está ativa

### Erro: "Connection timeout"

- Verifique sua conexão com a internet
- O firewall pode estar bloqueando a porta 993
- Tente a opção "Atualizar" no menu

### Erro: "INBOX não encontrada"

- O Gmail pode usar nomes diferentes dependendo do idioma
- Use a opção "Pastas / Marcadores" para ver os nomes reais

### Nenhum anexo encontrado

- Alguns e-mails podem ter anexos inline (incorporados)
- Verifique se o e-mail realmente tem anexos

## 📝 Licença

Este projeto é fornecido "como está" para fins educacionais e de uso pessoal.

---

**Nota:** Este projeto usa IMAP padrão e não a API do Gmail. Para integrações mais complexas, considere usar a [Gmail API oficial](https://developers.google.com/gmail/api).
