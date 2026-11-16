"""Authenticated client for Zexa's opt-in Android Accessibility Bridge.

The Android companion service is a separate app and must be installed and
enabled by the device owner. This module never launches adb, shell commands,
or arbitrary URLs. Exact-action requests require a caller-supplied approval
callback; bounded navigation requests must match a task grant explicitly created
and approved in the Android app. Screen reads are read-only.
"""
from __future__ import annotations

import json
import re
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ALLOWED_ACTIONS = {"tap", "swipe", "scroll", "back", "home", "input_text", "launch_app", "open_url"}
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}")
_TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_GRANTABLE_ACTIONS = {"swipe", "scroll", "back", "home", "launch_app"}


class AccessibilityBridge:
    def __init__(
        self,
        token: str,
        base_url: str = "http://127.0.0.1:8765",
        timeout: int = 8,
    ) -> None:
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~-]{16,256}", token):
            raise ValueError("Bridge token must be 16–256 URL-safe characters.")
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Accessibility bridge must use local HTTP loopback only.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Bridge URL must not contain credentials, query, or fragment.")
        if parsed.port != 8765 or parsed.path not in {"", "/"}:
            raise ValueError("Bridge URL must use port 8765 and have no path.")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1, min(int(timeout), 20))

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method,
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(256_001)
                if len(raw) > 256_000:
                    raise RuntimeError("Accessibility bridge response exceeded the size limit.")
                result = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 403:
                raise PermissionError("Accessibility bridge denied this request or its permission scope.") from exc
            raise RuntimeError(f"Accessibility bridge returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Accessibility bridge is not reachable on this device.") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("Accessibility bridge returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Accessibility bridge response must be a JSON object.")
        return result

    def status(self) -> dict:
        """Read bridge status; does not perform a device action."""
        return self._request("GET", "/v1/status")

    def screen(self) -> dict:
        """Read the current UI accessibility snapshot."""
        return self._request("GET", "/v1/screen")

    def task_grants(self) -> list[dict]:
        """List active bounded grants created and approved in the Android app."""
        result = self._request("GET", "/v1/grants")
        grants = result.get("grants")
        if result.get("ok") is not True or not isinstance(grants, list):
            raise RuntimeError("Android bridge returned an invalid task-grant list.")
        for item in grants:
            if not isinstance(item, dict) or set(item) != {
                "grant_id", "task_id", "allowed_actions", "expires_at_epoch_ms", "remaining_actions"
            }:
                raise RuntimeError("Android bridge returned an invalid task-grant entry.")
            if (
                not isinstance(item["grant_id"], str)
                or not _REQUEST_ID_PATTERN.fullmatch(item["grant_id"])
                or not isinstance(item["task_id"], str)
                or not _TASK_ID_PATTERN.fullmatch(item["task_id"])
                or not isinstance(item["allowed_actions"], list)
                or not item["allowed_actions"]
                or any(action not in _GRANTABLE_ACTIONS for action in item["allowed_actions"])
                or type(item["expires_at_epoch_ms"]) is not int
                or item["expires_at_epoch_ms"] < 0
                or type(item["remaining_actions"]) is not int
                or not 1 <= item["remaining_actions"] <= 30
            ):
                raise RuntimeError("Android bridge returned an invalid task-grant entry.")
        return grants

    def revoke_task_grant(self, grant_id: str) -> bool:
        """Revoke one active bounded task grant on this device."""
        if not isinstance(grant_id, str) or not _REQUEST_ID_PATTERN.fullmatch(grant_id):
            raise ValueError("Task grant ID is invalid.")
        result = self._request("POST", "/v1/grants/revoke", {"grant_id": grant_id})
        if result.get("grant_id") != grant_id or result.get("status") not in {"revoked", "not_found"}:
            raise RuntimeError("Android bridge returned an invalid task-grant revocation result.")
        if result.get("ok") is not (result.get("status") == "revoked"):
            raise RuntimeError("Android bridge returned an inconsistent task-grant revocation result.")
        return result["status"] == "revoked"

    def perform_granted(
        self,
        action: str,
        payload: dict,
        task_id: str,
        grant_id: str,
    ) -> dict:
        """Execute one eligible navigation action inside a previously approved native task grant."""
        if action not in _GRANTABLE_ACTIONS:
            raise ValueError("Action is not eligible for a bounded task grant.")
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be an object.")
        if not isinstance(task_id, str) or not _TASK_ID_PATTERN.fullmatch(task_id):
            raise ValueError("Task ID is invalid.")
        if not isinstance(grant_id, str) or not _REQUEST_ID_PATTERN.fullmatch(grant_id):
            raise ValueError("Task grant ID is invalid.")
        result = self._request("POST", "/v1/action", {
            "action": action,
            "payload": payload,
            "task_id": task_id,
            "grant_id": grant_id,
        })
        if result.get("status") in {"grant_scope_mismatch_or_expired", "grant_unavailable"}:
            raise PermissionError("Task grant is expired, revoked, or outside its approved scope.")
        if result.get("status") == "execution_unknown":
            raise TimeoutError("Android action may have started, but its result is unknown. Do not retry automatically; inspect the device first.")
        if result.get("status") not in {"completed", "dispatched"} or result.get("ok") is not True:
            raise RuntimeError("Android bridge did not confirm successful granted action execution.")
        if result.get("grant_id") != grant_id:
            raise RuntimeError("Android bridge returned a result for a different task grant.")
        return result

    def perform(
        self,
        action: str,
        payload: dict,
        approve: Callable[[str, dict], bool] | None = None,
    ) -> dict:
        """Queue one allowlisted action and require exact native approval before success."""
        if action not in _ALLOWED_ACTIONS:
            raise ValueError("Action is not allowlisted.")
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be an object.")
        if approve is None or approve(action, dict(payload)) is not True:
            raise PermissionError("Android action was not explicitly approved.")

        queued = self._request("POST", "/v1/action", {"action": action, "payload": payload})
        if queued.get("status") != "pending_approval" or queued.get("ok") is not True:
            # A successful action must never be accepted directly from the
            # enqueue response: the native app's separate approval screen is
            # the authority for executing device actions.
            raise RuntimeError("Android bridge did not create a valid native approval request.")

        request_id = queued.get("request_id")
        if not isinstance(request_id, str) or not _REQUEST_ID_PATTERN.fullmatch(request_id):
            raise RuntimeError("Android bridge returned an invalid approval request ID.")

        # The Android app must be open and the user must approve the exact
        # action and payload there. This client-side callback is an additional
        # gate, not a substitute for native confirmation.
        deadline = time.monotonic() + 65.0
        while time.monotonic() < deadline:
            result = self._request("GET", "/v1/action/" + request_id)
            status = result.get("status")
            if result.get("request_id") != request_id:
                raise RuntimeError("Android bridge returned a result for a different approval request.")
            if status in {"completed", "dispatched"}:
                if result.get("ok") is not True:
                    raise RuntimeError("Android bridge reported an action result without confirming success.")
                return result
            if status == "denied":
                raise PermissionError("Android user denied the device action.")
            if status == "expired_or_unknown":
                raise TimeoutError("Android action approval expired or is no longer available.")
            if status == "execution_unknown":
                raise TimeoutError("Android action may have started, but its result is unknown. Do not retry automatically; inspect the device first.")
            if status == "failed":
                raise RuntimeError("Android device action failed; no success was reported.")
            if status not in {"pending_approval", "executing"} or result.get("ok") is not True:
                raise RuntimeError("Android bridge returned an invalid approval status.")
            time.sleep(0.5)
        raise TimeoutError("Timed out waiting for native Android action approval.")
