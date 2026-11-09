import sqlite3
import shutil
import sys
import re
from pathlib import Path
from data_transfer import normalize_one_decimal

if getattr(sys, "frozen", False):
    _BUNDLE_DIR = Path(sys._MEIPASS)
    _DB_DIR = Path(sys.executable).resolve().parent / "db"
else:
    _BUNDLE_DIR = Path(__file__).resolve().parent.parent
    _DB_DIR = _BUNDLE_DIR / "db"
_DB_DIR.mkdir(parents=True, exist_ok=True)
SEED_DB = _BUNDLE_DIR / "db" / "agile_backlog.db"
DB_NAME = _DB_DIR / "agile_backlog.db"
if not DB_NAME.exists() and SEED_DB != DB_NAME and SEED_DB.exists():
    shutil.copy(SEED_DB, DB_NAME)


def connect_db(db_path=DB_NAME):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required_tables = {"Product_Backlog", "Sprints_Backlog", "Historico_Sprints"}
        if required_tables <= tables:
            stories = {
                str(story_id).upper(): story_id
                for story_id, in conn.execute("SELECT Id FROM Product_Backlog")
            }
            tasks = conn.execute(
                "SELECT Id_Task, User_Story FROM Sprints_Backlog"
            ).fetchall()
            for task_id, user_story in tasks:
                match = re.match(r"^(US-\d+)(?:\s|$)", str(user_story or ""), re.IGNORECASE)
                story_id = stories.get(match.group(1).upper()) if match else None
                if story_id is not None and user_story != story_id:
                    conn.execute(
                        "UPDATE Sprints_Backlog SET User_Story=? WHERE Id_Task=?",
                        (story_id, task_id),
                    )

            histories = conn.execute("""
                SELECT H.Id_Historico, S.User_Story
                FROM Historico_Sprints AS H
                JOIN Sprints_Backlog AS S ON S.Id_Task = H.Id_Task
                WHERE H.User_Story != S.User_Story
                   OR H.User_Story IS NULL
            """).fetchall()
            for history_id, task_story in histories:
                conn.execute(
                    "UPDATE Historico_Sprints SET User_Story=? WHERE Id_Historico=?",
                    (task_story, history_id),
                )
            conn.execute("PRAGMA user_version = 1")
            conn.commit()
    return conn


def get_fibonacci():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Story_Points, Significado, Exemplos_de_Tarefas FROM Fibonacci")
    data = cursor.fetchall()
    conn.close()
    return {str(row[0]): {"Significado": row[1], "Exemplos": row[2]} for row in data}
    # ...existing code...

def get_sprints():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Titulo_Sprint FROM Sprints_Backlog")
    data = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return data

def get_status_product_backlog():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Status, Significado, Quando_usar FROM Status_ProductBacklog")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: {"Significado": row[1], "Quando_usar": row[2]} for row in data}

def get_status_sprint():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Status, Significado, Quando_usar FROM Status_Sprint ORDER BY Id_StSp")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: {"Significado": row[1], "Quando_usar": row[2]} for row in data}

def get_product_backlog_stories():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Modulo, Story_Points FROM Product_Backlog ORDER BY Id")
    data = cursor.fetchall()
    conn.close()
    return data

def list_sprint_backlog():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT S.Id_Task, S.Titulo_Sprint,
               COALESCE(P.Id || ' ' || P.Modulo, S.User_Story),
               S.Subtarefa_Tecnica, S.Responsavel, S.Story_Points,
               S.Horas_Estimadas, S.Horas_Gastas, S.Horas_Restantes,
               S.Status, S.Data_Conclusao
        FROM Sprints_Backlog AS S
        LEFT JOIN Product_Backlog AS P ON P.Id = S.User_Story
        ORDER BY S.Id_Task
    """)
    data = cursor.fetchall()
    conn.close()
    return data

def insert_sprint_backlog(id_task, titulo_sprint, user_story, subtarefa, responsavel,
                          story_points, horas_estimadas, horas_gastas, horas_restantes,
                          status, data_conclusao):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Sprints_Backlog (
            Id_Task, Titulo_Sprint, User_Story, Subtarefa_Tecnica, Responsavel,
            Story_Points, Horas_Estimadas, Horas_Gastas, Horas_Restantes,
            Status, Data_Conclusao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (id_task, titulo_sprint, user_story, subtarefa, responsavel, story_points,
          horas_estimadas, horas_gastas, horas_restantes, status, data_conclusao))
    conn.commit()
    conn.close()

def update_sprint_backlog(id_task, titulo_sprint, user_story, subtarefa, responsavel,
                          story_points, horas_estimadas, horas_gastas, horas_restantes,
                          status, data_conclusao):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Sprints_Backlog
        SET Titulo_Sprint=?, User_Story=?, Subtarefa_Tecnica=?, Responsavel=?,
            Story_Points=?, Horas_Estimadas=?, Horas_Gastas=?, Horas_Restantes=?,
            Status=?, Data_Conclusao=?
        WHERE Id_Task=?
    """, (titulo_sprint, user_story, subtarefa, responsavel, story_points,
          horas_estimadas, horas_gastas, horas_restantes, status, data_conclusao,
          id_task))
    conn.commit()
    conn.close()

