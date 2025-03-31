from ast import Dict
from dataclasses import dataclass, field
import stanza
import logging
import threading

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    processors: list[str] = field(default_factory=lambda: ["tokenize", "pos", "lemma"])
    use_gpu: bool = False

@dataclass
class StanzaConfig:
    languages: list[str] = field(default_factory=list)
    model_dir: str = field(default="stanza_resources")

class StanzaClient:
    def __init__(self, config: StanzaConfig):
        self.config = config
        self.model_configs: Dict[str, ModelConfig] = {
            "english": ModelConfig(use_gpu=config.use_gpu),
            "russian": ModelConfig(use_gpu=config.use_gpu),
            "polish": ModelConfig(use_gpu=config.use_gpu),
        }
        self.installed_languages: list[str] = []
        self.loaded_languages: Dict[str, stanza.Pipeline] = {}
        self.download_languages()
    
    def load_pipeline(self, lang: str) -> None:
        if lang not in self.loaded_languages:
            self.loaded_languages[lang] = stanza.Pipeline(lang, dir=self.config.model_dir, download_method=None, **self.model_configs[lang].__dict__)
            
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
        logger.info(f"Installed language: {language}")

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