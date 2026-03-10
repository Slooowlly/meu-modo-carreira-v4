"""Wrapper de compatibilidade para baixar bandeiras.

Mantem o comando legado `python baixar_bandeiras.py` funcionando,
encaminhando para `Scripts/Manutencao/baixar_bandeiras.py`.
"""

from Scripts.Manutencao.baixar_bandeiras import baixar_bandeiras


if __name__ == "__main__":
    baixar_bandeiras()
