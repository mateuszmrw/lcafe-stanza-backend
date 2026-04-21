import inspect
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any  # noqa: F401

import stanza

from src.core.config import get_settings


def _to_pinyin(text: str) -> str:
    try:
        from pypinyin import lazy_pinyin, Style
        return " ".join(lazy_pinyin(text, style=Style.TONE))
    except ImportError:
        return ""


logger = logging.getLogger(__name__)


def _patch_stanza_coref_compat() -> None:
    """Give plateau_epochs a default so old coref .pt files (pre-1.11.x) still load.

    Stanza 1.11.x added plateau_epochs as a required field to CorefModel.Config,
    but the udcoref_xlm-roberta-lora model file on the resources server was saved
    before that change and doesn't carry the key.  Patching the default to 5
    (the value used in Stanza's own training scripts) lets load_model succeed
    without modifying the on-disk model file.
    """
    try:
        from stanza.models.coref import model as _coref_model
        sig = inspect.signature(_coref_model.Config.__init__)
        param = sig.parameters.get("plateau_epochs")
        if param is not None and param.default is inspect.Parameter.empty:
            _orig = _coref_model.Config.__init__
            def _patched(self, *args: object, plateau_epochs: int = 5, **kwargs: object) -> None:
                _orig(self, *args, plateau_epochs=plateau_epochs, **kwargs)
            _coref_model.Config.__init__ = _patched  # type: ignore[method-assign]
            logger.debug("Applied stanza coref Config.plateau_epochs compatibility patch")
    except Exception:
        pass


_patch_stanza_coref_compat()

# Per-language feature gating — referenced by all NLP ADRs (018–025).
# Add a language here only when Stanza ships a supported model.
_LANGS_WITH_MWT = {"french", "spanish", "italian", "portuguese"}
_LANGS_WITH_NER = {"english", "russian", "polish", "spanish", "german", "zh-hans"}  # ko absent from stanza NER models
_LANGS_WITH_COREF = {"english", "russian", "polish", "spanish", "german"}
_LANGS_WITH_CONSTITUENCY = {"english", "spanish", "german", "italian", "portuguese"}  # verified against stanza 1.11.0 resources + docs
_LANGS_WITH_MORGSEP = {"russian"}  # requires `morphseg` pip package (not a Stanza model file)

# Processors that can be silently skipped when the model is unavailable.
# Skipped on disk (upgrade scenario) when the language dir exists but the processor dir doesn't.
# Skipped at download time when the Stanza resources registry doesn't list them for that language.
# Skipped at load time when the model raises TypeError/ImportError (version incompatibility).
# Core processors (tokenize, pos, lemma, depparse) are never optional.
_OPTIONAL_PROCESSORS = frozenset({"morphseg", "constituency", "coref"})

# Processors delivered as pip packages rather than Stanza model files.
# They have no .pt file in stanza_resources/ — presence is determined by
# whether the package is importable, not by directory existence.
# _load_pipeline_with_optional_fallback handles ImportError if the package is absent.
_PIP_BASED_PROCESSORS = frozenset({"morphseg"})


_COREF_BUDGET_SECONDS = 10  # max wall-clock time for coref chain building per page


@dataclass
class TokenizeResult:
    tokens: list[dict]
    constituency: list[str | None]  # one bracket string per sentence; None on parse fail


@dataclass
class ModelConfig:
    processors: list[str] = field(default_factory=lambda: ["tokenize", "pos", "lemma", "depparse"])
    use_gpu: bool = False
    ner_enabled: bool = False
    coref_enabled: bool = False
    constituency_enabled: bool = False
    mwt_enabled: bool = False


@dataclass
class StanzaConfig:
    languages: list[str] = field(default_factory=list)
    model_dir: str = field(default="stanza_resources")
    use_gpu: bool = False


