"""Handler Agenda réel : Google Calendar via compte de service (Service Account).

Lecture + écriture. Le compte de service doit avoir l'API Calendar activée, et
l'agenda de Denis doit lui être PARTAGÉ (droit « Apporter des modifications aux
événements »). Le calendarId = l'adresse de l'agenda partagé (ex: l'e-mail Google).

Config (.env) :
    GOOGLE_SA_KEY_FILE   chemin du JSON du compte de service
    AGENDA_CALENDAR_ID   id de l'agenda (souvent l'e-mail Google de Denis)
    AGENDA_TIMEZONE      défaut "Europe/Paris"

Chaque réponse inclut un champ `answer` (phrase orale) pour que Jarvis la prononce.
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import date, datetime, time as dtime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from jarvis.domain.types import DeviceCommand, ExecutionResult, ExecutionStatus

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]


class AgendaGoogleHandler:
    """Accès Google Calendar (lecture + écriture) via compte de service."""

    def __init__(self, key_file: str | None = None, calendar_id: str | None = None,
                 timezone: str | None = None) -> None:
        self._key_file = key_file or os.getenv("GOOGLE_SA_KEY_FILE", "")
        self._calendar_id = calendar_id or os.getenv("AGENDA_CALENDAR_ID", "primary")
        self._tz = ZoneInfo(timezone or os.getenv("AGENDA_TIMEZONE", "Europe/Paris"))
        self._service = None

    def _svc(self):
        if self._service is None:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            creds = service_account.Credentials.from_service_account_file(
                self._key_file, scopes=_SCOPES)
            self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        start = time.perf_counter()
        intent = command.params.get("intent", "")
        try:
            response = await asyncio.to_thread(self._dispatch, intent, command.params)
        except Exception as e:  # noqa: BLE001
            return ExecutionResult(
                status=ExecutionStatus.failure, correlation_id=command.correlation_id,
                device_url=command.device_url, action=command.action,
                error=f"Agenda Google indisponible : {type(e).__name__}: {e}",
            )
        return ExecutionResult(
            status=ExecutionStatus.success, correlation_id=command.correlation_id,
            device_url=command.device_url, action=command.action,
            duration_ms=int((time.perf_counter() - start) * 1000), response=response,
        )

    # ------------------------------------------------------------------
    def _dispatch(self, intent: str, params: dict[str, Any]) -> dict[str, Any]:
        if intent == "list_events_today":
            d = datetime.now(self._tz).date()
            return self._list_day(d, "aujourd'hui")
        if intent == "list_events_tomorrow":
            d = datetime.now(self._tz).date() + timedelta(days=1)
            return self._list_day(d, "demain")
        if intent == "list_events_range":
            d0 = date.fromisoformat(params["start_date"])
            d1 = date.fromisoformat(params["end_date"])
            return self._list_range(d0, d1)
        if intent == "create_event":
            return self._create(params)
        if intent == "delete_event":
            return self._delete(params)
        if intent == "find_slot":
            return self._find_slot(params)
        raise ValueError(f"intent agenda inconnu : {intent!r}")

    def _fetch(self, t_min: datetime, t_max: datetime) -> list[dict[str, Any]]:
        res = self._svc().events().list(
            calendarId=self._calendar_id,
            timeMin=t_min.isoformat(), timeMax=t_max.isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=50,
        ).execute()
        return res.get("items", [])

    def _bounds(self, d: date) -> tuple[datetime, datetime]:
        t0 = datetime.combine(d, dtime.min, tzinfo=self._tz)
        return t0, t0 + timedelta(days=1)

    def _list_day(self, d: date, label: str) -> dict[str, Any]:
        items = self._fetch(*self._bounds(d))
        events = [self._serialize(e) for e in items]
        if not events:
            answer = f"Vous n'avez aucun rendez-vous {label}, Monsieur."
        else:
            bits = [f"{e['heure']}, {e['titre']}" for e in events]
            answer = f"{label.capitalize()}, vous avez {len(events)} rendez-vous : " + " ; ".join(bits) + "."
        return {"intent": "list_events", "events": events, "answer": answer}

    def _list_range(self, d0: date, d1: date) -> dict[str, Any]:
        if (d1 - d0).days > 31:
            raise ValueError("plage > 31 jours")
        t_min, _ = self._bounds(d0)
        _, t_max = self._bounds(d1)
        items = self._fetch(t_min, t_max)
        events = [self._serialize(e) for e in items]
        if not events:
            answer = "Vous n'avez aucun rendez-vous sur cette période, Monsieur."
        else:
            bits = [f"le {e['jour']} à {e['heure']}, {e['titre']}" for e in events]
            answer = f"Vous avez {len(events)} rendez-vous : " + " ; ".join(bits) + "."
        return {"intent": "list_events", "events": events, "answer": answer}

    def _create(self, params: dict[str, Any]) -> dict[str, Any]:
        start_dt = datetime.fromisoformat(params["start"])
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=self._tz)
        end_dt = start_dt + timedelta(minutes=int(params["duration_minutes"]))
        body: dict[str, Any] = {
            "summary": params["title"],
            "start": {"dateTime": start_dt.isoformat(), "timeZone": str(self._tz)},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": str(self._tz)},
        }
        if params.get("location"):
            body["location"] = params["location"]
        if params.get("description"):
            body["description"] = params["description"]
        ev = self._svc().events().insert(calendarId=self._calendar_id, body=body).execute()
        e = self._serialize(ev)
        answer = f"C'est noté, Monsieur : {e['titre']}, le {e['jour']} à {e['heure']}."
        return {"intent": "create_event", "event": e, "answer": answer}

    def _candidates(self, params: dict[str, Any]) -> list[dict[str, Any]] | None:
        """Retourne les événements correspondant aux critères. None = aucun critère fourni."""
        title_q = (params.get("title_query") or "").strip().lower()
        has_criteria = bool(title_q or params.get("date") or params.get("start"))
        if not has_criteria:
            return None

        sdt: datetime | None = None
        if params.get("start"):
            sdt = datetime.fromisoformat(params["start"])
            if sdt.tzinfo is None:
                sdt = sdt.replace(tzinfo=self._tz)
            items = self._fetch(*self._bounds(sdt.date()))
        elif params.get("date"):
            day = date.fromisoformat(params["date"])
            items = self._fetch(*self._bounds(day))
        else:
            now = datetime.now(self._tz)
            items = self._fetch(now - timedelta(days=1), now + timedelta(days=31))

        if title_q:
            items = [e for e in items if title_q in (e.get("summary", "") or "").lower()]

        if sdt is not None:
            timed = []
            for e in items:
                raw = e.get("start", {}).get("dateTime")
                if not raw:
                    continue
                try:
                    edt = datetime.fromisoformat(raw)
                except ValueError:
                    continue
                if edt.tzinfo is None:
                    edt = edt.replace(tzinfo=self._tz)
                if edt.hour == sdt.hour and edt.minute == sdt.minute:
                    timed.append(e)
            if timed:
                items = timed
        return items

    def _delete(self, params: dict[str, Any]) -> dict[str, Any]:
        cands = self._candidates(params)
        if cands is None:
            return {"intent": "delete_event", "deleted": None,
                    "answer": "Précisez quel rendez-vous supprimer, Monsieur — son titre ou sa date."}
        if not cands:
            return {"intent": "delete_event", "deleted": None,
                    "answer": "Je ne trouve aucun rendez-vous correspondant, Monsieur."}
        if len(cands) > 1:
            bits = []
            for e in cands[:5]:
                s = self._serialize(e)
                bits.append(f"{s['titre']} le {s['jour']} à {s['heure']}")
            return {"intent": "delete_event", "deleted": None, "ambiguous": True,
                    "answer": "J'ai trouvé plusieurs rendez-vous : " + " ; ".join(bits)
                              + ". Lequel dois-je supprimer, Monsieur ?"}
        ev = cands[0]
        self._svc().events().delete(calendarId=self._calendar_id, eventId=ev.get("id")).execute()
        s = self._serialize(ev)
        return {"intent": "delete_event", "deleted": s,
                "answer": f"C'est supprimé, Monsieur : {s['titre']}, le {s['jour']} à {s['heure']}."}

    def _find_slot(self, params: dict[str, Any]) -> dict[str, Any]:
        dur = timedelta(minutes=int(params["duration_minutes"]))
        earliest = datetime.fromisoformat(params["earliest"])
        latest = datetime.fromisoformat(params["latest"])
        if earliest.tzinfo is None:
            earliest = earliest.replace(tzinfo=self._tz)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=self._tz)
        items = self._fetch(earliest, latest)
        busy: list[tuple[datetime, datetime]] = []
        for e in items:
            s = e.get("start", {}).get("dateTime")
            en = e.get("end", {}).get("dateTime")
            if s and en:
                busy.append((datetime.fromisoformat(s), datetime.fromisoformat(en)))
        busy.sort()
        cursor = earliest
        for bs, be in busy:
            if bs - cursor >= dur:
                break
            cursor = max(cursor, be)
        slot = cursor if (latest - cursor) >= dur else None
        if slot is None:
            return {"intent": "find_slot", "slot": None,
                    "answer": "Je ne trouve aucun créneau libre sur cette période, Monsieur."}
        sl = self._serialize_dt(slot)
        return {"intent": "find_slot", "slot": slot.isoformat(),
                "answer": f"Un créneau est libre le {sl['jour']} à {sl['heure']}, Monsieur."}

    # ------------------------------------------------------------------
    def _serialize(self, ev: dict[str, Any]) -> dict[str, Any]:
        start = ev.get("start", {})
        raw = start.get("dateTime") or start.get("date")
        out = {"id": ev.get("id", ""), "titre": ev.get("summary", "(sans titre)"),
               "jour": "", "heure": "toute la journée",
               "location": ev.get("location", "")}
        if raw:
            try:
                dt = datetime.fromisoformat(raw)
                d = self._serialize_dt(dt if dt.tzinfo else dt.replace(tzinfo=self._tz))
                out["jour"], out["heure"] = d["jour"], d["heure"] if start.get("dateTime") else "toute la journée"
            except ValueError:
                pass
        return out

    def _serialize_dt(self, dt: datetime) -> dict[str, str]:
        dt = dt.astimezone(self._tz)
        return {"jour": f"{dt.day} {_MOIS[dt.month]}", "heure": f"{dt.hour}h{dt.minute:02d}"}
