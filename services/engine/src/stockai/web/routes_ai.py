"""AI writing for the Blog page's "Rewrite with AI". Admin only, since it uses the admin's Gemini key."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from stockai.web.deps import CurrentUser, admin_writer
from stockai.web.gemini import AIError, generate_json

router = APIRouter(prefix="/api/ai")

_STATUS = {"not_granted": 503, "rate_limited": 429, "invalid_json": 502, "refused": 422, "upstream_error": 502}


class PromptIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=60_000)


@router.post("/json")
def write_json(body: PromptIn, _: CurrentUser = Depends(admin_writer)):
    try:
        return {"result": generate_json(body.prompt)}
    except AIError as err:
        detail = {"code": err.code, "message": err.message}
        raise HTTPException(status_code=_STATUS.get(err.code, 502), detail=detail) from err
