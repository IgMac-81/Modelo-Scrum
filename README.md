# Scrum — Gestão Ágil de Projetos

Aplicação desktop em **Python + Tkinter** para gerenciar um projeto Scrum completo: Product Backlog, Sprints Backlog, Histórico de Sprints, Governança, Transparência, Qualidade e Dashboards executivos. Os dados ficam em um banco **SQLite** local.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Requisitos](#requisitos)
- [Como executar](#como-executar)
- [Executável (instalação para o usuário final)](#executável-instalação-para-o-usuário-final)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Banco de dados](#banco-de-dados)
- [Problemas comuns](#problemas-comuns)
- [Observações](#observações)

## Funcionalidades

### Menu Principal
- A aplicação **sempre abre no Menu Principal**.
- Botões de acesso às telas à esquerda, com resumo objetivo de cada formulário à direita.
- **Combobox + botão "Abrir manual"**: manual de instruções detalhado de cada formulário (objetivo, dados, automações e ações).
- **Botão "Novo projeto"**: apaga todos os dados do projeto atual (histórias, tarefas, históricos, governança, transparência e qualidade) com confirmação, mantendo as tabelas de referência (Fibonacci e Status).

### Product Backlog
- Cadastro de histórias: módulo, história de usuário, prioridade, Story Points (Fibonacci), sprint alocada, status e observações.
- Busca, filtros por status/sprint, edição, exclusão e ajudas contextuais (prioridade, Fibonacci, status).
- **Importar/Exportar CSV e Excel** e geração de modelos de importação.

### Sprints Backlog
- Tarefas técnicas vinculadas às histórias: responsável, Story Points, horas estimadas/gastas/restantes, status e data de conclusão.
- Automações: dados da história preenchidos automaticamente; horas restantes calculadas.
- **Importar/Exportar CSV e Excel** (ignora `Id_Task` duplicado).

### Histórico de Sprints
- Registro de planejamento x entrega por tarefa/sprint: pontos planejados/entregues, Velocity_% e capacidade.
- Automações: dados vêm da tarefa; pontos entregues conforme status; `Velocity_% = entregues / planejados × 100`.
- **Importar/Exportar CSV e Excel** (`Id_Historico` gerado automaticamente).

### Governança
- Políticas, responsáveis, periodicidade, status e vínculos com histórias do backlog.
- **Importar/Exportar CSV e Excel** (ignora política duplicada).

### Transparência
- Relatórios publicados, frequência, responsável, visibilidade e vínculos com histórias.
- **Importar/Exportar CSV e Excel** (ignora relatório duplicado).

### Qualidade
- Métricas com Valor_Alvo x Valor_Real, atingimento por métrica e índice geral do projeto.
- Fontes automáticas: Velocity e tempo médio de resolução derivados de tarefas concluídas; **Coverage.py** (JSON/XML) para cobertura; CSV de monitoramento (`online_hours,total_hours`) para disponibilidade.
- **Importar/Exportar CSV e Excel** (ignora métrica duplicada).

### Dashboards
- Seis abas (uma por formulário) com **4 cards de indicadores + 2 gráficos** cada:
  - Product Backlog: histórias, pontos, % concluídas, sem sprint | rosca por status, pontos por prioridade.
  - Sprints Backlog: tarefas, % concluídas, horas gastas/restantes | tarefas por status, horas estimadas x gastas.
  - Histórico: registros, velocity média, pontos planejados/entregues | velocity por sprint, planejado x entregue.
  - Governança: políticas, % ativas, periodicidades, vínculos | por status e periodicidade.
  - Transparência: relatórios, visibilidades, responsáveis, vínculos | por visibilidade e frequência.
  - Qualidade: métricas, índice do projeto, metas atingidas, vínculos | atingimento por métrica (meta = 100%), rosca por status.
- Botão **⟳ Atualizar** recarrega os dados do banco.

## Requisitos

- Python 3.10+ (desenvolvido em 3.14)
- Dependências em [requirements.txt](requirements.txt):

```
pip install -r requirements.txt
```

| Pacote | Uso |
|---|---|
| pandas | Cálculo de atingimento/índice na Qualidade |
| openpyxl | Importação/exportação Excel |
| matplotlib | Gráficos dos Dashboards |
| pytest | Testes |

O Tkinter e o SQLite já vêm com o Python.

## Como executar

```
python src/main.py
```

## Executável (instalação para o usuário final)

O arquivo `dist/Scrum.exe` (~51 MB) é a versão empacotada para Windows: **não exige Python instalado**.

1. Copie `Scrum.exe` para qualquer pasta (ex.: `C:\Scrum` ou a Área de Trabalho).
2. Execute com duplo clique. Na primeira execução, o app cria automaticamente a subpasta `db\` ao lado do exe com o banco SQLite semeado (tabelas de referência + dados de exemplo).
3. Todos os dados gravados ficam em `db\agile_backlog.db` ao lado do exe — para "desinstalar", basta apagar a pasta.

Para gerar novamente o executável:

```
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Scrum --add-data "db;db" src/main.py
```

O executável é gerado em `dist/Scrum.exe`. Opções: `--onefile` (arquivo único), `--windowed` (sem console), `--add-data "db;db"` (banco semente embutido). O arquivo `Scrum.spec` permite ajustes finos do empacotamento.

## Estrutura do projeto

```
Scrum/
├── db/
│   ├── agile_backlog.db        # Banco SQLite (gerado automaticamente)
│   └── create_tables.py        # Cria as tabelas (não apaga dados existentes)
├── src/
│   ├── main.py                 # Ponto de entrada (abre no Menu Principal)
│   ├── formulario.py           # Menu Principal + Product Backlog + navegação
│   ├── sprints_formulario.py   # Sprints Backlog
│   ├── historico_formulario.py # Histórico de Sprints
│   ├── governanca_formulario.py# Governança
│   ├── transparencia_formulario.py # Transparência
│   ├── qualidade_formulario.py # Qualidade
│   ├── dashboard_formulario.py # Dashboards (cards + gráficos)
│   ├── database.py             # Acesso SQLite (CRUD, vínculos, reset de projeto)
│   ├── data_transfer.py        # Importar/exportar CSV e Excel compartilhado
│   └── grid_sizing.py          # Ajuste automático de largura das colunas dos grids
├── dist/
│   └── Scrum.exe               # Executável para o usuário final
├── Scrum.spec                  # Configuração do empacotamento PyInstaller
└── requirements.txt
```

## Banco de dados

- Arquivo: `db/agile_backlog.db`, com caminho resolvido em `src/database.py`:
  - **Modo desenvolvimento**: usa o banco da pasta `db/` do projeto.
  - **Modo empacotado (Scrum.exe)**: usa/cria o banco na subpasta `db/` ao lado do executável, copiando o banco semente embutido na primeira execução.
- Tabelas de dados: `Product_Backlog`, `Sprints_Backlog`, `Historico_Sprints`, `Governanca`, `Transparencia`, `Qualidade`, `Roadmap` e vínculos `Backlog_Governanca`, `Backlog_Transparencia`, `Backlog_Qualidade`.
- Tabelas de referência (preservadas no "Novo projeto"): `Fibonacci`, `Status_ProductBacklog`, `Status_Sprint`.
- Para recriar a estrutura em um banco novo: `python db/create_tables.py`.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `python` não é reconhecido no terminal | Use o caminho completo do interpretador (ex.: `C:/Python314/python.exe src/main.py`) ou adicione o Python ao PATH |
| `ModuleNotFoundError: No module named 'pandas'` (ou outra dependência) | Execute `pip install -r requirements.txt` |
| Gráficos dos Dashboards não aparecem | Instale o matplotlib (`pip install matplotlib`); o restante do app continua funcionando |
| Antivírus/SmartScreen bloqueia o Scrum.exe | Clique em "Mais informações" → "Executar assim mesmo" (comum em executáveis PyInstaller não assinados) |
| Dados "sumiram" após usar o exe | O exe usa o banco em `db/` **ao lado dele**, não o banco do projeto; copie o `agile_backlog.db` desejado para essa pasta |

## Observações

- Todos os grids dimensionam as colunas automaticamente pelo conteúdo.
- Arquivos CSV usam codificação `utf-8-sig` (abrem corretamente no Excel).
- Se o matplotlib não estiver instalado, os Dashboards mostram um aviso nos gráficos sem interromper o restante da aplicação.
