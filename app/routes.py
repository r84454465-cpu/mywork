# app/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import auth, schemas
from .services.replicate_client import call_replicate, ReplicateError
from . import storage

router = APIRouter()
bearer = HTTPBearer(auto_error=False)

def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
    token = credentials.credentials
    username = auth.get_username_for_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username


@router.post("/login/", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest):
    token = auth.authenticate_user(payload.username, payload.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"token": token}


@router.post("/prompt/", response_model=schemas.PromptResponse)
def prompt_endpoint(payload: schemas.PromptRequest, username: str = Depends(get_current_username)):
    try:
        model_text = call_replicate(payload.prompt)
    except ReplicateError as e:
        raise HTTPException(status_code=502, detail=str(e))

    storage.add_history(username=username, prompt=payload.prompt, response=model_text)

    return {"response": model_text}


@router.get("/history/", response_model=schemas.HistoryResponse)
def history_endpoint(username: str = Depends(get_current_username)):
    hist = storage.get_history(username)
    return {"history": hist}
