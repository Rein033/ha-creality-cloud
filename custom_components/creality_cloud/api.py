"""Small async client for Creality Cloud (crealitycloud.com and crealitycloud.cn).

Creality does not publish an API for this. The endpoints below come from the Creality Cloud website and may change
without notice.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import aiohttp

APP_VER = "7.3.28"

# region -> hosts and the website's client id
REGIONS: dict[str, dict[str, str]] = {
    "international": {"id": "https://id.creality.com", "api": "https://api.crealitycloud.com",
                      "client_id": "f9c302ecc29c59a0a6e921ff39a073ca"},
    "china": {"id": "https://id.creality.cn", "api": "https://api.crealitycloud.cn",
              "client_id": "8ea5010984fa52a298f12110af8b05d0"},
}

LOGIN = "/api/cxy/account/v2/loginV2"
DEVICES = "/api/rest/print/cluster/devices/getDeviceList"
RPC = "/api/rest/iotrouter/rpc/twoway/"
HISTORY = "/api/cxy/v3/print/record/list"
TIMELAPSES = "/api/cxy/v2/device/timelapsVideoList"
OTA = "/api/cxy/v2/firmware/otaList"

# images and videos are only taken from Creality's own CDNs
MEDIA_DOMAINS = ("creality.com", "crealitycloud.com", "creality.cn", "crealitycloud.cn")

# Same messages as the printer's local websocket; nothing else can be sent.
COMMANDS: dict[str, dict[str, int]] = {
    "pause": {"pause": 1},
    "resume": {"pause": 0},
    "cancel": {"stop": 1},
    "light_on": {"lightSw": 1},
    "light_off": {"lightSw": 0},
}
GCODE_DIR = "/usr/data/printer_data/gcodes/"   # where K1-series printers keep files on their own storage

STATES = {0: "idle", 1: "printing", 2: "finished", 3: "failed", 4: "stopped", 5: "paused"}
# printState in the print history
RECORD_STATES = {0: "waiting", 1: "printing", 2: "finished", 3: "failed", 4: "stopped", 5: "paused"}


# Creality Print / OrcaSlicer name files like "Model.stl_PLA_8h35m17s.gcode" or "Model_PETG_0.2_1h02m3s.gcode"
_JOB = re.compile(r"[._](?P<mat>[A-Z][A-Z0-9+-]{1,9})(?:_(?P<lh>0\.\d+))?_(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?(?:\.gcode)?$")
_SAFE_FILE = re.compile(r"^[^/\\\x00-\x1f]{1,200}\.gcode$", re.IGNORECASE)


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


def media_url(url: Any) -> str | None:
    """Only https URLs on Creality's own domains."""
    if not isinstance(url, str):
        return None
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme == "https" and any(host == d or host.endswith("." + d) for d in MEDIA_DOMAINS):
        return url
    return None


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
    hardware: str | None
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
    estimated: bool = False   # progress/remaining worked out from the slicer time in the file name (Creality sent nothing)

    @property
    def active(self) -> bool:
        return self.state in ("printing", "paused")


@dataclass
class PrintRecord:
    """One entry of the print history."""

    id: str
    name: str
    state: str
    start: int | None
    end: int | None
    duration: int | None  # seconds
    thumbnail: str | None
    on_printer: bool  # file is on the printer's own storage, so it can be printed again
    timelapse_id: str | None
    timelapse: str | None = None  # video URL, filled in from the timelapse list
    timelapse_cover: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ("id", "name", "state", "start", "end", "duration", "thumbnail",
                                              "on_printer", "timelapse", "timelapse_cover")}


def slicer_seconds(job: str | None) -> int | None:
    """Print time that slicers put in the file name, e.g. 'Skull_PLA_8h37m58s.gcode' -> 31078 (also '2d3h', '45m12s')."""
    m = re.search(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m(?!m))?(?:(\d+)s)?\.(?:gcode|3mf|bgcode)", str(job or ""), re.I)
    if not m or not any(m.groups()):
        return None
    d, h, mi, se = (int(x or 0) for x in m.groups())
    total = ((d * 24 + h) * 60 + mi) * 60 + se
    return total or None


def estimate(started: int | None, job: str | None, now: float | None = None) -> tuple[float, float] | None:
    """(progress %, remaining seconds) from the start time and the slicer time; None when we cannot tell."""
    total = slicer_seconds(job)
    if not started or not total:
        return None
    elapsed = max(0.0, (now if now is not None else time.time()) - started)
    return round(min(99.0, elapsed / total * 100), 1), max(0.0, total - elapsed)


