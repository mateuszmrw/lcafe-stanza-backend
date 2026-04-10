"""
End-to-end tests for the full book import pipeline.

Requires a running docker compose stack:
    docker compose up --build

Run with:
    uv run pytest tests/test_e2e_book_import.py -m e2e -v

Covers:
  - Pages transition from status=pending → status=ready
  - Words appear in the vocabulary (with gender field)
  - GET /books/{id}/pages returns enriched tokens for ready pages
  - Tokens include word DB `id` for known vocabulary words
  - GET /books/{id}/chapters returns chapter structure
  - PATCH /vocabulary/{id}/status updates word status
  - DELETE /books/{id} removes book from DB
  - Duplicate upload rejected with 409
"""
import asyncio
import io
import time
import uuid
import zipfile

import pytest
import httpx

BASE_URL = "http://localhost:8678"
TIMEOUT = 120  # seconds to wait for the worker to finish all pages
POLL_INTERVAL = 2


def _make_minimal_epub(text: str = "Hello world. The quick brown fox.") -> bytes:
    """Build a minimal valid EPUB in memory without any external dependencies."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be the first file and uncompressed
        zf.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/epub+zip",
        )
        zf.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?>'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            "  <rootfiles>"
            '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
            "  </rootfiles>"
            "</container>",
        )
        zf.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id">'
            "  <metadata>"
            '    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">E2E Test Book</dc:title>'
            '    <dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en</dc:language>'
            '    <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/" id="id">e2e-test-1</dc:identifier>'
            "  </metadata>"
            "  <manifest>"
            '    <item id="chapter1" href="chapter1.html" media-type="application/xhtml+xml"/>'
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
            "  </manifest>"
            '  <spine toc="ncx">'
            '    <itemref idref="chapter1"/>'
            "  </spine>"
            "</package>",
        )
        zf.writestr(
            "OEBPS/toc.ncx",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            "  <head>"
            '    <meta name="dtb:uid" content="e2e-test-1"/>'
            "  </head>"
            '  <docTitle><text>E2E Test Book</text></docTitle>'
            "  <navMap>"
            '    <navPoint id="ch1" playOrder="1">'
            '      <navLabel><text>Chapter 1</text></navLabel>'
            '      <content src="chapter1.html"/>'
            "    </navPoint>"
            "  </navMap>"
            "</ncx>",
        )
        zf.writestr(
            "OEBPS/chapter1.html",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            "<head><title>Chapter 1</title></head>"
            f"<body><p>{text}</p></body>"
            "</html>",
        )
    return buf.getvalue()


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def api_client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        yield client


@pytest.fixture(scope="module")
async def auth_token(api_client: httpx.AsyncClient):
    """Register a fresh user and return an access token."""
    suffix = uuid.uuid4().hex[:8]
    email = f"e2e-{suffix}@test.local"
    password = "E2eTestPass123!"

    reg = await api_client.post(
        "/auth/register",
        json={"email": email, "username": f"e2e_{suffix}", "password": password},
    )
    assert reg.status_code in (200, 201), f"Register failed: {reg.text}"

    login = await api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return login.json()["access_token"]


@pytest.fixture(scope="module")
async def language_id(api_client: httpx.AsyncClient, auth_token: str):
    """Fetch the first available language ID."""
    resp = await api_client.get(
        "/languages",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200, f"Languages failed: {resp.text}"
    languages = resp.json()
    assert languages, "No languages seeded — check DB migrations"
    return languages[0]["id"]


@pytest.mark.e2e
class TestBookImportE2E:

    @pytest.mark.asyncio
    async def test_full_import_pipeline(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """
        Upload a book → worker tokenizes → pages become ready → tokens enriched.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub(
            "The fox jumped over the lazy dog. "
            "Python is a programming language. "
            "Learning new words every day."
        )

        # 1. Upload
        upload_resp = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "E2E Test Book"},
            files={"file": ("test.epub", epub_bytes, "application/epub+zip")},
        )
        assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
        book_id = upload_resp.json()["id"]
        assert upload_resp.json()["status"] == "processing"

        # 2. Wait for worker to finish all pages
        deadline = time.time() + TIMEOUT
        book_completed = False
        while time.time() < deadline:
            await asyncio.sleep(POLL_INTERVAL)
            book_resp = await api_client.get(f"/books/{book_id}", headers=headers)
            assert book_resp.status_code == 200
            if book_resp.json()["status"] == "completed":
                book_completed = True
                break

        assert book_completed, f"Book did not complete within {TIMEOUT}s"

        # 3. Fetch pages — all should be ready with tokens
        pages_resp = await api_client.get(f"/books/{book_id}/pages", headers=headers)
        assert pages_resp.status_code == 200
        data = pages_resp.json()
        assert data["total"] >= 1

        ready_pages = [p for p in data["items"] if p["status"] == "ready"]
        assert len(ready_pages) == data["total"], "All pages should be ready after completion"

        # Every ready page must have at least one token
        for page in ready_pages:
            assert len(page["tokens"]) > 0, f"Page {page['page_number']} has no tokens"
            for token in page["tokens"]:
                assert "w" in token
                assert "status" in token
                assert token["status"] in ("new", "learning", "known", "ignored")

        # 4. Check vocabulary was populated with gender field present
        vocab_resp = await api_client.get(
            f"/vocabulary?language_id={language_id}",
            headers=headers,
        )
        assert vocab_resp.status_code == 200
        vocab = vocab_resp.json()
        assert vocab["total"] > 0, "Words should have been added to vocabulary"
        for word_item in vocab["items"]:
            assert "gender" in word_item, "WordResponse must include gender field"

        # 5. Verify tokens have `id` for words that exist in vocabulary
        vocab_words = {w["word"]: w for w in vocab["items"]}
        for page in ready_pages:
            for token in page["tokens"]:
                surface_lower = token["w"].lower()
                if surface_lower in vocab_words:
                    assert token.get("id") is not None, (
                        f"Token '{token['w']}' is in vocabulary but has no id"
                    )
                    assert token["id"] == vocab_words[surface_lower]["id"]

    @pytest.mark.asyncio
    async def test_chapters_endpoint(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """GET /books/{id}/chapters returns structured chapter data after import."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub("Chapter endpoint test content.")

        upload_resp = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Chapters E2E Book"},
            files={"file": ("chtest.epub", epub_bytes, "application/epub+zip")},
        )
        assert upload_resp.status_code == 201
        book_id = upload_resp.json()["id"]

        chapters_resp = await api_client.get(
            f"/books/{book_id}/chapters",
            headers=headers,
        )
        assert chapters_resp.status_code == 200
        chapters = chapters_resp.json()
        assert isinstance(chapters, list)

        for chapter in chapters:
            assert "chapter_number" in chapter
            assert "first_page_number" in chapter
            assert "page_count" in chapter
            assert chapter["page_count"] >= 1

    @pytest.mark.asyncio
    async def test_word_status_update(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """After import, PATCH /vocabulary/{id}/status updates word status."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub("Status update test words content.")

        upload_resp = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Status Update E2E"},
            files={"file": ("status.epub", epub_bytes, "application/epub+zip")},
        )
        assert upload_resp.status_code == 201
        book_id = upload_resp.json()["id"]

        # Wait for at least one page to be ready
        deadline = time.time() + TIMEOUT
        word_id = None
        while time.time() < deadline and word_id is None:
            await asyncio.sleep(POLL_INTERVAL)
            vocab_resp = await api_client.get(
                f"/vocabulary?language_id={language_id}",
                headers=headers,
            )
            if vocab_resp.status_code == 200 and vocab_resp.json()["total"] > 0:
                word_id = vocab_resp.json()["items"][0]["id"]

        assert word_id is not None, "No words appeared in vocabulary after import"

        patch_resp = await api_client.patch(
            f"/vocabulary/{word_id}/status",
            json={"status": "known"},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "known"
        assert "gender" in patch_resp.json()

    @pytest.mark.asyncio
    async def test_delete_book(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """DELETE /books/{id} removes the book and returns 204."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub("Delete me after import.")

        upload_resp = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Delete E2E Book"},
            files={"file": ("deleteme.epub", epub_bytes, "application/epub+zip")},
        )
        assert upload_resp.status_code == 201
        book_id = upload_resp.json()["id"]

        del_resp = await api_client.delete(
            f"/books/{book_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Book should no longer be accessible
        get_resp = await api_client.get(f"/books/{book_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_book_rejected(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """Uploading the same EPUB twice returns 409."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub("Duplicate test content for hashing.")

        first = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Duplicate Test"},
            files={"file": ("dup.epub", epub_bytes, "application/epub+zip")},
        )
        assert first.status_code == 201

        second = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Duplicate Test Again"},
            files={"file": ("dup.epub", epub_bytes, "application/epub+zip")},
        )
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_pending_pages_visible_immediately(
        self,
        api_client: httpx.AsyncClient,
        auth_token: str,
        language_id: int,
    ):
        """Pages are visible (status=pending) immediately after upload, before worker finishes."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        epub_bytes = _make_minimal_epub("Immediate visibility test content.")

        upload_resp = await api_client.post(
            "/books",
            headers=headers,
            data={"language_id": str(language_id), "title": "Immediate Visibility Test"},
            files={"file": ("immediate.epub", epub_bytes, "application/epub+zip")},
        )
        assert upload_resp.status_code == 201
        book_id = upload_resp.json()["id"]

        # Check pages immediately — worker may not have run yet
        pages_resp = await api_client.get(f"/books/{book_id}/pages", headers=headers)
        assert pages_resp.status_code == 200
        data = pages_resp.json()
        assert data["total"] >= 1

        # All statuses must be either pending or ready (worker may have already started)
        for page in data["items"]:
            assert page["status"] in ("pending", "ready")
