# PR #6 (aid4u) — analiza dyskusji code review

Kod z PR #6 został już zmergowany do main. Poniżej lista wątków z dyskusji recenzenckiej, które **nie** zostały w pełni rozwiązane w ramach PR i wymagają osobnej pracy. Utworzono dla nich bilety w Linear (projekt `AID4U`, zespół `Aid4u`).

## Pominięte (bez akcji)

- **coderabbitai** — automatyczne podsumowanie/walkthrough PR, brak konkretnej sugestii zmiany.
- **qodo-code-review** (PR Summary) — sam opis zmian; rekomendacja końcowa potwierdza, że minimalny fix w PR jest właściwy. Sugestia "shared fixture" z tego komentarza pokrywa się z osobnym wątkiem poniżej.
- **qodo-code-review** (review state, pusty `body`) — wpis bez treści, nic do wyodrębnienia.

## Zidentyfikowane akcje → bilety w Linear

### 1. [AID-5] Napraw brakujące ładowanie .env w SecretsManager.get()
- **Typ:** bug / reliability
- **Źródło:** komentarz `qodo-code-review` ("Secrets miss .env loading")
- **Problem:** `core.secrets.SecretsManager.get()` nie ładuje `.env` (to robi tylko `core.config` przy imporcie). Testy integracyjne Gemini pobierające klucz przez `get_secrets()` mogą fałszywie skipować, gdy `GEMINI_API_KEY` jest ustawiony tylko w `.env`.
- **Pliki:** `tests/core/test_gemini_integration.py:14-18`, `core/secrets.py:46-63`, `core/config.py:21-24`
- **Link:** https://linear.app/aid4u/issue/AID-5

### 2. [AID-6] Wydziel wspólny pytest fixture do pobierania klucza API Gemini i logiki skip
- **Typ:** dług techniczny / duplikacja kodu
- **Źródło:** komentarze `qodo-code-review` (High-Level Assessment) i `gemini-code-assist`, oba niezależnie proponują to samo
- **Problem:** logika pobrania `GEMINI_API_KEY` + `pytest.skip` powtórzona w 3 testach w `tests/core/test_gemini_integration.py`.
- **Link:** https://linear.app/aid4u/issue/AID-6

## Podsumowanie
- Liczba przeanalizowanych komentarzy: 5
- Liczba wyodrębnionych, atomowych zadań: 2
- Bilety utworzone w Linear via MCP (docker-mcp-gateway): tak (AID-5, AID-6)
