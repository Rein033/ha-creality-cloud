"""Small async client for Creality Cloud (crealitycloud.com).

Creality does not publish an API for this. The endpoints below come from the Creality Cloud website and may change
without notice. Only the international region (crealitycloud.com) is supported.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import aiohttp

ID_HOST = "https://id.creality.com"
API_HOST = "https://api.crealitycloud.com"
CLIENT_ID = "f9c302ecc29c59a0a6e921ff39a073ca"
APP_VER = "7.3.28"

LOGIN = "/api/cxy/account/v2/loginV2"
DEVICES = "/api/rest/print/cluster/devices/getDeviceList"
RPC = "/api/rest/iotrouter/rpc/twoway/"

THUMB_HOSTS = ("pic-cdn.creality.com", "pic2-cdn.creality.com")

# Same messages as the printer's local websocket; nothing else can be sent.
COMMANDS: dict[str, dict[str, int]] = {
    "pause": {"pause": 1},
    "resume": {"pause": 0},
    "cancel": {"stop": 1},
    "light_on": {"lightSw": 1},
    "light_off": {"lightSw": 0},
}

STATES = {0: "idle", 1: "printing", 2: "finished", 3: "failed", 4: "stopped", 5: "paused"}


# Creality Print / OrcaSlicer name files like "Model.stl_PLA_8h35m17s.gcode" or "Model_PETG_0.2_1h02m3s.gcode"
_JOB = re.compile(r"[._](?P<mat>[A-Z][A-Z0-9+-]{1,9})(?:_(?P<lh>0\.\d+))?_(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?(?:\.gcode)?$")


def parse_job(name: str | None) -> dict[str, Any]:
    """Slicer info from the file name: material, layer height and the slicer's time estimate (seconds)."""
    if not name:
        return {}
    m = _JOB.search(name)
    if not m or not any(m.group(k) for k in "dhms"):
        return {"file_name": name}
    est = sum(int(m.group(k) or 0) * f for k, f in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)))
    out: dict[str, Any] = {"file_name": name, "filament_types": [m.group("mat")], "slicer_estimate": est}
    if m.group("lh"):
        out["layer_height"] = float(m.group("lh"))
    return out


class CrealityError(Exception):
    """Creality Cloud answered with an error."""


class CrealityAuthError(CrealityError):
    """Login failed (wrong e-mail or password)."""


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@dataclass
class Printer:
    """One printer as Home Assistant needs it."""

    id: str
    tb_id: str
    name: str
    model: str
    firmware: str | None
    serial: str | None
    online: bool
    state: str
    job: str | None
    progress: float | None
    remaining: float | None  # seconds
    started: int | None  # unix time
    nozzle: float | None
    nozzle_target: float | None
    bed: float | None
    bed_target: float | None
    chamber: float | None
    light: bool | None
    error: int | None
    thumbnail: str | None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def active(self) -> bool:
        return self.state in ("printing", "paused")


def parse_device(d: dict[str, Any]) -> Printer:
    """Turn one entry of getDeviceList into a Printer (no network; tested with tests/device.json)."""
    a = {x.get("key"): x.get("value") for x in d.get("iotAttr") or []}
    p = d.get("printInfo") or {}
    state = STATES.get(a.get("state"), "unknown")
    active = state in ("printing", "paused")
    thumb = p.get("gcodeThumbnail") or None
    if thumb and not any(thumb.startswith("https://%s/" % h) for h in THUMB_HOSTS):
        thumb = None
    led = a.get("led_state")
    return Printer(
        id=str(d.get("deviceName") or d.get("id")),
        tb_id=str(d.get("tbId") or ""),
        name=d.get("aliasName") or d.get("deviceName") or "Creality printer",
        model=(d.get("deviceType") or {}).get("name") or d.get("model") or "Creality",
        firmware=d.get("printerVersion"),
        serial=d.get("factorySn") or a.get("productionSn"),
        online=d.get("deviceState") == 1 and a.get("connect", d.get("connect")) == 1,
        state=state,
        job=(p.get("modelName") or a.get("print")) if active else None,
        progress=_num(p.get("printProgress")) if active else None,
        remaining=_num(p.get("printLeftTime")) if active else None,
        started=a.get("printStartTime") if active else None,
        nozzle=_num(d.get("nozzleTemp")),
        nozzle_target=_num(a.get("nozzleTemp2")),
        bed=_num(d.get("bedTemp")),
        bed_target=_num(a.get("bedTemp2")),
        chamber=_num(d.get("boxTemp")),
        light=None if led is None else led == 1,
        error=(d.get("deviceErrorCode") or a.get("err") or None),
        thumbnail=thumb if active else None,
        raw=d,
    )


class CrealityCloud:
    """Login, list printers, send a fixed command. Re-logs in when the token expires."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str, token: dict | None = None) -> None:
        self._s = session
        self._email = email
        self._password = password
        self.token: dict | None = token  # {"token": ..., "uid": ...}

    @staticmethod
    def _headers(extra: dict[str, str]) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "__CXY_REQUESTID_": str(uuid.uuid4()),
            "__CXY_OS_LANG_": "0",
            "__CXY_PLATFORM_": "2",
            "__CXY_DUID_": "home-assistant",
            "__CXY_BRAND_": "creality",
            "__CXY_TIMEZONE_": str(time.localtime().tm_gmtoff),
        }
        h.update(extra)
        return h

    async def _post(self, url: str, data: dict, headers: dict) -> dict:
        try:
            async with self._s.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    raise CrealityError("HTTP %d from Creality Cloud" % r.status)
                return await r.json(content_type=None)
        except aiohttp.ClientError as ex:
            raise CrealityError(str(ex)) from ex

    async def login(self) -> dict:
        b = await self._post(
            ID_HOST + LOGIN,
            {"type": 2, "account": self._email, "password": self._password, "clientId": CLIENT_ID},
            self._headers({"__CXY_APP_ID_": "creality_account", "__CXY_APP_VER_": "0.0.1", "__CXY_PLATFORM_": "pc"}),
        )
        res = b.get("result") or {}
        if b.get("code") != 0 or not res.get("token"):
            raise CrealityAuthError(b.get("msg") or "login failed (code %s)" % b.get("code"))
        self.token = {"token": res["token"], "uid": res.get("userId")}
        return self.token

    async def call(self, path: str, data: dict) -> Any:
        for attempt in (0, 1):
            if not self.token or attempt:
                await self.login()
            b = await self._post(
                API_HOST + path,
                data,
                self._headers({"__CXY_APP_ID_": "cxy-gen2", "__CXY_APP_VER_": APP_VER,
                               "__CXY_TOKEN_": self.token["token"], "__CXY_UID_": str(self.token["uid"])}),
            )
            if b.get("code") in (4, 5) and not attempt:
                continue  # token expired
            if b.get("code", 0) != 0:
                raise CrealityError(b.get("msg") or "error code %s" % b.get("code"))
            return b.get("result")
        raise CrealityError("could not log in again")

    async def printers(self) -> dict[str, Printer]:
        res = await self.call(DEVICES, {"page": 1, "pageSize": 50}) or {}
        devices = list(res.get("ungroupedList") or [])
        for g in res.get("groupList") or []:
            devices += g.get("list") or g.get("devices") or []
        out = {}
        for d in devices:
            p = parse_device(d)
            out[p.id] = p
        return out

    async def command(self, printer: Printer, name: str) -> None:
        if name not in COMMANDS:
            raise ValueError("unknown command %s" % name)
        if not printer.tb_id:
            raise CrealityError("printer has no cloud id")
        await self.call(RPC + printer.tb_id, {"method": "set", "params": COMMANDS[name]})
