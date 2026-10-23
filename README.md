# Solicitação de Avaliação Geotécnica

## Instalação antes da execução

Use **Python 3.12** tanto localmente quanto no deploy. O app não instala
pacotes, não cria arquivos de credenciais globais e não inicia outro processo.
O ponto de entrada é `python -m streamlit run app.py`, a partir desta pasta.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

Dependências diretas confirmadas por leitura de todos os imports de `app.py`:

| Pacote | Uso |
| --- | --- |
| streamlit | Interface, navegação, cache e Secrets |
| pandas | Consultas, tabelas, datas e agregações |
| plotly | Gráficos do dashboard |
| SQLAlchemy | Engine, transações e SQL PostgreSQL |
| psycopg2-binary | Driver PostgreSQL carregado pelo SQLAlchemy |
| pillow | Orientação, compressão e redimensionamento das fotos (`PIL`) |
| folium | Mapas e marcadores |
| streamlit-folium | Mapas integrados à interface |
| fpdf2 | Relatórios PDF; fornece `fpdf` e `fpdf.enums` |

Nenhuma das nove dependências anteriores estava sobrando ou faltando. Os imports
de mapas, imagens e PDF ocorrem dentro de funções, mas são necessários para o app
completo. Não instale o pacote legado `fpdf`, que compartilha o namespace de
`fpdf2`. `datetime` e `io` pertencem à biblioteca padrão do Python.

`requirements.in` registra as nove dependências diretas com as versões avaliadas.
`requirements.txt` fixa também as dependências transitivas resolvidas em um
ambiente virtual limpo com Python 3.12/Linux. A nuvem e o ambiente local devem
instalar o mesmo arquivo. Isso fixa versões, mas não é um lock com hashes nem
garante binários idênticos entre sistemas operacionais. Windows/macOS precisam
passar pelos mesmos checks antes do uso.

## Configuração obrigatória

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e substitua
os valores de exemplo. Nunca versione o arquivo real; ele está no `.gitignore`.

- `DB_URL`: PostgreSQL com host, banco, usuário e senha. São aceitos `postgres://`,
  `postgresql://` e `postgresql+psycopg2://`; o primeiro é normalizado. Codifique
  caracteres especiais da senha na URL. Para Neon, preserve os parâmetros SSL
  fornecidos pelo serviço (por exemplo, `sslmode=require`).
- `SENHA_ADM`: string não vazia e exclusiva para Gestão. Não há senha de fallback.
  Troque a senha anteriormente embutida no código, se estava em uso.

Configuração ausente ou inválida interrompe a aplicação com orientação, antes da
criação do engine. As mensagens de validação e de conexão não incluem a URL nem
os valores dos Secrets. O engine usa `pool_pre_ping` e timeout de conexão de 10 s.
O timeout não substitui o diagnóstico de rede/DNS.

```bash
python preflight.py
# Opcional: verifica a conexão com SELECT 1, sem alterar o banco
python preflight.py --check-db
# Para um arquivo de Secrets em outro local:
python preflight.py --secrets /caminho/secrets.toml
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

O preflight retorna código 1 se houver problema e nunca instala pacotes.
A verificação de configuração é local; `--check-db` precisa de rede e credenciais
válidas. `SELECT 1` não valida o schema nem permissões de escrita.

O banco deve estar provisionado antes do uso: o código espera as tabelas
`solicitacoes`, `listas_opcoes` e `anexos`.
Este repositório não contém migrações ou DDL; a mudança não cria ou modifica
tabelas. Conserve o schema existente e verifique as operações do app em uma base
de homologação antes de promover o deploy.

## Deploy no Streamlit Community Cloud

1. Selecione o repositório, a branch revisada e `app.py` como arquivo de entrada.
2. Nas opções de deploy, selecione **Python 3.12**. `.python-version` documenta a
   versão local; não substitui a seleção no painel da nuvem.
3. Configure `DB_URL` e `SENHA_ADM` no painel Secrets. Não envie o arquivo local.
4. O build deve instalar `requirements.txt` antes de iniciar o Streamlit.
5. Valide início, acesso ao banco, cadastro, fotos, mapas e exportação de PDF em
   homologação. Não faça a validação funcional com gravações na produção.

Em outro provedor, use `python -m pip install -r requirements.txt` na etapa de
build e `python -m streamlit run app.py --server.headless=true` no início.
Configure host/porta conforme o provedor. Nenhum pacote deve ser instalado pelo
processo da aplicação.

## Atualizações e validação

Para atualizar dependências, ajuste `requirements.in`, instale-o em um ambiente
virtual novo de Python 3.12, execute os checks e gere novamente
`python -m pip freeze > requirements.txt`. Revise o diff de versões e mantenha
os dois arquivos no mesmo commit. Não gere o arquivo a partir de um ambiente
compartilhado com outros projetos.

O workflow `.github/workflows/validate.yml` instala o arquivo fixado, executa
`pip check` e os testes de configuração e inicialização sem Secrets reais.
Esses testes verificam também que a página inicial não conecta ao banco nem
executa subprocessos. Não substituem testes de integração com Neon e do fluxo
completo de cadastro/gestão.
