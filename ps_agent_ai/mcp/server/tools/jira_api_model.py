from pydantic import BaseModel


class JiraRouterRequest(BaseModel):
    payload: dict