def parse_device(d: dict[str, Any]) -> Printer:
    """Turn one entry of getDeviceList into a Printer (no network; tested with tests/device.json)."""
    a = {x.get("key"): x.get("value") for x in d.get("iotAttr") or []}
    p = d.get("printInfo") or {}
    state = STATES.get(a.get("state"), "unknown")
    active = state in ("printing", "paused")
    led = a.get("led_state")
    hw = re.search(r"printer hw ver:([^;]+)", str(a.get("modelVersion") or ""))
    printer = Printer(
        id=str(d.get("deviceName") or d.get("id")),
        tb_id=str(d.get("tbId") or ""),
        name=d.get("aliasName") or d.get("deviceName") or "Creality printer",
        model=(d.get("deviceType") or {}).get("name") or d.get("model") or "Creality",
        firmware=d.get("printerVersion"),
        hardware=hw.group(1).strip() if hw else None,
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
        thumbnail=media_url(p.get("gcodeThumbnail")) if active else None,
        raw=d,
    )
    # Creality sometimes sends no printInfo at all (no progress, no time left): estimate from the slicer time in the name
    if printer.state == "printing" and printer.progress is None and printer.remaining is None:
        est = estimate(printer.started, printer.job)
        if est:
            printer.progress, printer.remaining = est
            printer.estimated = True
    return printer


def parse_record(r: dict[str, Any]) -> PrintRecord:
    start, end = r.get("printStartTime") or None, r.get("printEndTime") or None
    job = r.get("printJobTime") or None
    return PrintRecord(
        id=str(r.get("id") or ""),
        name=str(r.get("name") or ""),
        state=RECORD_STATES.get(r.get("printState"), "unknown"),
        start=start,
        end=end,
        duration=job or (end - start if start and end and end > start else None),
        thumbnail=media_url(r.get("thumbnailUrl")),
        on_printer=bool(r.get("tfCard")),
        timelapse_id=str(r.get("timelapseId") or r.get("videoRecordId") or "") or None,
    )


def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def attach_timelapses(records: list[PrintRecord], videos: list[dict[str, Any]]) -> None:
    """Link timelapse videos to history entries by timelapse id, record id or print id."""
    by_key: dict[str, dict] = {}
    for v in videos:
        for k in ("id", "timelapseId", "videoRecordId", "printId", "recordId"):
            if v.get(k):
                by_key[str(v[k])] = v
    for r in records:
        v = by_key.get(r.timelapse_id or "") or by_key.get(r.id)
        if v:
            r.timelapse = media_url(_first(v, "videoUrl", "url", "playUrl", "fileUrl", "video"))
            r.timelapse_cover = media_url(_first(v, "coverUrl", "cover", "thumbnail", "coverImg"))


def latest_firmware(ota: list[dict[str, Any]], hardware: str | None) -> str | None:
    """Highest otaVer released for this hardware version."""
    if not hardware:
        return None
    def key(v: str) -> tuple:
        return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", v))
    vers = [str(o.get("otaVer")) for o in ota if o.get("hardwareVer") == hardware and o.get("otaVer")]
    return max(vers, key=key) if vers else None


def reprint_params(file_name: str) -> dict[str, str]:
    """The command that starts a file from the printer's own storage. Only plain .gcode file names."""
    if not _SAFE_FILE.match(file_name or ""):
        raise ValueError("not a printable file name")
    return {"opGcodeFile": "printprt:" + GCODE_DIR + file_name}


class CrealityCloud:
    """Login, printers, history, timelapses, firmware and a fixed set of commands. Re-logs in when the token expires."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str, token: dict | None = None,
                 region: str = "international") -> None:
        self._s = session
        self._email = email
        self._password = password
        self.token: dict | None = token  # {"token": ..., "uid": ...}
        self.region = REGIONS.get(region, REGIONS["international"])

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
        account = self._email.strip()
        kind = 2 if "@" in account else 1   # 1 = phone number (China region), 2 = e-mail
        b = await self._post(
            self.region["id"] + LOGIN,
            {"type": kind, "account": account, "password": self._password, "clientId": self.region["client_id"]},
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
                self.region["api"] + path,
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

    async def history(self, printer: Printer, size: int = 10) -> list[PrintRecord]:
        res = await self.call(HISTORY, {"page": 1, "pageSize": size, "deviceName": printer.raw.get("deviceName") or printer.id}) or {}
        records = [parse_record(r) for r in res.get("list") or []]
        if any(r.timelapse_id for r in records):
            vids = await self.call(TIMELAPSES, {"page": 1, "pageSize": 30}) or {}
            attach_timelapses(records, vids.get("list") or [])
        return records

    async def latest_firmware(self, hardware: str | None, pages: int = 6) -> str | None:
        found: list[dict] = []
        for page in range(1, pages + 1):
            res = await self.call(OTA, {"page": page, "pageSize": 50}) or {}
            items = res.get("list") or []
            found += items
            if latest_firmware(items, hardware) or len(items) < 50:
                break
        return latest_firmware(found, hardware)

    async def command(self, printer: Printer, name: str) -> None:
        if name not in COMMANDS:
            raise ValueError("unknown command %s" % name)
        await self._rpc(printer, COMMANDS[name])

    async def reprint(self, printer: Printer, file_name: str) -> None:
        """Print a file again from the printer's own storage. Refused while the printer is busy or offline."""
        params = reprint_params(file_name)
        if not printer.online or printer.active:
            raise CrealityError("the printer must be online and idle to start a print")
        await self._rpc(printer, params)

    async def _rpc(self, printer: Printer, params: dict) -> None:
        if not printer.tb_id:
            raise CrealityError("printer has no cloud id")
        await self.call(RPC + printer.tb_id, {"method": "set", "params": params})
