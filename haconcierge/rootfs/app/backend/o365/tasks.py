import logging
from datetime import datetime
from typing import Optional
import httpx

from .auth import O365Auth

logger = logging.getLogger(__name__)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class O365TasksClient:
    """Microsoft Planner integration for shared group tasks."""

    def __init__(self, auth: O365Auth, plan_id: str, group_email: str):
        self.auth = auth
        self.plan_id = plan_id
        self.group_email = group_email
        self._bucket_id: Optional[str] = None

    def _headers(self) -> dict:
        token = self.auth.get_token()
        if not token:
            raise RuntimeError("Could not obtain O365 access token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _get_default_bucket(self) -> Optional[str]:
        if self._bucket_id:
            return self._bucket_id
        url = f"{GRAPH_BASE}/planner/plans/{self.plan_id}/buckets"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                buckets = resp.json().get("value", [])
                if buckets:
                    self._bucket_id = buckets[0]["id"]
                    return self._bucket_id
        except Exception as e:
            logger.error("Failed to get Planner buckets: %s", e)
        return None

    async def _resolve_user_ids(self, emails: list[str]) -> list[str]:
        ids = []
        for email in emails:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(
                        f"{GRAPH_BASE}/users/{email}?$select=id",
                        headers=self._headers(),
                    )
                    if resp.status_code == 200:
                        ids.append(resp.json()["id"])
            except Exception:
                pass
        return ids

    async def create_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        assigned_to: list[str] = None,
    ) -> Optional[str]:
        bucket_id = await self._get_default_bucket()
        if not bucket_id:
            logger.error("No Planner bucket found for plan %s", self.plan_id)
            return None

        body: dict = {
            "planId": self.plan_id,
            "bucketId": bucket_id,
            "title": title,
        }
        if due_date:
            body["dueDateTime"] = due_date.strftime("%Y-%m-%dT00:00:00Z")
        if assigned_to:
            user_ids = await self._resolve_user_ids(assigned_to)
            if user_ids:
                body["assignments"] = {uid: {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"} for uid in user_ids}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(f"{GRAPH_BASE}/planner/tasks", json=body, headers=self._headers())
                resp.raise_for_status()
                task_id = resp.json().get("id")

            # Add description as task detail
            if description and task_id:
                await self._set_task_details(task_id, description)

            return task_id
        except Exception as e:
            logger.error("Failed to create Planner task: %s", e)
            return None

    async def _set_task_details(self, task_id: str, description: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get ETag first
                resp = await client.get(
                    f"{GRAPH_BASE}/planner/tasks/{task_id}/details",
                    headers=self._headers(),
                )
                etag = resp.headers.get("ETag", "*")
                patch_headers = {**self._headers(), "If-Match": etag}
                await client.patch(
                    f"{GRAPH_BASE}/planner/tasks/{task_id}/details",
                    json={"description": description},
                    headers=patch_headers,
                )
        except Exception as e:
            logger.warning("Failed to set task details: %s", e)

    async def list_tasks(self) -> list[dict]:
        url = f"{GRAPH_BASE}/planner/plans/{self.plan_id}/tasks?$select=id,title,dueDateTime,percentComplete,assignments"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                return resp.json().get("value", [])
        except Exception as e:
            logger.error("Failed to list Planner tasks: %s", e)
            return []
