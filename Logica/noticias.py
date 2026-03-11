"""Geracao e persistencia de noticias para o modo carreira."""

from __future__ import annotations

from typing import Any


def _safe_int(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(padrao)


def _texto_limpo(valor: Any) -> str:
    return str(valor or "").strip()


class GeradorNoticias:
    """Facade simples para registrar noticias no banco."""

    LIMITE_NOTICIAS = 400

    def __init__(self, banco: dict[str, Any]):
        self.banco = banco if isinstance(banco, dict) else {}
        noticias = self.banco.get("noticias")
        if not isinstance(noticias, list):
            noticias = []
            self.banco["noticias"] = noticias
        self.noticias = noticias

    def _next_timestamp(self) -> int:
        if not self.noticias:
            return 1
        ultimo = max(
            (_safe_int(item.get("timestamp"), 0) for item in self.noticias if isinstance(item, dict)),
            default=0,
        )
        return max(1, ultimo + 1)

    def _conter_chave(self, chave: str) -> bool:
        if not chave:
            return False
        for item in self.noticias:
            if not isinstance(item, dict):
                continue
            if _texto_limpo(item.get("chave")) == chave:
                return True
        return False

    def adicionar(
        self,
        *,
        tipo: str,
        icone: str,
        titulo: str,
        texto: str,
        rodada: int | None = None,
        temporada: int | None = None,
        categoria_id: str | None = None,
        categoria_nome: str | None = None,
        chave: str = "",
    ) -> dict[str, Any] | None:
        if chave and self._conter_chave(chave):
            return None

        noticia = {
            "tipo": _texto_limpo(tipo) or "geral",
            "icone": _texto_limpo(icone) or "•",
            "titulo": _texto_limpo(titulo) or "Noticia",
            "texto": _texto_limpo(texto) or "-",
            "rodada": _safe_int(rodada, 0) if rodada is not None else None,
            "temporada": _safe_int(temporada, 0) if temporada is not None else None,
            "categoria_id": _texto_limpo(categoria_id),
            "categoria_nome": _texto_limpo(categoria_nome),
            "timestamp": self._next_timestamp(),
            "chave": _texto_limpo(chave),
        }
        self.noticias.append(noticia)
        excesso = len(self.noticias) - int(self.LIMITE_NOTICIAS)
        if excesso > 0:
            del self.noticias[:excesso]
        return noticia

    def gerar_noticia_corrida(
        self,
        *,
        resultado: list[dict[str, Any]] | None,
        categoria_nome: str,
        rodada: int | None,
        temporada: int | None,
        circuito: str = "",
        categoria_id: str = "",
    ) -> dict[str, Any] | None:
        vencedor = "Piloto sem nome"
        if isinstance(resultado, list):
            for item in resultado:
                if not isinstance(item, dict):
                    continue
                if bool(item.get("dnf", False)):
                    continue
                vencedor = _texto_limpo(
                    item.get("piloto_nome", item.get("piloto", item.get("nome", "")))
                ) or vencedor
                break
        pista = _texto_limpo(circuito)
        if pista:
            texto = f"{vencedor} vence em {pista}."
        else:
            texto = f"{vencedor} venceu a rodada."
        rodada_txt = _safe_int(rodada, 0)
        titulo = f"Rodada {rodada_txt} - {categoria_nome}" if rodada_txt > 0 else f"{categoria_nome}"
        chave = f"corrida:{temporada}:{categoria_id or categoria_nome}:{rodada_txt}"
        return self.adicionar(
            tipo="corrida",
            icone="🏆",
            titulo=titulo,
            texto=texto,
            rodada=rodada,
            temporada=temporada,
            categoria_id=categoria_id,
            categoria_nome=categoria_nome,
            chave=chave,
        )

    def gerar_noticia_incidente(
        self,
        *,
        incidente: str,
        categoria_nome: str,
        rodada: int | None,
        temporada: int | None,
        categoria_id: str = "",
    ) -> dict[str, Any] | None:
        texto = _texto_limpo(incidente)
        if not texto:
            return None
        rodada_txt = _safe_int(rodada, 0)
        titulo = (
            f"Incidente - Rodada {rodada_txt} - {categoria_nome}"
            if rodada_txt > 0
            else f"Incidente - {categoria_nome}"
        )
        chave = f"incidente:{temporada}:{categoria_id or categoria_nome}:{rodada_txt}:{texto.casefold()}"
        return self.adicionar(
            tipo="incidente",
            icone="💥",
            titulo=titulo,
            texto=texto,
            rodada=rodada,
            temporada=temporada,
            categoria_id=categoria_id,
            categoria_nome=categoria_nome,
            chave=chave,
        )

    def gerar_noticia_mercado(
        self,
        *,
        transferencia: dict[str, Any],
        temporada: int | None,
    ) -> dict[str, Any] | None:
        if not isinstance(transferencia, dict):
            return None
        piloto = _texto_limpo(transferencia.get("piloto", "Piloto"))
        origem = _texto_limpo(transferencia.get("origem", "origem desconhecida"))
        destino = _texto_limpo(transferencia.get("destino", "destino desconhecido"))
        papel = _texto_limpo(transferencia.get("papel", ""))
        duracao = _safe_int(transferencia.get("duracao"), 0)
        detalhes = []
        if papel:
            detalhes.append(papel)
        if duracao > 0:
            detalhes.append(f"{duracao} ano(s)")
        detalhe_txt = f" ({', '.join(detalhes)})" if detalhes else ""
        texto = f"{piloto}: {origem} -> {destino}{detalhe_txt}."
        chave = f"mercado:{temporada}:{piloto.casefold()}:{destino.casefold()}:{duracao}"
        return self.adicionar(
            tipo="mercado",
            icone="📋",
            titulo="Mercado - Transferencia",
            texto=texto,
            temporada=temporada,
            chave=chave,
        )

    def gerar_noticia_promocao(
        self,
        *,
        equipe: str,
        origem: str,
        destino: str,
        temporada: int | None,
        tipo_evento: str = "promocao",
    ) -> dict[str, Any] | None:
        equipe_txt = _texto_limpo(equipe) or "Equipe"
        origem_txt = _texto_limpo(origem) or "?"
        destino_txt = _texto_limpo(destino) or "?"
        if tipo_evento == "rebaixamento":
            titulo = "Rebaixamento de equipe"
            icone = "⬇️"
        else:
            titulo = "Promocao de equipe"
            icone = "⬆️"
        texto = f"{equipe_txt}: {origem_txt} -> {destino_txt}."
        chave = f"{tipo_evento}:{temporada}:{equipe_txt.casefold()}:{origem_txt.casefold()}:{destino_txt.casefold()}"
        return self.adicionar(
            tipo=tipo_evento,
            icone=icone,
            titulo=titulo,
            texto=texto,
            temporada=temporada,
            chave=chave,
        )

    def gerar_noticia_aposentadoria(
        self,
        *,
        piloto: dict[str, Any],
        temporada: int | None,
    ) -> dict[str, Any] | None:
        if not isinstance(piloto, dict):
            return None
        nome = _texto_limpo(piloto.get("nome", "Piloto"))
        idade = _safe_int(piloto.get("idade"), 0)
        titulos = _safe_int(piloto.get("titulos"), 0)
        vitorias = _safe_int(piloto.get("vitorias"), 0)
        texto = f"{nome} ({idade}) encerra a carreira. Titulos: {titulos} | Vitorias: {vitorias}."
        chave = f"aposentadoria:{temporada}:{nome.casefold()}:{idade}"
        return self.adicionar(
            tipo="aposentadoria",
            icone="👴",
            titulo="Aposentadoria",
            texto=texto,
            temporada=temporada,
            chave=chave,
        )

    def gerar_noticia_rookie(
        self,
        *,
        rookies: list[dict[str, Any]],
        temporada: int | None,
    ) -> dict[str, Any] | None:
        if not isinstance(rookies, list) or not rookies:
            return None
        nomes = [
            _texto_limpo(item.get("piloto", item.get("nome", "")))
            for item in rookies
            if isinstance(item, dict)
        ]
        nomes = [nome for nome in nomes if nome]
        if not nomes:
            return None
        texto = ", ".join(nomes[:5])
        if len(nomes) > 5:
            texto = f"{texto} e mais {len(nomes) - 5}"
        chave = f"rookies:{temporada}:{'|'.join(sorted(nome.casefold() for nome in nomes))}"
        return self.adicionar(
            tipo="rookies",
            icone="🎓",
            titulo="Novos talentos",
            texto=f"Entraram na temporada: {texto}.",
            temporada=temporada,
            chave=chave,
        )

    def gerar_noticia_hierarquia(
        self,
        *,
        equipe_nome: str,
        evento: str,
        temporada: int | None,
        rodada: int | None,
    ) -> dict[str, Any] | None:
        equipe = _texto_limpo(equipe_nome) or "Equipe"
        evento_txt = _texto_limpo(evento)
        if not evento_txt:
            return None
        chave = f"hierarquia:{temporada}:{rodada}:{equipe.casefold()}:{evento_txt.casefold()}"
        return self.adicionar(
            tipo="hierarquia",
            icone="⚡",
            titulo=f"Dinamica interna - {equipe}",
            texto=evento_txt,
            temporada=temporada,
            rodada=rodada,
            chave=chave,
        )

    def gerar_noticia_milestone(
        self,
        *,
        jogador: dict[str, Any] | None,
        milestone: dict[str, Any] | None,
        temporada: int | None,
        rodada: int | None,
        categoria_id: str = "",
        categoria_nome: str = "",
    ) -> dict[str, Any] | None:
        """Registra noticia especial quando um marco de carreira e desbloqueado."""
        if not isinstance(milestone, dict):
            return None

        titulo_m = _texto_limpo(milestone.get("titulo", "Marco de carreira"))
        descricao = _texto_limpo(milestone.get("descricao", ""))
        icone_m = _texto_limpo(milestone.get("icone", "🏆")) or "🏆"
        jogador_nome = _texto_limpo((jogador or {}).get("nome", "Jogador")) or "Jogador"
        milestone_id = _texto_limpo(milestone.get("id", "")).casefold()

        texto = f"{jogador_nome} desbloqueou o marco '{titulo_m}'."
        if descricao:
            texto = f"{texto} {descricao}"

        chave = f"milestone:{temporada}:{rodada}:{jogador_nome.casefold()}:{milestone_id}"
        return self.adicionar(
            tipo="milestone",
            icone=icone_m,
            titulo=f"Marco de carreira - {titulo_m}",
            texto=texto,
            rodada=rodada,
            temporada=temporada,
            categoria_id=categoria_id,
            categoria_nome=categoria_nome,
            chave=chave,
        )

    def gerar_noticia_lesao(
        self,
        *,
        piloto_nome: str,
        lesao: dict[str, Any],
        temporada: int | None,
        rodada: int | None,
        tipo_evento: str = "lesao",
    ) -> dict[str, Any] | None:
        nome = _texto_limpo(piloto_nome) or "Piloto"
        if tipo_evento == "retorno":
            titulo = "Retorno de lesao"
            texto = f"{nome} esta de volta ao grid."
            icone = "🏥"
        else:
            tipo = _texto_limpo(lesao.get("tipo", "lesao"))
            corridas = _safe_int(lesao.get("corridas_restantes"), 0)
            titulo = "Lesao"
            texto = f"{nome} sofreu lesao ({tipo}) e deve ficar {corridas} corrida(s) fora."
            icone = "🏥"
        chave = f"{tipo_evento}:{temporada}:{rodada}:{nome.casefold()}:{_texto_limpo(texto).casefold()}"
        return self.adicionar(
            tipo=tipo_evento,
            icone=icone,
            titulo=titulo,
            texto=texto,
            temporada=temporada,
            rodada=rodada,
            chave=chave,
        )


def listar_noticias_ordenadas(
    banco: dict[str, Any],
    *,
    tipo: str = "",
    limite: int | None = None,
) -> list[dict[str, Any]]:
    noticias = banco.get("noticias", []) if isinstance(banco, dict) else []
    if not isinstance(noticias, list):
        return []

    tipo_norm = _texto_limpo(tipo).casefold()
    filtradas = [
        item
        for item in noticias
        if isinstance(item, dict)
        and (not tipo_norm or _texto_limpo(item.get("tipo")).casefold() == tipo_norm)
    ]
    filtradas.sort(key=lambda item: _safe_int(item.get("timestamp"), 0), reverse=True)
    if isinstance(limite, int) and limite > 0:
        return filtradas[:limite]
    return filtradas
