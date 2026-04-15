"""Slovo Anki note model definition — fields, templates, and CSS."""

SLOVO_MODEL_NAME = "Slovo"

SLOVO_FIELDS = [
    "Word",
    "POS",
    "Gender",
    "Reading",
    "Morphology",
    "Definition",
    "Hint",
    "SentenceContext",
    "FrequencyTier",
    "Audio",
]

SLOVO_FRONT_TEMPLATE = """\
<div class="slovo-front">
  <div class="word">{{Word}}</div>
  {{#Reading}}<div class="reading">{{Reading}}</div>{{/Reading}}
  <div class="pos">{{POS}}</div>
</div>
"""

SLOVO_BACK_TEMPLATE = """\
<div class="slovo-back">
  {{FrontSide}}
  <hr>
  {{#Definition}}<div class="definition">{{Definition}}</div>{{/Definition}}
  {{#Hint}}<div class="hint"><span class="label">Note:</span> {{Hint}}</div>{{/Hint}}
  {{#Gender}}<div class="meta"><span class="label">Gender:</span> {{Gender}}</div>{{/Gender}}
  {{#Morphology}}<div class="meta"><span class="label">Morphology:</span> {{Morphology}}</div>{{/Morphology}}
  {{#SentenceContext}}<div class="sentence"><span class="label">Context:</span><br>{{SentenceContext}}</div>{{/SentenceContext}}
  {{#FrequencyTier}}<div class="freq">{{FrequencyTier}}</div>{{/FrequencyTier}}
  {{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}
</div>
"""

SLOVO_CSS = """\
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: #18181b;
  color: #e4e4e7;
  text-align: center;
  padding: 20px;
  line-height: 1.5;
}

.slovo-front .word {
  font-size: 2.2em;
  font-weight: 700;
  margin-bottom: 6px;
  color: #f4f4f5;
}

.slovo-front .reading {
  font-size: 1.1em;
  color: #a1a1aa;
  margin-bottom: 4px;
}

.slovo-front .pos {
  font-size: 0.85em;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

hr {
  border: none;
  border-top: 1px solid #3f3f46;
  margin: 16px 0;
}

.slovo-back {
  text-align: left;
  max-width: 480px;
  margin: 0 auto;
}

.slovo-back .definition {
  font-size: 1.15em;
  color: #e4e4e7;
  margin-bottom: 10px;
}

.slovo-back .hint {
  font-size: 0.95em;
  color: #a1a1aa;
  margin-bottom: 8px;
  font-style: italic;
}

.slovo-back .meta {
  font-size: 0.85em;
  color: #71717a;
  margin-bottom: 4px;
}

.slovo-back .label {
  color: #a1a1aa;
  font-weight: 600;
}

.slovo-back .sentence {
  font-size: 0.95em;
  color: #a1a1aa;
  margin: 10px 0;
  padding: 8px 12px;
  background: #27272a;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.slovo-back .freq {
  font-size: 0.8em;
  color: #52525b;
  margin-top: 8px;
}

.slovo-back .audio {
  margin-top: 10px;
}
"""


def get_create_model_params() -> dict:
    """Return the params dict for AnkiConnect's createModel action."""
    return {
        "modelName": SLOVO_MODEL_NAME,
        "inOrderFields": SLOVO_FIELDS,
        "css": SLOVO_CSS,
        "cardTemplates": [
            {
                "Name": "Card 1",
                "Front": SLOVO_FRONT_TEMPLATE,
                "Back": SLOVO_BACK_TEMPLATE,
            }
        ],
    }
