import sqlite3
from pathlib import Path

# Conectar ao banco
DB_NAME = Path(__file__).resolve().parent / "agile_backlog.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# -----------------------------
# Recriar tabelas
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS Product_Backlog (
    Id TEXT PRIMARY KEY,
    Modulo TEXT,
    Historia_Usuario TEXT,
    Prioridade TEXT,
    Story_Points INTEGER,
    Sprint_Alocada TEXT,
    Status TEXT,
    Observacoes TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Sprints_Backlog (
    Id_Task TEXT PRIMARY KEY,
    Titulo_Sprint TEXT,   -- Novo campo logo após Id_Task
    User_Story TEXT,
    Subtarefa_Tecnica TEXT,
    Responsavel TEXT,
    Story_Points INTEGER,
    Horas_Estimadas TEXT,
    Horas_Gastas TEXT,
    Horas_Restantes TEXT,
    Status TEXT,
    Data_Conclusao TEXT,
    FOREIGN KEY(User_Story) REFERENCES Product_Backlog(Id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Historico_Sprints (
    Id_Historico INTEGER PRIMARY KEY,
    Id_Task TEXT,
    Titulo_Sprint TEXT,   -- Novo campo incluído
    User_Story TEXT,
    Data_Inicio TEXT,
    Data_Fim TEXT,
    Pontos_Planejados INTEGER,
    Pontos_Entregues INTEGER,
    Velocity REAL,
    Capacidade_Horas TEXT,
    Status_Sprint TEXT,
    FOREIGN KEY(Id_Task) REFERENCES Sprints_Backlog(Id_Task),
    FOREIGN KEY(User_Story) REFERENCES Product_Backlog(Id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Roadmap (
    Id_Rm INTEGER PRIMARY KEY,
    Fase TEXT,
    Sprint TEXT,
    Periodo TEXT,
    Data TEXT,
    Principais_Entregas TEXT,
    Story_Points INTEGER,
    Status TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Fibonacci (
    Id_Fibonacci INTEGER PRIMARY KEY,
    Story_Points TEXT,
    Significado TEXT,
    Exemplos_de_Tarefas TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Status_ProductBacklog (
    Id_StPb INTEGER PRIMARY KEY,
    Status TEXT,
    Significado TEXT,
    Quando_usar TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Status_Sprint (
    Id_StSp INTEGER PRIMARY KEY,
    Status TEXT,
    Significado TEXT,
    Quando_usar TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Governanca (
    Id_Gov INTEGER PRIMARY KEY,
    Politica TEXT,
    Responsavel TEXT,
    Periodicidade TEXT,
    Status TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Transparencia (
    Id_Transp INTEGER PRIMARY KEY,
    Relatorio TEXT,
    Frequencia_Publicacao TEXT,
    Responsavel TEXT,
    Visibilidade TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Qualidade (
    Id_Qualidade INTEGER PRIMARY KEY,
    Metrica TEXT,
    Valor_Alvo REAL,
    Valor_Real REAL,
    Status TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Backlog_Governanca (
    Id_Backlog TEXT,
    Id_Gov INTEGER,
    FOREIGN KEY(Id_Backlog) REFERENCES Product_Backlog(Id),
    FOREIGN KEY(Id_Gov) REFERENCES Governanca(Id_Gov)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Backlog_Transparencia (
    Id_Backlog TEXT,
    Id_Transp INTEGER,
    FOREIGN KEY(Id_Backlog) REFERENCES Product_Backlog(Id),
    FOREIGN KEY(Id_Transp) REFERENCES Transparencia(Id_Transp)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Backlog_Qualidade (
    Id_Backlog TEXT,
    Id_Qualidade INTEGER,
    FOREIGN KEY(Id_Backlog) REFERENCES Product_Backlog(Id),
    FOREIGN KEY(Id_Qualidade) REFERENCES Qualidade(Id_Qualidade)
);
""")

# Salvar alterações
conn.commit()
conn.close()

print("Tabelas verificadas/criadas com sucesso.")
