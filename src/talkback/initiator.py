# src/talkback/initiator.py
"""
Low-level RTSP back-channel (talk-back) initiator.

Public API
----------
* __init__(rtsp_url, client_port=None, verbose=False)
* start()                  -> (camera_ip, back_channel_port)
* keep_alive()             -> bool
* terminate()              -> graceful TEARDOWN
"""

from __future__ import annotations

import hashlib
import re
import socket
from typing import Tuple

from .exceptions import RTSPAuthError, RTSPHandshakeError
from .settings   import settings
from .utils      import RTSPUrlParts, get_logger, parse_rtsp_url


class TalkBackInitiator:
    """Blocking implementation of the ONVIF talk-back handshake."""

    def __init__(
        self,
        rtsp_url: str,
        *,
        client_port: int | None = None,
        verbose: bool = False,
    ) -> None:
        self._url: RTSPUrlParts = parse_rtsp_url(rtsp_url)
        self._client_port: int = client_port or settings.default_client_port
        self._rtsp_timeout: int = settings.rtsp_timeout

        # if verbose=True, bump logger to DEBUG; otherwise INFO is default
        self._logger = get_logger(level="DEBUG" if verbose else None)

        # handshake state
        self._sock: socket.socket | None = None
        self._session_id: str | None     = None
        self._realm: str | None          = None
        self._nonce: str | None          = None
        self._uri_base: str | None       = None
        self._back_channel_port: int | None = None
        self._cseq: int                  = 5  # next CSeq after PLAY

    # ─────────────── Public API ────────────────────────────────────────────
    def start(self) -> Tuple[str, int]:
        """
        Perform the RTSP handshake up to PLAY.
        Returns (camera_ip, back_channel_port).
        """
        try:
            self._do_rtsp_handshake()
            self._logger.info(f"Talk-back session started: {self._url.host}:{self._back_channel_port}")
            return self._url.host, self._back_channel_port  # type: ignore[arg-type]
        except Exception:
            self.terminate()
            raise

    def keep_alive(self) -> bool:
        """Send an OPTIONS keep-alive. Returns True if 200 OK."""
        if not self._sock or not self._uri_base:
            self._logger.warning("Keep-alive requested but no active session")
            return False
        self._cseq += 1
        ok = self._send_simple(
            method="OPTIONS",
            uri=self._uri_base,
            cseq=self._cseq,
            session=self._session_id,
        )
        if ok:
            self._logger.info(f"OPTIONS keep-alive successful (CSeq={self._cseq})")
        else:
            self._logger.warning(f"OPTIONS keep-alive failed (CSeq={self._cseq})")
        return ok

    def terminate(self) -> None:
        """Send TEARDOWN (best-effort) and close the socket."""
        if not self._sock or not self._uri_base:
            return
        try:
            self._send_simple(
                method="TEARDOWN",
                uri=self._uri_base,
                cseq=self._cseq + 1,
                session=self._session_id,
                raise_on_error=False,
            )
            self._logger.info(f"Sent TEARDOWN (CSeq={self._cseq + 1})")
        except Exception as e:
            self._logger.warning(f"TEARDOWN error: {e}")
        finally:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._logger.info("RTSP talk-back session terminated")

    # ─────────────── Internal helpers ──────────────────────────────────────
    def _build_authorization(self, method: str, uri: str) -> str:
        if self._url.username is None or self._url.password is None:
            raise RTSPAuthError("No credentials for digest auth")
        assert self._realm and self._nonce
        ha1 = hashlib.md5(
            f"{self._url.username}:{self._realm}:{self._url.password}".encode()
        ).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        resp = hashlib.md5(f"{ha1}:{self._nonce}:{ha2}".encode()).hexdigest()
        return (
            f'Digest username="{self._url.username}", realm="{self._realm}", '
            f'nonce="{self._nonce}", uri="{uri}", response="{resp}"'
        )

    def _log_request(self, req: str) -> None:
        first = req.splitlines()[0]
        self._logger.debug(f"-> {first}")
        self._logger.debug(req.rstrip())

    def _log_response(self, resp: str) -> None:
        first = resp.splitlines()[0] if resp else "EMPTY RESPONSE"
        self._logger.debug(f"<- {first}")
        self._logger.debug(resp.rstrip())

    def _send(self, request: str) -> str:
        if not self._sock:
            raise RTSPHandshakeError("Socket is not open")
        self._log_request(request)
        self._sock.sendall(request.encode())
        response = self._sock.recv(8192).decode(errors="replace")
        self._log_response(response)
        return response

    def _send_simple(
        self,
        *,
        method: str,
        uri: str,
        cseq: int,
        session: str | None,
        raise_on_error: bool = True,
    ) -> bool:
        auth = self._build_authorization(method, uri)
        req = (
            f"{method} {uri} RTSP/1.0\r\n"
            f"CSeq: {cseq}\r\n"
            f"Authorization: {auth}\r\n"
        )
        if session:
            req += f"Session: {session}\r\n"
        req += "\r\n"

        resp = self._send(req)
        ok = resp.startswith("RTSP/1.0 200")
        if ok:
            self._logger.debug(f"{method} OK (CSeq={cseq})")
        if not ok and raise_on_error:
            raise RTSPHandshakeError(f"{method} failed: {resp.splitlines()[0]}")
        return ok

    # ───────── Handshake steps ─────────────────────────────────────────────
    def _do_rtsp_handshake(self) -> None:
        self._uri_base = f"rtsp://{self._url.host}:{self._url.port}/{self._url.path}"

        # TCP connect
        self._sock = socket.create_connection(
            (self._url.host, self._url.port), timeout=self._rtsp_timeout
        )
        self._logger.info(f"Connected to {self._url.host}:{self._url.port}")

        # 1) DESCRIBE (unauthenticated)
        resp1 = self._send(
            f"DESCRIBE {self._uri_base} RTSP/1.0\r\n"
            "CSeq: 1\r\n"
            "Accept: application/sdp\r\n"
            "Require: www.onvif.org/ver20/backchannel\r\n\r\n"
        )

        # 2) Digest challenge
        m = re.search(
            r'WWW-Authenticate:\s*Digest realm="([^"]+)",\s*nonce="([^"]+)"', resp1
        )
        if not m:
            raise RTSPAuthError("Digest challenge not received from camera")
        self._realm, self._nonce = m.groups()
        self._logger.info(f"Received digest challenge (realm={self._realm})")

        # 3) Authenticated DESCRIBE
        auth_header = self._build_authorization("DESCRIBE", self._uri_base)
        resp2 = self._send(
            f"DESCRIBE {self._uri_base} RTSP/1.0\r\n"
            "CSeq: 2\r\n"
            "Accept: application/sdp\r\n"
            "Require: www.onvif.org/ver20/backchannel\r\n"
            f"Authorization: {auth_header}\r\n\r\n"
        )
        self._logger.info("Authenticated DESCRIBE succeeded")

        # 4) Content-Base
        cb_match = re.search(r"Content-Base:\s*(\S+)", resp2)
        if not cb_match:
            raise RTSPHandshakeError("Content-Base header missing")
        content_base = cb_match.group(1).rstrip("/") + "/"
        self._logger.info(f"Extracted Content-Base: {content_base}")

        # 5) Find sendonly track
        sdp = resp2.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in resp2 else ""
        talk_control: str | None = None
        for section in sdp.split("m="):
            if "a=sendonly" in section:
                m2 = re.search(r"a=control:(.*)", section)
                if m2:
                    talk_control = m2.group(1).strip()
                    break
        if not talk_control:
            raise RTSPHandshakeError("No talk-back (a=sendonly) track found")
        self._logger.info(f"Found talk-back control track: {talk_control}")
        talk_url = content_base + talk_control

        # 6) SETUP
        setup_resp = self._send(
            f"SETUP {talk_url} RTSP/1.0\r\n"
            "CSeq: 3\r\n"
            f"Transport: RTP/AVP;unicast;"
            f"client_port={self._client_port}-{self._client_port + 1}\r\n"
            f"Authorization: {self._build_authorization('SETUP', talk_url)}\r\n\r\n"
        )

        sess = re.search(r"Session:\s*([^;\s]+)", setup_resp)
        if not sess:
            raise RTSPHandshakeError("Session header missing in SETUP")
        self._session_id = sess.group(1)
        self._logger.info(f"Session established: {self._session_id}")

        sp = re.search(r"server_port=(\d+)-(\d+)", setup_resp)
        if not sp:
            raise RTSPHandshakeError("server_port missing in SETUP")
        self._back_channel_port = int(sp.group(1))
        self._logger.info(f"Camera back-channel port: {self._back_channel_port}")

        # 7) PLAY
        self._cseq = 4
        if self._send_simple(
            method="PLAY",
            uri=self._uri_base,
            cseq=self._cseq,
            session=self._session_id,
        ):
            self._logger.info(f"PLAY succeeded (CSeq={self._cseq})")
        else:
            raise RTSPHandshakeError("PLAY failed")
