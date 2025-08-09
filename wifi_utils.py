# wifi_utils.py (macOS-only)
# Robust Wi‑Fi helper for ez Share on macOS: strong verification (SSID/BSSID/subnet/ping),
# resilient SSID detection (networksetup/airport/wdutil/scutil), and optional monitoring.

from __future__ import annotations

import logging
import re
import shlex
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# -----------------
# Small shell util
# -----------------
def _run(cmd, *, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run command with capture and debug logging. Accepts str or list."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    logger.debug("exec: %s", " ".join(cmd))
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        logger.debug(" -> rc=%s; out=%r; err=%r", cp.returncode, cp.stdout, cp.stderr)
        return cp
    except Exception:
        logger.exception("command failed: %s", " ".join(cmd))
        raise


def _norm_ssid(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else None


# -------------
# macOS backend
# -------------
class _MacOS:
    AIRPORT = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    WDUTIL = "/System/Library/PrivateFrameworks/WirelessDiagnostics.framework/Versions/Current/usr/bin/wdutil"

    def __init__(self):
        self.iface = self._find_wifi_iface()

    def _find_wifi_iface(self) -> Optional[str]:
        cp = _run(["networksetup", "-listallhardwareports"])
        dev = None
        current_is_wifi = False
        for line in cp.stdout.splitlines():
            if line.strip().startswith("Hardware Port:"):
                # handles “Wi‑Fi” vs “Wi-Fi”
                current_is_wifi = ("Wi-Fi" in line) or ("Wi‑Fi" in line)
            elif line.strip().startswith("Device:"):
                dev = line.split(":", 1)[1].strip()
                if current_is_wifi and dev:
                    logger.info("macOS Wi‑Fi interface=%s", dev)
                    return dev
        logger.error("macOS: Wi‑Fi interface not found")
        return None

    # ---- Power helpers ----
    def _power_state(self) -> Optional[bool]:
        if not self.iface and not self._find_wifi_iface():
            return None
        cp = _run(["networksetup", "-getairportpower", self.iface])
        # "Wi‑Fi Power (en0): On" / "Off"
        m = re.search(r":\s*(On|Off)\s*$", (cp.stdout or "").strip(), re.I)
        if not m:
            return None
        return m.group(1).lower() == "on"

    def _ensure_power_on(self):
        st = self._power_state()
        if st is False:
            _run(["networksetup", "-setairportpower", self.iface, "on"])
            time.sleep(1.0)  # allow radio to come up

    # ---- Connect / Disconnect ----
    def connect(self, ssid: str, psk: Optional[str]) -> bool:
        if not self.iface and not self._find_wifi_iface():
            return False
        self._ensure_power_on()
        cmd = ["networksetup", "-setairportnetwork", self.iface, ssid]
        if psk:
            cmd.append(psk)
        cp = _run(cmd)
        time.sleep(2.5)  # settle association
        return cp.returncode == 0

    def disconnect(self) -> bool:
        if not self.iface and not self._find_wifi_iface():
            return False
        ok = True
        for state in ("off", "on"):  # quick toggle is most reliable
            cp = _run(["networksetup", "-setairportpower", self.iface, state])
            ok = ok and (cp.returncode == 0)
            time.sleep(0.8)
        return ok

    # ---- State queries ----
    def current_ssid_bssid(self) -> Tuple[Optional[str], Optional[str]]:
        """Try multiple sources; airport can be grumpy while radio is coming up."""
        self._ensure_power_on()

        ssid: Optional[str] = None
        bssid: Optional[str] = None

        # 1) networksetup (fast path for SSID)
        cp = _run(["networksetup", "-getairportnetwork", self.iface or "en0"])
        out = (cp.stdout or "").strip()
        m = re.search(r"Current Wi-?Fi Network:\s*(.*)$", out)
        if m:
            ssid = _norm_ssid(m.group(1))

        # 2) airport -I (SSID + BSSID) — may print deprecation only if not ready
        cp2 = _run([self.AIRPORT, "-I"])
        m_ssid = re.search(r"^\s*SSID:\s*(.+)\s*$", cp2.stdout or "", re.M)
        if m_ssid:
            ssid = ssid or _norm_ssid(m_ssid.group(1))
        m_bssid = re.search(r"^\s*BSSID:\s*([0-9A-Fa-f:]{17})\s*$", cp2.stdout or "", re.M)
        if m_bssid:
            bssid = (m_bssid.group(1) or "").lower()

        # 3) wdutil info (Ventura/Sonoma+)
        if not ssid and shutil.which(self.WDUTIL):
            cp3 = _run([self.WDUTIL, "info"])
            m3 = re.search(r"^\s*SSID:\s*(.+)\s*$", cp3.stdout or "", re.M)
            if m3:
                ssid = _norm_ssid(m3.group(1))

        # 4) scutil --nwi
        if not ssid:
            cp4 = _run(["scutil", "--nwi"])
            m4 = re.search(r"SSID:\s*(.+)", cp4.stdout or "")
            if m4:
                ssid = _norm_ssid(m4.group(1))

        return ssid or None, bssid or None

    def on_expected_subnet(self, subnet_prefix: str) -> bool:
        self._ensure_power_on()
        cp = _run(["ipconfig", "getifaddr", self.iface or "en0"])
        ip = (cp.stdout or "").strip()
        return ip.startswith(subnet_prefix)

    def ping(self, ip: str, count: int = 2, timeout_s: int = 4) -> bool:
        cp = _run(["ping", "-c", str(count), "-W", str(timeout_s), ip], timeout=timeout_s + 2)
        return cp.returncode == 0


# --------------
# Public facade
# --------------
@dataclass
class VerifySpec:
    expected_ssid: Optional[str] = None
    expected_bssid: Optional[str] = None  # optional extra guard
    expected_subnet_prefix: str = "192.168.4."
    gateway_ip: str = "192.168.4.1"


class ConnectionManager:
    """
    Low-level connection primitive with strong verification.
    Thread-safe; only sets `connected=True` after verify() passes.
    macOS only.
    """
    def __init__(self):
        self._os = _MacOS()
        self._lock = threading.Lock()
        self.connected: bool = False

    # convenience getter
    def current_ssid_bssid(self) -> Tuple[Optional[str], Optional[str]]:
        return self._os.current_ssid_bssid()

    # connect / disconnect
    def connect(self, ssid: str, psk: Optional[str]) -> bool:
        with self._lock:
            logger.info("Connecting to SSID=%r", ssid)
            ok = self._os.connect(ssid, psk)
            if not ok:
                logger.warning("Association command failed.")
            return ok

    def disconnect(self) -> bool:
        with self._lock:
            logger.info("Disconnecting (toggle/reset).")
            ok = self._os.disconnect()
            self.connected = False
            return ok

    # verification
    def verify(
        self,
        spec: VerifySpec,
        *,
        max_attempts: int = 10,
        settle_delay: float = 1.3,   # Sonoma can be slow to report SSID
        ping_count: int = 2,
        ping_timeout_s: int = 4,
    ) -> bool:
        """
        Prove we're on expected SSID/BSSID, on expected subnet, and can ping the gateway.
        If SSID is temporarily unreadable, accept subnet+ping success (warn once).
        """
        for attempt in range(1, max_attempts + 1):
            time.sleep(settle_delay)

            ssid, bssid = self._os.current_ssid_bssid()

            # SSID/BSSID checks
            ssid_expected = _norm_ssid(spec.expected_ssid)
            ssid_actual = _norm_ssid(ssid)
            ssid_ok = True if ssid_expected is None else (ssid_actual == ssid_expected)

            bssid_ok = True
            if spec.expected_bssid:
                bssid_ok = ((bssid or "").lower() == spec.expected_bssid.lower())

            subnet_ok = self._os.on_expected_subnet(spec.expected_subnet_prefix)
            ping_ok = self._os.ping(spec.gateway_ip, count=ping_count, timeout_s=ping_timeout_s)

            # Accept when all good OR SSID unreadable but subnet+ping prove it's the card.
            if (ssid_ok and bssid_ok and subnet_ok and ping_ok) or (ssid_actual is None and subnet_ok and ping_ok):
                if ssid_actual is None and ssid_expected:
                    logger.warning("SSID unavailable on verify[%d/%d], but subnet+ping OK; accepting.",
                                   attempt, max_attempts)
                self.connected = True
                logger.info("Wi‑Fi verified.")
                return True

            # Log reasons
            if ssid_expected and not ssid_ok:
                logger.warning("verify[%d/%d]: wrong SSID: got %r want %r",
                               attempt, max_attempts, ssid_actual, ssid_expected)
            if spec.expected_bssid and not bssid_ok:
                logger.warning("verify[%d/%d]: wrong BSSID: got %r want %r",
                               attempt, max_attempts, bssid, spec.expected_bssid)
            if not subnet_ok:
                logger.warning("verify[%d/%d]: not on subnet %s",
                               attempt, max_attempts, spec.expected_subnet_prefix)
            if not ping_ok:
                logger.warning("verify[%d/%d]: ping %s failed",
                               attempt, max_attempts, spec.gateway_ip)

        logger.error("Wi‑Fi verification failed after %d attempts.", max_attempts)
        self.connected = False
        return False

    # combined flow
    def connect_and_verify(
        self,
        ssid: str,
        psk: Optional[str],
        spec: Optional[VerifySpec] = None,
        *,
        connect_attempts: int = 3,
        verify_attempts: int = 10,
        retry_delay: float = 2.0,
    ) -> bool:
        spec = spec or VerifySpec(expected_ssid=ssid)
        for i in range(1, connect_attempts + 1):
            if not self.connect(ssid, psk):
                logger.info("connect attempt %d/%d failed; retrying…", i, connect_attempts)
                time.sleep(retry_delay)
                continue
            if self.verify(spec, max_attempts=verify_attempts):
                return True
            logger.info("verify failed on attempt %d/%d; resetting interface…", i, connect_attempts)
            self.disconnect()
            time.sleep(retry_delay)
        return False


class WiFiManager:
    """
    High-level, app-friendly API for macOS.
    Optional background monitor keeps you verified and auto-reconnects if the OS roams.
    """
    def __init__(self):
        self.conn = ConnectionManager()
        self._mon_thread: Optional[threading.Thread] = None
        self._mon_stop = threading.Event()

    def ensure_connected(self, ssid: str, psk: Optional[str], verify: Optional[VerifySpec] = None) -> bool:
        verify = verify or VerifySpec(expected_ssid=ssid)
        # quick short-circuit if already valid
        if self.conn.verify(verify, max_attempts=1):
            return True
        return self.conn.connect_and_verify(ssid, psk, verify)

    def disconnect(self) -> bool:
        self.stop_monitor()
        return self.conn.disconnect()

    @property
    def connected(self) -> bool:
        return self.conn.connected

    # Background monitor
    def start_monitor(self, ssid: str, psk: Optional[str], verify: Optional[VerifySpec] = None, *, interval_s: float = 3.0):
        self.stop_monitor()
        verify = verify or VerifySpec(expected_ssid=ssid)
        self._mon_stop.clear()

        def _loop():
            logger.info("Wi‑Fi monitor started.")
            while not self._mon_stop.is_set():
                try:
                    if not self.conn.verify(verify, max_attempts=1):
                        logger.warning("Monitor: Wi‑Fi no longer valid; reconnecting…")
                        self.conn.connect_and_verify(ssid, psk, verify, connect_attempts=2, verify_attempts=5)
                except Exception:
                    logger.exception("Monitor loop error")
                finally:
                    self._mon_stop.wait(interval_s)
            logger.info("Wi‑Fi monitor stopped.")

        self._mon_thread = threading.Thread(target=_loop, name="WiFiMonitor", daemon=True)
        self._mon_thread.start()

    def stop_monitor(self):
        if self._mon_thread and self._mon_thread.is_alive():
            self._mon_stop.set()
            self._mon_thread.join(timeout=5)
        self._mon_thread = None
        self._mon_stop.clear()
