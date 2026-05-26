"""Handler Mail : lecture de la boîte Gmail via IMAP (mot de passe d'application).

Lecture seule (résumé des non-lus, derniers mails). Pas d'envoi (volontaire).
imaplib + email = bibliothèque standard Python, aucune dépendance externe.

Config (.env) :
    MAIL_IMAP_HOST       défaut "imap.gmail.com"
    MAIL_ADDRESS         adresse e-mail (ex: s2drenovation@gmail.com)
    MAIL_APP_PASSWORD    mot de passe d'application Google (16 caractères)

Si non configuré OU EXECUTION_MODE != production → réponse SIMULÉE (aucune connexion).
Chaque réponse inclut un champ `answer` (phrase orale) prononcé par Jarvis.
"""
from __future__ import annotations

import asyncio
import email
import imaplib
import os
import time
from email.header import decode_header, make_header
from typing import Any

from jarvis.domain.types import DeviceCommand, ExecutionResult, ExecutionStatus

_DEFAULT_HOST = "imap.gmail.com"
_MAX_LISTED = 5  # nb de mails détaillés à l'oral


class MailImapHandler:
    def __init__(self, host: str | None = None, address: str | None = None,
                 password: str | None = None) -> None:
        self._host = host or os.getenv("MAIL_IMAP_HOST", _DEFAULT_HOST)
        self._address = address or os.getenv("MAIL_ADDRESS", "")
        self._password = password if password is not None else os.getenv("MAIL_APP_PASSWORD", "")
        self._mode = os.getenv("EXECUTION_MODE", "mock").lower()

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        start = time.perf_counter()
        intent = command.params.get("intent", "")

        if self._mode != "production" or not self._password or not self._address:
            return self._ok(command, start, {
                "simulated": True, "intent": intent,
                "answer": "Vous avez 2 nouveaux messages : un de la MAAF, un de Pôle emploi. (simulation)",
            })
        try:
            count = int(command.params.get("count", _MAX_LISTED))
            only_unread = intent == "check_mail"
            response = await asyncio.to_thread(self._read_sync, only_unread, count)
        except Exception as e:  # noqa: BLE001
            return ExecutionResult(
                status=ExecutionStatus.failure, correlation_id=command.correlation_id,
                device_url=command.device_url, action=command.action,
                error=f"Messagerie indisponible : {type(e).__name__}: {e}",
            )
        return self._ok(command, start, response)

    def _read_sync(self, only_unread: bool, count: int) -> dict[str, Any]:
        count = max(1, min(10, count))
        M = imaplib.IMAP4_SSL(self._host)
        try:
            M.login(self._address, self._password)
            M.select("INBOX", readonly=True)
            criterion = "UNSEEN" if only_unread else "ALL"
            typ, data = M.search(None, criterion)
            ids = data[0].split() if data and data[0] else []
            total = len(ids)
            mails: list[dict[str, str]] = []
            for num in reversed(ids[-count:]):
                typ, msg_data = M.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
                raw = msg_data[0][1] if msg_data and msg_data[0] else b""
                msg = email.message_from_bytes(raw)
                mails.append({
                    "from": _clean(_decode(msg.get("From", ""))),
                    "subject": _decode(msg.get("Subject", "(sans objet)")),
                })
        finally:
            try:
                M.logout()
            except Exception:  # noqa: BLE001
                pass
        return {
            "intent": "check_mail" if only_unread else "recent_mails",
            "unread_total": total, "mails": mails,
            "answer": _build_answer(only_unread, total, mails),
        }

    def _ok(self, command: DeviceCommand, start: float, response: dict[str, Any]) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.success, correlation_id=command.correlation_id,
            device_url=command.device_url, action=command.action,
            duration_ms=int((time.perf_counter() - start) * 1000), response=response,
        )


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:  # noqa: BLE001
        return value.strip()


def _clean(sender: str) -> str:
    """'Nom <a@b.com>' -> 'Nom' ; sinon l'adresse."""
    if "<" in sender:
        name = sender.split("<", 1)[0].strip().strip('"')
        if name:
            return name
        return sender.split("<", 1)[1].rstrip(">").strip()
    return sender


def _build_answer(only_unread: bool, total: int, mails: list[dict[str, str]]) -> str:
    if only_unread:
        if total == 0:
            return "Vous n'avez aucun message non lu, Monsieur."
        intro = f"Vous avez {total} message{'s' if total > 1 else ''} non lu{'s' if total > 1 else ''}"
    else:
        if not mails:
            return "Votre boîte de réception est vide, Monsieur."
        intro = "Vos derniers messages"
    bits = [f"de {m['from']}, {m['subject']}" for m in mails]
    return intro + " : " + " ; ".join(bits) + "."
