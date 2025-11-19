from http.client import HTTPException
from typing import Dict, Any

import requests
from langgraph.checkpoint.memory import logger
from requests.auth import HTTPBasicAuth
from .jira_api_model import JiraRouterRequest

class JiraTool:
    def __init__(self):
        self.baseUrl = "https://agent-ui-ai.atlassian.net"  # e.g. https://your-domain.atlassian.net
        self.email = "ajay.jamiahamdard@gmail.com"
        self.token = "ATATT3xFfGF0KKWs_PbNLGm8T7VIvSGJ6Tg98FuGb36IRpBpwNFGbE0NYTVhGb0xX_DUHttQ8Q-ic7lBYwX34d5IhBrTyx4sutNJRcLWjybzmpA5UTxLm9R9TF3ZARSZhJ25ALQxHA79xXgmIjRyXSUHCoABCNJGPuIu-bXhS8jdIAd5w32MGcc=05D45BEB"
        self.projectKey = "AG"

    def content_jira_issue_payload(self,text: str) -> Dict[str, Any]:
        # simple convert: each non-empty line -> paragraph
        lines = text.splitlines() or [text]
        content = []
        for line in lines:
            if line.strip():
                content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
        if not content:
            content = [{"type": "paragraph", "content": [{"type": "text", "text": ""}]}]
        return {"type": "doc", "version": 1, "content": content}

    async def call_jira(self,method:str,baseUri:str, payload: Dict[str, Any]=None) -> Dict[str, Any]:
        url = f"{self.baseUrl.rstrip('/')}{baseUri}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        request_map = {
            "GET": requests.get,
            "POST": requests.post
        }
        req_func = request_map.get(method, requests.get);
        response = req_func(
                    url,
                    json=payload,
                    auth=HTTPBasicAuth(self.email, self.token),
                    headers=headers,
                    timeout=30
                )

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}
        return {"status_code": response.status_code, "body": body}

    async def get_issue(self,req:dict):
        try:
            print(f"MCP calling add_comment {req}")
            print(f"add_comment issue_key ==>>>{req.get("issue_key")}")
            result = await self.call_jira("GET",f"/rest/api/3/issue/{req.get("issue_key")}")
            status = result["status_code"]
            response = result["body"]
            if status == 200:
                print(f"Response  {response}")
                return {"success": True, "issue_key": req.get("issue_key"), "response": response}
            else:
                logger.error("Jira create failed: {} {}", status)
                raise HTTPException(detail={"message": "Jira Fetch issue failed", "status": status})
        except Exception as e:
            logger.exception(f"Exception while fetch Jira issue:-{e}")
            raise HTTPException(status_code=500, detail={"message": str(e)})

    async def add_comment(self,req:dict):
        try:
            print(f"MCP calling add_comment {req}")
            print(f"add_comment issue_key ==>>>{req.get("issue_key")}")
            body = self.content_jira_issue_payload(req.get("comment"))
            print(f"adf ==>>>{body}")

            payload = {"body": body}
            print(f"sending payload to add_comment {payload}")
            # Idempotency: if client_request_id provided, could store in DB/cache to prevent duplicates. For brevity omitted.
            result = await self.call_jira("POST",f"/rest/api/3/issue/{req.get("issue_key")}/comment",payload)
            status = result["status_code"]
            response = result["body"]
            if status == 201:
                body = response.get("body")
                body["self"]=response.get("self")
                print(f"Response  {body}")
                return {"success": True, "issue_key": req.get("issue_key"), "response": body}
            else:
                logger.error("Jira create failed: {} {}", status, body)
                raise HTTPException(status_code=500,
                                    detail={"message": "Jira comment failed", "status": status, "body": body})
        except Exception as e:
            logger.exception(f"Exception while commenting on Jira issue:-{e}")
            raise HTTPException(status_code=500, detail={"message": str(e)})

    async def create_issue(self,req:dict):
        print(f"MCP calling create_issue {req}")
        print(f"MCP calling create_issue >>>>> {req.get("summary")}")
        print(f"MCP calling create_issue  >>> {req.get("description")}")
        try:
            adf = self.content_jira_issue_payload(req["description"])
            fields = {
                "project": {"key": self.projectKey},
                "summary": req["summary"],
                "description": adf,
                "issuetype": {"name": req.get("issue_type") or "Task"},
                "priority": {"name": req.get("priority") or "Medium"},
            }
            if req.get("labels"):
                fields["labels"] = req.get("labels") or ""
            if req.get("assignee"):
                # depending on Jira instance, assignee field accepts accountId or name/email — adjust accordingly
                fields["assignee"] = {"name": req.get("assignee")}  # older instances; modern Cloud likely use accountId
            payload = {"fields": fields}

            # Idempotency: if client_request_id provided, could store in DB/cache to prevent duplicates. For brevity omitted.
            result = await self.call_jira("POST","/rest/api/3/issue",payload)
            status = result.get("status_code")
            body = result.get("body")
            print(f"Response  {body}")
            if status == 201:
                issue_key = body.get("key")
                return {"success": True, "issue_key": issue_key, "response": body}
            else:
                logger.error("Jira create failed: {} {}", status, body)
                raise HTTPException(status_code=500,
                                    detail={"message": "Jira create failed", "status": status, "body": body})
        except Exception as e:
            logger.exception("Exception creating Jira issue")
            raise HTTPException(status_code=500, detail={"message": str(e)})
