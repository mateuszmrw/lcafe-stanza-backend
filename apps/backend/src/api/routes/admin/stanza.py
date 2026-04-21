import os
import shutil

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_arq_pool, get_db, get_stanza_client_dependency, require_admin
from src.api.schemas.stanza import InstallLanguageRequest
from src.core.config import get_settings
from src.infrastructure import StanzaClient
from src.infrastructure.db.models.content import ContentItem, ContentPage

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


@router.post("/retokenize")
async def retokenize_all(
    language_id: int | None = None,
    session: AsyncSession = Depends(get_db),
    arq=Depends(get_arq_pool),
) -> JSONResponse:
    """Enqueue tokenize_page for every ready page, optionally filtered by language.

    Use after upgrading Stanza models or adding new processors (NER, constituency,
    morgsep, coref). Pages are re-tokenized in place — no content is lost.
    """
    query = sa.select(ContentPage.id).join(
        ContentItem, ContentPage.content_item_id == ContentItem.id
    ).where(ContentPage.status == "ready")

    if language_id is not None:
        query = query.where(ContentItem.language_id == language_id)

    result = await session.execute(query)
    page_ids = [str(row.id) for row in result]

    for pid in page_ids:
        await arq.enqueue_job("tokenize_page", pid)

    return JSONResponse({"enqueued": len(page_ids)})
