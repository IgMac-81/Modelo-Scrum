import subprocess

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def atualizar_github():
    # Verifica se há alterações
    status = run(["git", "status", "--porcelain"])
    if not status:
        print("Nenhuma alteração detectada. Nada a commitar.")
        return

    # Adiciona todas as mudanças
    subprocess.run(["git", "add", "."], check=True)

    # Cria commit automático
    subprocess.run(["git", "commit", "-m", "auto: atualização de cadastro"], check=True)

    # Envia para o GitHub
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("Alterações enviadas para o GitHub com sucesso!")

if __name__ == "__main__":
    atualizar_github()

'''
Script para automatizar commits e push no GitHub.
Verifica alterações, adiciona, comita e envia para o repositório remoto.
rode:
python auto_commit.py
inclua nas funções que salvam, editam e excluem registros nos formulários a chamada para atualizar_github() para automatizar o commit e push.
'''