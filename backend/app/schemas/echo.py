from pydantic import BaseModel


class EchoResponse(BaseModel):
    request_id: str