def delete_sprint_backlog(id_task):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Sprints_Backlog WHERE Id_Task=?", (id_task,))
    conn.commit()
    conn.close()

def get_history_sprint_titles():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Titulo_Sprint FROM Sprints_Backlog WHERE Titulo_Sprint IS NOT NULL AND Titulo_Sprint != '' ORDER BY Titulo_Sprint")
    data = [row[0] for row in cursor.fetchall()]
    conn.close()
    return data

def get_sprint_task_for_history(id_task):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT S.Id_Task, S.Titulo_Sprint, S.User_Story, S.Story_Points,
               S.Horas_Estimadas, S.Status, P.Id || ' ' || P.Modulo
        FROM Sprints_Backlog AS S
        LEFT JOIN Product_Backlog AS P ON P.Id = S.User_Story
        WHERE S.Id_Task = ?
    """, (id_task,))
    data = cursor.fetchone()
    conn.close()
    return data

def list_history_sprints():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT H.Id_Historico, H.Id_Task, H.Titulo_Sprint,
               COALESCE(P.Id || ' ' || P.Modulo, H.User_Story),
               H.Data_Inicio, H.Data_Fim, H.Pontos_Planejados,
               H.Pontos_Entregues, H.Velocity, H.Capacidade_Horas,
               H.Status_Sprint
        FROM Historico_Sprints AS H
        LEFT JOIN Product_Backlog AS P ON P.Id = H.User_Story
        ORDER BY H.Id_Historico
    """)
    data = cursor.fetchall()
    conn.close()
    return data

def insert_history_sprint(id_historico, id_task, titulo_sprint, user_story, data_inicio,
                          data_fim, pontos_planejados, pontos_entregues, velocity,
                          capacidade_horas, status_sprint):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Historico_Sprints (
            Id_Historico, Id_Task, Titulo_Sprint, User_Story, Data_Inicio, Data_Fim,
            Pontos_Planejados, Pontos_Entregues, Velocity, Capacidade_Horas, Status_Sprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (id_historico, id_task, titulo_sprint, user_story, data_inicio, data_fim,
          pontos_planejados, pontos_entregues, velocity, capacidade_horas, status_sprint))
    conn.commit()
    conn.close()

def update_history_sprint(id_historico, id_task, titulo_sprint, user_story, data_inicio,
                          data_fim, pontos_planejados, pontos_entregues, velocity,
                          capacidade_horas, status_sprint):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Historico_Sprints
        SET Id_Task=?, Titulo_Sprint=?, User_Story=?, Data_Inicio=?, Data_Fim=?,
            Pontos_Planejados=?, Pontos_Entregues=?, Velocity=?, Capacidade_Horas=?,
            Status_Sprint=?
        WHERE Id_Historico=?
    """, (id_task, titulo_sprint, user_story, data_inicio, data_fim, pontos_planejados,
          pontos_entregues, velocity, capacidade_horas, status_sprint, id_historico))
    conn.commit()
    conn.close()

def delete_history_sprint(id_historico):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Historico_Sprints WHERE Id_Historico=?", (id_historico,))
    conn.commit()
    conn.close()

def insert_product_backlog(id, modulo, historia, prioridade, story_points, sprint, status, observacoes):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Product_Backlog (Id, Modulo, Historia_Usuario, Prioridade, Story_Points, Sprint_Alocada, Status, Observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (id, modulo, historia, prioridade, story_points, sprint, status, observacoes))
    conn.commit()
    conn.close()

def list_product_backlog():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Modulo, Historia_Usuario, Prioridade, Story_Points, Sprint_Alocada, Status, Observacoes FROM Product_Backlog")
    data = cursor.fetchall()
    conn.close()
    return data

def update_product_backlog(id, modulo, historia, prioridade, story_points, sprint, status, observacoes):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Product_Backlog
        SET Modulo=?, Historia_Usuario=?, Prioridade=?, Story_Points=?, Sprint_Alocada=?, Status=?, Observacoes=?
        WHERE Id=?
    """, (modulo, historia, prioridade, story_points, sprint, status, observacoes, id))
    conn.commit()
    conn.close()

