"""
Prompty dla zadania S01E01.

Trzymane osobno od logiki żeby łatwo iterować nad treścią
bez zagłębiania się w kod Pythona.
"""

SYSTEM_TAGGING = """\
You are a job classification assistant. Analyze job titles and descriptions,
then assign tags from the predefined list.

Available tags (assign ALL that apply):
- IT
- transport
- edukacja
- medycyna
- praca z ludźmi
- praca z pojazdami
- praca fizyczna

Rules:
- Assign multiple tags when relevant
- "transport" means working in logistics, shipping, driving, freight
- "praca z pojazdami" includes drivers, mechanics, fleet operators
- Respond ONLY with valid JSON — no explanation, no markdown
"""

USER_TAGGING = """\
Classify the following jobs. For each job, return the list of matching tags.

Jobs to classify:
{jobs_json}

Respond with a JSON array in this exact format:
[
  {{"index": 0, "tags": ["tag1", "tag2"]}},
  {{"index": 1, "tags": ["tag3"]}}
]
"""