class StanzaClient:
    def __init__(self, config: StanzaConfig):
        self.config = config
        self.model_configs: dict[str, ModelConfig] = {
            "english": ModelConfig(use_gpu=config.use_gpu),
            "russian": ModelConfig(use_gpu=config.use_gpu),
            "polish": ModelConfig(use_gpu=config.use_gpu),
            "ko": ModelConfig(use_gpu=config.use_gpu),
            "zh-hans": ModelConfig(use_gpu=config.use_gpu),
        }
        # Gate processors in Stanza pipeline order: ner → constituency → coref → morphseg.
        # Each processor may depend on those before it (NER needs pos/lemma; coref needs NER; etc.)
        for lang, cfg in self.model_configs.items():
            if lang in _LANGS_WITH_NER:
                cfg.processors = cfg.processors + ["ner"]
                cfg.ner_enabled = True

        for lang, cfg in self.model_configs.items():
            if lang in _LANGS_WITH_CONSTITUENCY:
                cfg.processors = cfg.processors + ["constituency"]
                cfg.constituency_enabled = True

        coref_langs = set(get_settings().coref_enabled_languages)
        for lang, cfg in self.model_configs.items():
            if lang in coref_langs and lang in _LANGS_WITH_COREF:
                cfg.processors = cfg.processors + ["coref"]
                cfg.coref_enabled = True

        for lang, cfg in self.model_configs.items():
            if lang in _LANGS_WITH_MORGSEP:
                cfg.processors = cfg.processors + ["morphseg"]

        for lang, cfg in self.model_configs.items():
            if lang in _LANGS_WITH_MWT:
                # Insert mwt right after tokenize (before pos/lemma).
                idx = cfg.processors.index("tokenize") + 1
                cfg.processors = cfg.processors[:idx] + ["mwt"] + cfg.processors[idx:]
                cfg.mwt_enabled = True

        self.installed_languages: list[str] = []
        self.loaded_languages: dict[str, Any] = {}
        # One lock per language — Stanza pipelines are NOT thread-safe.
        # tokenize_sync acquires the lock so only one thread uses a pipeline at a time.
        self._pipeline_locks: dict[str, threading.Lock] = {}
        self.download_languages()

    def load_pipeline(self, lang: str) -> None:
        if lang not in self.loaded_languages:
            cfg = self.model_configs[lang]
            self.loaded_languages[lang] = stanza.Pipeline(
                lang,
                dir=self.config.model_dir,
                download_method=None,
                processors=cfg.processors,
                use_gpu=cfg.use_gpu,
            )

    def _load_pipeline_with_optional_fallback(self, language: str) -> None:
        """Load pipeline, retrying without optional processors on model compatibility errors."""
        cfg = self.model_configs[language]
        while True:
            try:
                self.load_pipeline(language)
                return
            except (TypeError, ImportError) as exc:
                dropped = False
                for proc in list(cfg.processors):
                    if proc in _OPTIONAL_PROCESSORS:
                        logger.warning(
                            "Optional processor %s failed to load for %s (%s) — disabling",
                            proc, language, type(exc).__name__,
                        )
                        cfg.processors = [p for p in cfg.processors if p != proc]
                        if proc == "coref":
                            cfg.coref_enabled = False
                        elif proc == "constituency":
                            cfg.constituency_enabled = False
                        dropped = True
                        break
                if not dropped:
                    raise

    def get_pipeline(self, lang: str) -> stanza.Pipeline:
        if lang not in self.installed_languages:
            self.install_language(lang)
        self._load_pipeline_with_optional_fallback(lang)
        return self.loaded_languages[lang]

    def list_installed_languages(self) -> list[str]:
        return [lang.capitalize() for lang in self.model_configs]

    # These are always pre-loaded regardless of the `languages` env var.
    DEFAULT_LANGUAGES: list[str] = ["english", "russian", "polish", "ko", "zh-hans"]

    # Stanza stores models under the ISO code, not the full language name
    _LANG_CODE_MAP: dict[str, str] = {
        "english": "en",
        "russian": "ru",
        "polish": "pl",
        "ko": "ko",
        "zh-hans": "zh-hans",
    }

    def _is_language_installed(self, language: str) -> bool:
        """Return True if all processor model files exist for this language.

        Pip-based processors (e.g. morphseg) have no .pt file — they are skipped
        here and handled by _load_pipeline_with_optional_fallback via ImportError.
        """
        lang_code = self._LANG_CODE_MAP.get(language, language)
        processors = self.model_configs[language].processors
        lang_dir = os.path.join(self.config.model_dir, lang_code)
        if not os.path.isdir(lang_dir):
            return False
        for proc in processors:
            if proc in _PIP_BASED_PROCESSORS:
                continue
            proc_dir = os.path.join(lang_dir, proc)
            if not os.path.isdir(proc_dir):
                return False
            if not any(f.endswith(".pt") for f in os.listdir(proc_dir)):
                return False
        return True

    def download_languages(self):
        # Merge defaults with any extra languages from config (deduped, order preserved).
        to_load = list(self.DEFAULT_LANGUAGES)
        for lang in self.config.languages:
            if lang not in to_load:
                to_load.append(lang)
        for lang in to_load:
            self.install_language(lang)
        logger.info(f"Downloaded languages: {to_load}")

    def _drop_missing_optional_processors(self, language: str) -> None:
        """Remove optional processors whose model dirs don't exist on an already-installed language.

        Only runs when the language base dir exists (partial upgrade scenario).  For a fresh
        install the language dir won't exist yet, so we skip this and let `_download_with_fallback`
        handle processors the resources registry doesn't know about.

        Pip-based processors (e.g. morphseg) have no .pt file and are always kept here —
        _load_pipeline_with_optional_fallback drops them via ImportError if the package is absent.
        """
        lang_code = self._LANG_CODE_MAP.get(language, language)
        lang_dir = os.path.join(self.config.model_dir, lang_code)
        if not os.path.isdir(lang_dir):
            return  # fresh install — nothing to prune
        cfg = self.model_configs[language]
        kept = []
        for proc in cfg.processors:
            if proc in _OPTIONAL_PROCESSORS and proc not in _PIP_BASED_PROCESSORS:
                proc_dir = os.path.join(lang_dir, proc)
                installed = os.path.isdir(proc_dir) and any(
                    f.endswith(".pt") for f in os.listdir(proc_dir)
                )
                if not installed:
                    logger.warning(
                        "Optional processor %s not found for %s — skipping (download to enable)",
                        proc,
                        language,
                    )
                    continue
            kept.append(proc)
        cfg.processors = kept

    def _download_with_fallback(self, language: str) -> None:
        """Download processors, retrying without optional ones when the resources registry lacks them."""
        cfg = self.model_configs[language]
        while cfg.processors:
            try:
                stanza.download(language, model_dir=self.config.model_dir, processors=cfg.processors)
                return
            except (ValueError, KeyError) as exc:
                msg = str(exc)
                dropped = False
                for proc in list(cfg.processors):
                    if proc in _OPTIONAL_PROCESSORS and proc in msg:
                        logger.warning(
                            "Processor %s not available for %s in resources registry — removing",
                            proc,
                            language,
                        )
                        cfg.processors = [p for p in cfg.processors if p != proc]
                        dropped = True
                        break
                if not dropped:
                    raise

    def _pre_download_coref_bert(self, language: str) -> None:
        """Download xlm-roberta-large before pipeline load.

        stanza.Pipeline(download_method=None) forces local_files_only=True for all
        HuggingFace downloads, so the base BERT model must already be in the HF cache
        before the pipeline is constructed.  We download it once here with internet
        access; subsequent loads find it offline via the cached files.
        """
        if "coref" not in self.model_configs[language].processors:
            return
        try:
            from transformers import AutoModel, AutoTokenizer
            bert_model = "FacebookAI/xlm-roberta-large"
            logger.info("Pre-downloading coref BERT base model: %s (one-time download)", bert_model)
            AutoTokenizer.from_pretrained(bert_model, local_files_only=False)
            AutoModel.from_pretrained(bert_model, local_files_only=False)
            logger.info("Coref BERT model cached: %s", bert_model)
        except Exception as exc:
            logger.warning(
                "Failed to pre-download coref BERT for %s (%s) — coref may be disabled",
                language, exc,
            )

    def install_language(self, language: str) -> None:
        if language not in self.model_configs:
            raise ValueError(f"Language {language} not supported")
        processor = self.model_configs[language].processors
        if self._is_language_installed(language):
            logger.info(f"Language {language} already installed, skipping download")
        else:
            logger.info(f"Downloading language: {language} with processors: {processor}")
            self._download_with_fallback(language)
        # Prune optional processors that are still missing after the download attempt
        # (e.g. not in Stanza's resources registry for this language).
        # Must run after the install check so newly added optional processors
        # (like morphseg) trigger a download rather than being silently skipped.
        self._drop_missing_optional_processors(language)
        self._pre_download_coref_bert(language)
        self.installed_languages.append(language)
        try:
            self._load_pipeline_with_optional_fallback(language)
        except FileNotFoundError as exc:
            # Partial install: processor .pt files exist but a shared dependency
            # (e.g. pretrain embedding) is missing. Re-download to repair.
            logger.warning(
                "Pipeline load failed for %s (missing file: %s) — re-downloading to repair",
                language, exc,
            )
            self._download_with_fallback(language)
            self._load_pipeline_with_optional_fallback(language)
        if language not in self._pipeline_locks:
            self._pipeline_locks[language] = threading.Lock()
        logger.info(f"Installed language: {language}")

    def tokenize_sync(self, lang: str, text: str) -> TokenizeResult:
        """Thread-safe tokenization. Call via asyncio.to_thread() to avoid blocking the event loop.

        Acquires a per-language lock so only one thread uses the pipeline at a time.
        Multiple languages can tokenize concurrently.
        """
        pipeline = self.get_pipeline(lang)
        # Double-checked locking: the fast path is dict.get without any lock.
        # If missing, we acquire the global lock and check again before creating
        # the per-language lock — prevents two threads creating separate locks
        # for the same language, which would allow concurrent pipeline calls.
        lock = self._pipeline_locks.get(lang)
        if lock is None:
            with _lock:
                lock = self._pipeline_locks.get(lang)
                if lock is None:
                    lock = threading.Lock()
                    self._pipeline_locks[lang] = lock

        with lock:
            doc = pipeline(text)

        cfg = self.model_configs.get(lang, ModelConfig())
        is_chinese = lang == "zh-hans"

        # Coref chain annotation (per-occurrence, not per-lemma).
        # Build {(sentence_idx, word_id): (chain_id, is_head, rep_text, is_zero)}.
        coref_map: dict[tuple[int, int], tuple[int, bool, str, bool]] = {}
        if cfg.coref_enabled and hasattr(doc, "coref") and doc.coref:
            t0 = time.monotonic()
            try:
                for chain_id, chain in enumerate(doc.coref, start=1):
                    # Representative: longest non-pronoun mention, fallback to first.
                    rep_mention = None
                    for mention in chain.mentions:
                        m_text = getattr(mention, "text", "") or ""
                        if rep_mention is None or len(m_text) > len(getattr(rep_mention, "text", "") or ""):
                            rep_mention = mention
                    rep_text = getattr(rep_mention, "text", "") or "" if rep_mention else ""

                    for mention_idx, mention in enumerate(chain.mentions):
                        is_zero = bool(getattr(mention, "is_zero", False))
                        si_m = getattr(mention, "sentence", 0)
                        start_w = getattr(mention, "start_word", 0)
                        end_w = getattr(mention, "end_word", start_w + 1)
                        for wid in range(start_w, end_w):
                            coref_map[(si_m, wid)] = (
                                chain_id,
                                mention_idx == 0 and wid == start_w,
                                rep_text,
                                is_zero,
                            )
                    if time.monotonic() - t0 > _COREF_BUDGET_SECONDS:
                        logger.warning("coref budget exceeded on lang=%s, truncating chains", lang)
                        coref_map.clear()
                        break
            except Exception:
                logger.exception("coref chain building failed for lang=%s, skipping", lang)
                coref_map.clear()

        # Constituency: one bracket string per sentence.
        constituency: list[str | None] = []
        if cfg.constituency_enabled:
            for sentence in doc.sentences:
                try:
                    tree = sentence.constituency
                    constituency.append(str(tree) if tree is not None else None)
                except Exception:
                    constituency.append(None)

        tokens: list[dict] = []
        next_mwt_id = 1
        for si, sentence in enumerate(doc.sentences):
            for stanza_token in sentence.tokens:
                is_mwt = isinstance(stanza_token.id, tuple)
                mwt_gid: int | None = None
                if is_mwt:
                    mwt_gid = next_mwt_id
                    next_mwt_id += 1

                for word in stanza_token.words:
                    feats = word.feats or ""
                    gender = next(
                        (f.split("=")[1] for f in feats.split("|") if f.startswith("Gender=")),
                        "",
                    )
                    reading = _to_pinyin(word.text) if is_chinese else ""

                    # NER: word.parent is the Token object; .ner holds the IOB tag (e.g. "B-PER").
                    ent_type = ""
                    ent_iob = ""
                    if cfg.ner_enabled and word.parent:
                        ner_tag = word.parent.ner or "O"
                        if ner_tag != "O":
                            iob, _, etype = ner_tag.partition("-")
                            ent_iob = iob
                            ent_type = etype

                    # Coref: word.id is 1-based; coref_map is 0-based.
                    word_idx = (word.id - 1) if isinstance(word.id, int) else 0
                    cc, ch, cr, cz = coref_map.get((si, word_idx), (0, False, "", False))

                    # Morpheme segmentation (morgseg processor, RU only in current active set).
                    morphemes = getattr(word, "morphemes", None)

                    tokens.append(
                        {
                            "w": word.text,
                            "r": reading,
                            "l": word.lemma or "",
                            "lr": "",
                            "pos": word.upos or "",
                            "x": word.xpos or "",
                            "si": si,
                            "g": gender,
                            "feats": feats,
                            "dep_head": word.head if word.head is not None else 0,
                            "dep_rel": word.deprel or "",
                            "e": ent_type,
                            "eb": ent_iob,
                            "m": list(morphemes) if morphemes else [],
                            "lm": [],  # filled in below after batch lemma segmentation
                            "cc": cc,
                            "ch": ch,
                            "cr": cr,
                            "cz": cz,
                            "mwt_group_id": mwt_gid,
                        }
                    )

        # Batch-segment lemmas using the pipeline's already-loaded morphseg model.
        # Lemma morphemes are more consistent than surface-form morphemes because
        # they don't carry inflectional endings, avoiding noise like рас·с·казать·ывать·й
        # (from imperative рассказывай) when the user views рассказываем.
        if "morphseg" in cfg.processors:
            try:
                proc = pipeline.processors.get("morphseg")
                segmenter = getattr(proc, "_segmenter", None)
                if segmenter is not None:
                    unique_lemmas = sorted(
                        {t["l"] for t in tokens if t["l"] and " " not in t["l"]}
                    )
                    if unique_lemmas:
                        results = segmenter.segment(
                            " ".join(unique_lemmas), show_progress=False
                        )
                        lm_map = {
                            lemma: segs
                            for lemma, segs in zip(unique_lemmas, results)
                            if segs
                        }
                        for tok in tokens:
                            tok["lm"] = lm_map.get(tok["l"], [])
            except Exception:
                logger.debug("Lemma morpheme segmentation failed, skipping", exc_info=True)

        return TokenizeResult(tokens=tokens, constituency=constituency)

    def list_installed_models(self) -> list[str]:
        return list(self.loaded_languages)

    def remove_languages(self) -> None:
        self.installed_languages = []
        self.loaded_languages = {}


_instance: StanzaClient | None = None
_lock = threading.Lock()


def get_stanza_client(config: StanzaConfig) -> StanzaClient:
    """Return the process-wide StanzaClient, creating it if needed.

    Prefer constructing the client eagerly in the app lifespan and sharing it
    via `app.state.stanza`. This function remains for ARQ workers and legacy
    callers that don't have an app instance.
    """
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = StanzaClient(config)
    return _instance


def set_stanza_client(client: StanzaClient) -> None:
    """Register an already-constructed client as the process-wide singleton."""
    global _instance
    with _lock:
        _instance = client
