import os


def consolidar_codigo():
    # Diretórios e arquivos que devem ser estritamente ignorados
    dirs_ignorados = {"data", "necessarios", "reports", "tests", "venv", "__pycache__"}
    arquivos_ignorados = {
        ".gitignore",
        "README.md",
        "requirements.txt",
        "agrupar_codigo.py",
        "tudo.txt",
    }

    arquivo_saida = "tudo.txt"

    with open(arquivo_saida, "w", encoding="utf-8") as outfile:
        # os.walk percorre a árvore de diretórios a partir da raiz('.')
        for root, dirs, files in os.walk("."):
            # Modifica a lista 'dirs' in-place para pular os diretórios ignorados e pastas ocultas (como .git)
            dirs[:] = [
                d for d in dirs if d not in dirs_ignorados and not d.startswith(".")
            ]

            for file in files:
                # Pular arquivos que não queremos ou que não são Python
                if file in arquivos_ignorados or not file.endswith(".py"):
                    continue

                caminho_completo = os.path.join(root, file)

                try:
                    with open(caminho_completo, "r", encoding="utf-8") as infile:
                        conteudo = infile.read()

                        # Cria um cabeçalho visual para separar os arquivos no txt final
                        outfile.write(f"\n{'='*60}\n")
                        outfile.write(f"### ARQUIVO: {caminho_completo} ###\n")
                        outfile.write(f"{'='*60}\n\n")

                        outfile.write(conteudo)
                        outfile.write("\n")

                except Exception as e:
                    print(f"Erro ao ler o arquivo {caminho_completo}: {e}")

    print(f"Processo concluído! Todo o código foi salvo em '{arquivo_saida}'.")


if __name__ == "__main__":
    consolidar_codigo()
