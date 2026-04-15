import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any  # noqa: F401

import stanza

def _to_pinyin(text: str) -> str:
    try:
        from pypinyin import lazy_pinyin, Style
        return " ".join(lazy_pinyin(text, style=Style.TONE))
    except ImportError:
        return ""

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    processors: list[str] = field(default_factory=lambda: ["tokenize", "pos", "lemma", "depparse"])
    use_gpu: bool = False


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
        self.installed_languages: list[str] = []
        self.loaded_languages: dict[str, Any] = {}
        # One lock per language — Stanza pipelines are NOT thread-safe.
        # tokenize_sync acquires the lock so only one thread uses a pipeline at a time.
        self._pipeline_locks: dict[str, threading.Lock] = {}
        self.download_languages()

    def load_pipeline(self, lang: str) -> None:
        if lang not in self.loaded_languages:
            self.loaded_languages[lang] = stanza.Pipeline(
                lang,
                dir=self.config.model_dir,
                download_method=None,
                **self.model_configs[lang].__dict__,
            )

    def get_pipeline(self, lang: str) -> stanza.Pipeline:
        if lang not in self.installed_languages:
            self.install_language(lang)
        self.load_pipeline(lang)
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
        """Return True if all processor model files exist for this language."""
        lang_code = self._LANG_CODE_MAP.get(language, language)
        processors = self.model_configs[language].processors
        lang_dir = os.path.join(self.config.model_dir, lang_code)
        if not os.path.isdir(lang_dir):
            return False
        for proc in processors:
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

    def install_language(self, language: str) -> None:
        if language not in self.model_configs:
            raise ValueError(f"Language {language} not supported")
        processor = self.model_configs[language].processors
        if self._is_language_installed(language):
            logger.info(f"Language {language} already installed, skipping download")
        else:
            logger.info(f"Downloading language: {language} with processors: {processor}")
            stanza.download(language, model_dir=self.config.model_dir, processors=processor)
        self.installed_languages.append(language)
        self.load_pipeline(language)
        if language not in self._pipeline_locks:
            self._pipeline_locks[language] = threading.Lock()
        logger.info(f"Installed language: {language}")

    def tokenize_sync(self, lang: str, text: str) -> list[dict]:
        """Thread-safe tokenization. Call via asyncio.to_thread() to avoid blocking the event loop.

        Acquires a per-language lock so only one thread uses the pipeline at a time.
        Multiple languages can tokenize concurrently.
        """
        pipeline = self.get_pipeline(lang)
        lock = self._pipeline_locks.get(lang)
        if lock is None:
            lock = threading.Lock()
            self._pipeline_locks[lang] = lock

        with lock:
            doc = pipeline(text)

        is_chinese = lang == "zh-hans"

        tokens: list[dict] = []
        for si, sentence in enumerate(doc.sentences):
            for word in sentence.words:
                feats = word.feats or ""
                gender = next(
                    (f.split("=")[1] for f in feats.split("|") if f.startswith("Gender=")),
                    "",
                )
                reading = _to_pinyin(word.text) if is_chinese else ""
                tokens.append(
                    {
                        "w": word.text,
                        "r": reading,
                        "l": word.lemma or "",
                        "lr": "",
                        "pos": word.upos or "",
                        "si": si,
                        "g": gender,
                        "feats": feats,
                        "dep_head": word.head if word.head is not None else 0,
                        "dep_rel": word.deprel or "",
                    }
                )
        return tokens

    def list_installed_models(self) -> list[str]:
        models = [lang for lang in self.loaded_languages]
        print(models)
        return models

    def remove_languages(self) -> None:
        self.installed_languages = []
        self.loaded_languages = {}


_instance = None
_lock = threading.Lock()


def get_stanza_client(config: StanzaConfig) -> StanzaClient:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = StanzaClient(config)
    return _instance
