from fastapi import APIRouter

from . import audio, cover, crud, pages, tts

router = APIRouter()
router.include_router(crud.router)
router.include_router(pages.router)
router.include_router(cover.router)
router.include_router(audio.router)
router.include_router(tts.router)
