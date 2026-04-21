"""Route registration.

`all_routers` lists every APIRouter the app exposes. main.py includes them in
order. Add a new router here — do not touch main.py.
"""

from fastapi import APIRouter

from . import (
    activity,
    auth,
    books,
    dictionary,
    exercises,
    grammar,
    health,
    languages,
    nlp,
    phrases,
    sentences,
    setup,
    stats,
    synonyms,
    translation,
    users,
    vocabulary,
    website,
    youtube,
)
from .admin import (
    anki as admin_anki,
)
from .admin import (
    data as admin_data,
)
from .admin import (
    deepl_instances as admin_deepl_instances,
)
from .admin import (
    dictionary as admin_dictionary,
)
from .admin import (
    frequencies as admin_frequencies,
)
from .admin import (
    languages as admin_languages,
)
from .admin import (
    llm as admin_llm,
)
from .admin import (
    providers as admin_providers,
)
from .admin import (
    cognates as admin_cognates,
)
from .admin import (
    stanza as admin_stanza,
)
from .admin import (
    system_keys as admin_system_keys,
)
from .admin import (
    tts as admin_tts,
)
from .admin import (
    users as admin_users,
)
from .admin import (
    youtube as admin_youtube,
)

all_routers: list[APIRouter] = [
    health.router,
    nlp.router,
    auth.router,
    users.router,
    books.router,
    exercises.router,
    languages.router,
    vocabulary.router,
    dictionary.router,
    translation.router,
    grammar.router,
    synonyms.router,
    phrases.router,
    stats.router,
    sentences.router,
    activity.router,
    youtube.router,
    website.router,
    admin_languages.router,
    admin_providers.router,
    admin_users.router,
    admin_dictionary.router,
    admin_system_keys.router,
    admin_deepl_instances.router,
    admin_llm.router,
    admin_data.router,
    admin_frequencies.router,
    admin_tts.router,
    admin_anki.router,
    admin_youtube.router,
    admin_stanza.router,
    admin_cognates.router,
    setup.router,
]

__all__ = ["all_routers"]
