import logging
import threading
from dataclasses import dataclass, field
from typing import Any  # noqa: F401

import stanza

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

    def download_languages(self):
        for lang in self.config.languages:
            self.install_language(lang)
        logger.info(f"Downloaded languages: {self.config.languages}")

    def install_language(self, language: str) -> None:
        if language not in self.model_configs:
            raise ValueError(f"Language {language} not supported")
        processor = self.model_configs[language].processors
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

        tokens: list[dict] = []
        for si, sentence in enumerate(doc.sentences):
            for word in sentence.words:
                feats = word.feats or ""
                gender = next(
                    (f.split("=")[1] for f in feats.split("|") if f.startswith("Gender=")),
                    "",
                )
                tokens.append(
                    {
                        "w": word.text,
                        "r": "",
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
