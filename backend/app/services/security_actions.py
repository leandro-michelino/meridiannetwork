import io
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Settings
from app.models import SecurityAction, SecurityActionHistoryResponse, SecurityActionRequest
from app.oci_clients import OciClientFactory

_OBJECT_KEY_SUFFIX = "actions.jsonl"


@dataclass(frozen=True)
class SecurityActionsService:
    settings: Settings
    client_factory: OciClientFactory

    @property
    def _enabled(self) -> bool:
        return (
            self.settings.security_action_object_storage_enabled
            and bool(self.settings.security_action_object_storage_namespace)
            and bool(self.settings.security_action_object_storage_bucket)
        )

    @property
    def _object_key(self) -> str:
        prefix = self.settings.security_action_object_storage_prefix.rstrip("/")
        return f"{prefix}/{_OBJECT_KEY_SUFFIX}"

    def _download_lines(self) -> list[str]:
        try:
            client = self.client_factory.object_storage_client()
            response = client.get_object(
                namespace_name=self.settings.security_action_object_storage_namespace,
                bucket_name=self.settings.security_action_object_storage_bucket,
                object_name=self._object_key,
            )
            return [line for line in response.data.text.splitlines() if line.strip()]
        except Exception as exc:
            # 404 = no file yet; all other errors fall back to empty
            if "404" not in str(exc) and "NotFound" not in type(exc).__name__:
                pass  # swallow; callers get an empty list
            return []

    def _upload_lines(self, lines: list[str]) -> None:
        client = self.client_factory.object_storage_client()
        content = "\n".join(lines) + "\n"
        client.put_object(
            namespace_name=self.settings.security_action_object_storage_namespace,
            bucket_name=self.settings.security_action_object_storage_bucket,
            object_name=self._object_key,
            put_object_body=io.BytesIO(content.encode()),
            content_type="application/x-ndjson",
        )

    def list_actions(self) -> SecurityActionHistoryResponse:
        actions: list[SecurityAction] = []
        archive_error: str | None = None
        storage = "browser-local"

        if self._enabled:
            storage = "object-storage"
            try:
                for line in self._download_lines():
                    try:
                        actions.append(SecurityAction.model_validate_json(line))
                    except Exception:
                        pass
                actions = list(reversed(actions))  # newest first
            except Exception as exc:
                archive_error = str(exc)

        return SecurityActionHistoryResponse(
            total_actions=len(actions),
            actions=actions,
            retention_days=self.settings.security_action_retention_days,
            storage=storage,
            archive_enabled=self._enabled,
            archive_prefix=self.settings.security_action_object_storage_prefix if self._enabled else None,
            archive_error=archive_error,
        )

    def record_action(self, request: SecurityActionRequest) -> SecurityAction:
        action = SecurityAction(
            **request.model_dump(),
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        if self._enabled:
            lines = self._download_lines()
            lines.append(action.model_dump_json())
            self._upload_lines(lines)
        return action
