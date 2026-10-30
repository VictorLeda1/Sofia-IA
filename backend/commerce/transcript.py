"""Exportação local da conversa, sem prompt, chave ou resultados internos das ferramentas."""

import logging
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings

logger = logging.getLogger(__name__)
SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def save_conversation(session):
    """Cria o arquivo no primeiro diálogo e o atualiza após cada nova mensagem."""
    if not settings.SOFIA_EXPORT_CONVERSATIONS:
        return
    if not any(message["role"] == "user" for message in session["messages"]):
        return
    directory = Path(settings.REPO_DIR) / "docs" / "conversas"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if "transcript_filename" not in session:
            started = datetime.now(SAO_PAULO).strftime("%Y-%m-%d_%H-%M-%S")
            session["transcript_filename"] = f"{started}_{session['id']}.txt"
        target = directory / session["transcript_filename"]
        lines = ["Conversa Sofia IA — ambiente de teste", "Dados usados nesta conversa devem ser fictícios.", ""]
        for message in session["messages"]:
            speaker = "CLIENTE" if message["role"] == "user" else "SOFIA"
            lines.append(f"{speaker}: {message['text']}")
            if message.get("cards"):
                lines.append("Produtos exibidos: " + ", ".join(message["cards"]))
            lines.append("")
        if session["orders"]:
            lines.append("Pedidos nesta conversa:")
            for order in session["orders"].values():
                lines.append(f"- {order['id']}: {order['status']}")
        temporary = directory / f".{session['transcript_filename']}.{uuid4().hex}.tmp"
        try:
            temporary.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError:
        logger.exception("Não foi possível salvar a conversa local")
