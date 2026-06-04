"""Cliente HTTP para o backend do OpenTracy.

Usa httpx com timeout, retry limitado e tratamento de erros.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx


class OpenTracyError(Exception):
    """Erro na comunicacao com o OpenTracy."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenTracyClient:
    """Cliente HTTP para o backend do OpenTracy.

    Nao gerencia token automaticamente — o chamador fornece via `auth_token`.
    """

    def __init__(
        self,
        backend_url: str,
        runtime_url: str,
        agent_id: str,
        timeout: int = 30,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.runtime_url = runtime_url.rstrip("/")
        self.agent_id = agent_id
        self.timeout = timeout
        self._client = httpx.Client(timeout=httpx.Timeout(timeout))

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    def check_backend_health(self) -> bool:
        """Verifica se o backend esta respondendo."""
        try:
            r = self._client.get(f"{self.backend_url}/health")
            return r.is_success
        except httpx.RequestError:
            return False

    def check_runtime_health(self) -> bool:
        """Verifica se o runtime esta respondendo."""
        try:
            r = self._client.get(f"{self.runtime_url}/health")
            return r.is_success
        except httpx.RequestError:
            return False

    # ------------------------------------------------------------------
    # Agentes
    # ------------------------------------------------------------------

    def list_agents(self, auth_token: str) -> list[dict[str, Any]]:
        """Lista agentes registrados."""
        r = self._get(
            f"{self.backend_url}/v1/agents",
            auth_token,
        )
        if r.status_code == 404:
            return []
        _raise_for_status(r)
        data = r.json()
        if isinstance(data, dict):
            return data.get("agents", [])
        if isinstance(data, list):
            return data
        return []

    def get_agent_channel_api(self, auth_token: str) -> Optional[dict[str, Any]]:
        """Retorna status do canal API do agente."""
        r = self._get(
            f"{self.backend_url}/v1/agents/{self.agent_id}/channels/api",
            auth_token,
        )
        if r.status_code in (401, 403, 404):
            return None
        _raise_for_status(r)
        return r.json()

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(
        self,
        request: str,
        history: Optional[list[dict[str, str]]] = None,
        *,
        auth_token: str,
        channel: str = "terminal",
    ) -> dict[str, Any]:
        """Envia mensagem para o agente e retorna a resposta.

        Retorna dict com chaves: response, trace_id, duration_ms, success, error.
        """
        payload: dict[str, Any] = {
            "request": request,
            "channel": channel,
        }
        if history:
            payload["history"] = history

        url = f"{self.backend_url}/v1/api/{self.agent_id}/chat"
        r = self._post(url, payload, auth_token)

        if r.status_code == 401:
            raise OpenTracyError(
                "Token do agente invalido ou nao autorizado. "
                "Verifique o token em ~/.ligadoai/api_token ou reconecte o canal API.",
                status_code=401,
            )
        if r.status_code == 402:
            detail = r.json().get("detail", "Quota excedida.")
            raise OpenTracyError(f"Limite excedido: {detail}", status_code=402)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After", "30")
            raise OpenTracyError(
                f"Muitas requisicoes. Aguarde {retry_after}s antes de tentar novamente.",
                status_code=429,
            )
        if r.status_code == 502:
            detail = r.text[:200] if r.text else "Erro no runtime/backend."
            raise OpenTracyError(f"Erro no servidor: {detail}", status_code=502)

        _raise_for_status(r)

        data = r.json()
        return {
            "response": data.get("response"),
            "trace_id": data.get("trace_id"),
            "duration_ms": data.get("duration_ms", 0),
            "success": data.get("success", False),
            "error": data.get("error"),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get(self, url: str, auth_token: str) -> httpx.Response:
        try:
            return self._client.get(
                url,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        except httpx.RequestError as exc:
            raise OpenTracyError(f"Falha de conexao: {exc}") from exc

    def _post(
        self, url: str, payload: dict[str, Any], auth_token: str
    ) -> httpx.Response:
        try:
            return self._client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        except httpx.TimeoutException as exc:
            raise OpenTracyError(
                f"Timeout de {self.timeout}s excedido. O backend pode estar ocupado.",
            ) from exc
        except httpx.RequestError as exc:
            raise OpenTracyError(f"Falha de conexao: {exc}") from exc

    def close(self) -> None:
        self._client.close()


def _raise_for_status(r: httpx.Response) -> None:
    """Levanta OpenTracyError para codigos HTTP nao tratados."""
    if r.is_success:
        return
    try:
        detail = r.json().get("error") or r.json().get("detail") or r.text[:200]
    except Exception:
        detail = r.text[:200]
    raise OpenTracyError(
        f"HTTP {r.status_code}: {detail}",
        status_code=r.status_code,
    )