def delete_product_backlog(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Product_Backlog WHERE Id=?", (id,))
    conn.commit()
    conn.close()

def get_governance_statuses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Status FROM Governanca WHERE Status IS NOT NULL AND Status != '' ORDER BY Status")
    statuses = [row[0] for row in cursor.fetchall()]
    conn.close()
    return statuses

def get_governance_backlog_options():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Modulo FROM Product_Backlog ORDER BY Id")
    records = cursor.fetchall()
    conn.close()
    return records

def list_governanca():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT G.Id_Gov, G.Politica, G.Responsavel, G.Periodicidade, G.Status,
               COUNT(B.Id_Backlog)
        FROM Governanca AS G
        LEFT JOIN Backlog_Governanca AS B ON B.Id_Gov = G.Id_Gov
        GROUP BY G.Id_Gov, G.Politica, G.Responsavel, G.Periodicidade, G.Status
        ORDER BY G.Id_Gov
    """)
    records = cursor.fetchall()
    conn.close()
    return records

def get_governanca_backlog_ids(id_gov):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id_Backlog FROM Backlog_Governanca WHERE Id_Gov=? ORDER BY Id_Backlog", (id_gov,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def save_governanca(id_gov, politica, responsavel, periodicidade, status, backlog_ids):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        if id_gov is None:
            cursor.execute("SELECT COALESCE(MAX(Id_Gov), 0) + 1 FROM Governanca")
            id_gov = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO Governanca (Id_Gov, Politica, Responsavel, Periodicidade, Status)
                VALUES (?, ?, ?, ?, ?)
            """, (id_gov, politica, responsavel, periodicidade, status))
        else:
            cursor.execute("""
                UPDATE Governanca
                SET Politica=?, Responsavel=?, Periodicidade=?, Status=?
                WHERE Id_Gov=?
            """, (politica, responsavel, periodicidade, status, id_gov))
        cursor.execute("DELETE FROM Backlog_Governanca WHERE Id_Gov=?", (id_gov,))
        cursor.executemany(
            "INSERT INTO Backlog_Governanca (Id_Backlog, Id_Gov) VALUES (?, ?)",
            [(backlog_id, id_gov) for backlog_id in sorted(set(backlog_ids))],
        )
        conn.commit()
        return id_gov
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_governanca(id_gov):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Backlog_Governanca WHERE Id_Gov=?", (id_gov,))
        cursor.execute("DELETE FROM Governanca WHERE Id_Gov=?", (id_gov,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def list_transparencia():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT T.Id_Transp, T.Relatorio, T.Frequencia_Publicacao, T.Responsavel,
               T.Visibilidade,
               (SELECT COUNT(1) FROM Backlog_Transparencia AS B WHERE B.Id_Transp = T.Id_Transp),
               COALESCE((
                   SELECT GROUP_CONCAT(StoryLink, '; ')
                   FROM (
                       SELECT B.Id_Backlog || ' | ' || COALESCE(P.Modulo, '') AS StoryLink
                       FROM Backlog_Transparencia AS B
                       LEFT JOIN Product_Backlog AS P ON P.Id = B.Id_Backlog
                       WHERE B.Id_Transp = T.Id_Transp
                       ORDER BY B.Id_Backlog
                   )
               ), '')
        FROM Transparencia AS T
        ORDER BY T.Id_Transp
    """)
    records = cursor.fetchall()
    conn.close()
    return records

def get_transparencia_backlog_ids(id_transp):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id_Backlog FROM Backlog_Transparencia WHERE Id_Transp=? ORDER BY Id_Backlog", (id_transp,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def save_transparencia(id_transp, relatorio, frequencia, responsavel, visibilidade, backlog_ids):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        if id_transp is None:
            cursor.execute("SELECT COALESCE(MAX(Id_Transp), 0) + 1 FROM Transparencia")
            id_transp = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO Transparencia (Id_Transp, Relatorio, Frequencia_Publicacao, Responsavel, Visibilidade)
                VALUES (?, ?, ?, ?, ?)
            """, (id_transp, relatorio, frequencia, responsavel, visibilidade))
        else:
            cursor.execute("""
                UPDATE Transparencia
                SET Relatorio=?, Frequencia_Publicacao=?, Responsavel=?, Visibilidade=?
                WHERE Id_Transp=?
            """, (relatorio, frequencia, responsavel, visibilidade, id_transp))
        cursor.execute("DELETE FROM Backlog_Transparencia WHERE Id_Transp=?", (id_transp,))
        cursor.executemany(
            "INSERT INTO Backlog_Transparencia (Id_Backlog, Id_Transp) VALUES (?, ?)",
            [(backlog_id, id_transp) for backlog_id in sorted(set(backlog_ids))],
        )
        conn.commit()
        return id_transp
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_transparencia(id_transp):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Backlog_Transparencia WHERE Id_Transp=?", (id_transp,))
        cursor.execute("DELETE FROM Transparencia WHERE Id_Transp=?", (id_transp,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def list_qualidade():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Q.Id_Qualidade, Q.Metrica, Q.Valor_Alvo, Q.Valor_Real, Q.Status,
               (SELECT COUNT(1) FROM Backlog_Qualidade AS B WHERE B.Id_Qualidade = Q.Id_Qualidade),
               COALESCE((
                   SELECT GROUP_CONCAT(StoryLink, '; ')
                   FROM (
                       SELECT B.Id_Backlog || ' | ' || COALESCE(P.Modulo, '') AS StoryLink
                       FROM Backlog_Qualidade AS B
                       LEFT JOIN Product_Backlog AS P ON P.Id = B.Id_Backlog
                       WHERE B.Id_Qualidade = Q.Id_Qualidade
                       ORDER BY B.Id_Backlog
                   )
               ), '')
        FROM Qualidade AS Q
        ORDER BY Q.Id_Qualidade
    """)
    records = cursor.fetchall()
    conn.close()
    return records

def get_qualidade_backlog_ids(id_qualidade):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id_Backlog FROM Backlog_Qualidade WHERE Id_Qualidade=? ORDER BY Id_Backlog", (id_qualidade,))
    records = [row[0] for row in cursor.fetchall()]
    conn.close()
    return records

def get_qualidade_statuses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Status FROM Qualidade WHERE Status IS NOT NULL AND Status != '' ORDER BY Status")
    values = [row[0] for row in cursor.fetchall()]
    conn.close()
    return values

def save_qualidade(id_qualidade, metrica, valor_alvo, valor_real, status, backlog_ids):
    valor_alvo = float(normalize_one_decimal(valor_alvo))
    valor_real = float(normalize_one_decimal(valor_real))
    conn = connect_db()
    try:
        cursor = conn.cursor()
        if id_qualidade is None:
            cursor.execute("SELECT COALESCE(MAX(Id_Qualidade), 0) + 1 FROM Qualidade")
            id_qualidade = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO Qualidade (Id_Qualidade, Metrica, Valor_Alvo, Valor_Real, Status)
                VALUES (?, ?, ?, ?, ?)
            """, (id_qualidade, metrica, valor_alvo, valor_real, status))
        else:
            cursor.execute("""
                UPDATE Qualidade
                SET Metrica=?, Valor_Alvo=?, Valor_Real=?, Status=?
                WHERE Id_Qualidade=?
            """, (metrica, valor_alvo, valor_real, status, id_qualidade))
        cursor.execute("DELETE FROM Backlog_Qualidade WHERE Id_Qualidade=?", (id_qualidade,))
        cursor.executemany(
            "INSERT INTO Backlog_Qualidade (Id_Backlog, Id_Qualidade) VALUES (?, ?)",
            [(backlog_id, id_qualidade) for backlog_id in sorted(set(backlog_ids))],
        )
        conn.commit()
        return id_qualidade
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_qualidade(id_qualidade):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Backlog_Qualidade WHERE Id_Qualidade=?", (id_qualidade,))
        cursor.execute("DELETE FROM Qualidade WHERE Id_Qualidade=?", (id_qualidade,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()

def reset_project_data(db_path=DB_NAME):
    conn = connect_db(db_path)
    try:
        cursor = conn.cursor()
        for table in (
            "Backlog_Governanca", "Backlog_Transparencia", "Backlog_Qualidade",
            "Historico_Sprints", "Sprints_Backlog", "Product_Backlog",
            "Governanca", "Transparencia", "Qualidade", "Roadmap",
        ):
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_database_tables(db_path=DB_NAME):
    conn = connect_db(db_path)
    try:
        table_names = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        tables = []
        for table_name in table_names:
            escaped_name = table_name.replace('"', '""')
            columns = [
                row[1] for row in conn.execute(f'PRAGMA table_info("{escaped_name}")')
            ]
            rows = conn.execute(f'SELECT * FROM "{escaped_name}"').fetchall()
            tables.append((table_name, columns, rows))
        return tables
    finally:
        conn.close()
