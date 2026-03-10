"""Wrapper de compatibilidade para iniciar a aplicacao.

Mantem o comando legado `python main.py`, delegando para `Projeto/main.py`.
"""

from Projeto.main import main


if __name__ == "__main__":
    main()
