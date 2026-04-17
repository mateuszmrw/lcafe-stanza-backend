import os
import shutil

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse

from src.api.dependencies import get_stanza_client_dependency, require_admin
from src.api.schemas.stanza import InstallLanguageRequest
from src.core.config import get_settings
from src.infrastructure import StanzaClient

router = APIRouter(
    prefix="/admin/stanza",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/models")
def list_models(stanza_client: StanzaClient = Depends(get_stanza_client_dependency)):
    return JSONResponse(content=stanza_client.list_installed_languages())


@router.post("/models")
def install_model(
    request: InstallLanguageRequest,
    stanza_client: StanzaClient = Depends(get_stanza_client_dependency),
):
    stanza_client.install_language(request.language)
    return PlainTextResponse(content="Language and dependencies installed correctly")


@router.delete("/models")
def remove_models(stanza_client: StanzaClient = Depends(get_stanza_client_dependency)):
    stanza_client.remove_languages()
    settings = get_settings()
    path = os.path.join(os.path.dirname("app"), settings.model_dir)
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    return PlainTextResponse(content="Languages removed correctly")
