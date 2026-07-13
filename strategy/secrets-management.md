# Strategia Zarządzania Sekretami — aid4u

> **Status:** Living Document | v1.0.0
> **Ścieżka docelowa w repo:** `aid4u/strategy/secrets-management.md`
> **Ostatnia aktualizacja:** 2026-07-02

---

## 🔐 Filozofia "Keyring First"

W projekcie `aid4u` bezpieczeństwo kluczy API jest priorytetem. Stosujemy podejście, w którym sekrety nigdy nie powinny znajdować się w plikach tekstowych na dysku w formie jawnej, jeśli jest dostępna alternatywa systemowa.

### Główne zasady:
1. **Keyring jako Primary Storage:** Wszystkie klucze API i tokeny są przechowywane w systemowym magazynie haseł (OS Keychain / Secret Service).
2. **.env jako Fallback / Bootstrap:** Plik `.env` jest dopuszczalny wyłącznie jako tymczasowy magazyn do importu lub w środowiskach, gdzie keyring jest niedostępny (np. niektóre instancje VPS).
3. **Zakaz Commitowania:** Pliki `.env` oraz wszelkie pliki zawierające sekrety są bezwzględnie zablokowane w `.gitignore`.

---

## 🚫 Reżim dostępu (ABSOLUTNE ZASADY)

1. **ZAKAZ PODGLĄDU `.env`:** Obowiązuje **ABSOLUTNY ZAKAZ** otwierania, czytania lub wyświetlania zawartości plików `.env` oraz `.env*`. Jakakolwiek próba lub potrzeba odczytu tych plików przez Agenta jest błędem. W razie potrzeby należy skorzystać wyłącznie z interfejsu `SecretsManager()` lub `Config()`. Jeśli te mechanizmy są niewystarczające — należy oddelegować zadanie do użytkownika.
2. **PRIORYTET KONFIGURACJI:** `Config()` ma wyższy priorytet nad `SecretsManager()` w dostępie do konfiguracji aplikacji. `SecretsManager()` powinien być używany do operacji zarządzania samymi sekretami (set/delete/list), natomiast `Config()` jest głównym interfejsem dla logiki biznesowej.
3. **BEZPIECZEŃSTWO KLUCZY:** Jeśli Agent przypadkowo pozna treść klucza API (poza wymienionym jako przykład `APIKEY`), **MUSI** natychmiast zgłosić to użytkownikowi i przerwać wykonywane zadanie.
4. **OBFUSKACJA WYDRUKU:** Każde jawne wywołanie listy sekretów lub ich wartości (np. w celach diagnostycznych) **MUSI** odbywać się z użyciem obfuscacji (pokazywanie tylko pierwszych i ostatnich 3-4 znaków, reszta maskowana gwiazdkami).
5. **CZYSTOŚĆ LOGÓW:** Żaden sekret nie może trafić do logów aplikacji ani wyjścia konsoli w formie jawnej.

---

## 🛠️ Mechanizm techniczny

### Usługa i Implementacja
- **Service Name:** `aid4u`
- **Klasa bazowa:** `SecretsManager` (`aid4u/core/secrets.py`)
- **Singleton:** `Config` (`aid4u/core/config.py`)

### Procedura sprawdzania (Lookup Order):
1. Systemowy Keyring (funkcja `_from_keyring`).
2. Zmienne środowiskowe OS (`os.getenv`).
3. Plik `.env` (ładowany przez `python-dotenv`).

---

## 📋 Aktualna lista obsługiwanych kluczy

Poniższa lista definiuje klucze uznawane za "standardowe" w systemie `SecretsManager`:

| Klucz | Opis |
|-------|------|
| `APIKEY` | Główny klucz API projektu aid4u |
| `ANTHROPIC_API_KEY` | Klucz do modeli Claude (Anthropic) |
| `OPENAI_API_KEY` | Klucz do modeli GPT (OpenAI) |
| `GEMINI_API_KEY` | Klucz do modeli Gemini (Google) — tier **standard** (darmowy) |
| `GEMINI_API_KEY_PREMIUM` | Klucz do modeli Gemini (Google) — tier **premium** (płatny) |
| `LANGFUSE_PUBLIC_KEY` | Klucz publiczny do obserwacji Langfuse |
| `LANGFUSE_SECRET_KEY` | Klucz prywatny do obserwacji Langfuse |
| `LOGFIRE_TOKEN` | Token do logowania i telemetrii Pydantic Logfire |
| `VPS_HOST` | Adres hosta do deploymentu / SSH |

---

## ⚠️ Szczególny przypadek: darmowy vs płatny klucz Gemini

Free i paid tier Gemini API są własnością **osobnych projektów Google Cloud**
(billing wyłączony vs włączony) — jeden klucz API fizycznie nie może obsłużyć
obu tierów naraz. Dlatego dla Gemini istnieją **dwa** osobne klucze
(`GEMINI_API_KEY` / `GEMINI_API_KEY_PREMIUM`), a nie jeden z przełącznikiem.

Wybór, który klucz zostanie użyty, odbywa się **wyłącznie** w
`core/llm/factory.py` (parametr `tier`, domyślnie `"standard"`) —
`GeminiAdapter` o tierach nic nie wie i nie powinien. CLI: `run.py solve ... --premium`.
Szczegóły strategii eskalacji: `strategy/llm-selection.md`.

---

## 🔄 Workflow Agenta

Gdy brakuje klucza:
1. Agent **nie prosi** o wpisanie klucza w `.env`.
2. Agent **instruuje** użytkownika, jak ustawić klucz przez keyring:
   `uv run python -m keyring set aid4u <KEY_NAME>`
3. Jeśli użytkownik dostarczy klucze w sekcji `.env`, Agent powinien zaproponować uruchomienie `uv run scripts/import_keyring.py` i natychmiastowe usunięcie ich z pliku tekstowego.
