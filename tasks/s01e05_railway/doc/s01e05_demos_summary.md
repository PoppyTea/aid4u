---
edges:
  - to: "[[s01e01_demos_summary]]"
    type: "builds_upon"
  - to: "[[s01e04_demos_summary]]"
    type: "extends_mcp"
tags:
  - "#demo"
  - "#ai-devs-4"
  - "#mcp"
  - "#agent-loop"
  - "#human-in-the-loop"
  - "#token-management"
difficulty_python: "Średni"
core_tech_ts:
  - "Hono"
  - "OpenAI SDK (Responses API)"
  - "@google/genai (Interactions API)"
  - "@modelcontextprotocol/sdk"
  - "gray-matter"
  - "Drizzle ORM"
core_tech_py:
  - "FastAPI"
  - "openai / google-genai"
  - "mcp (python sdk)"
  - "python-frontmatter"
  - "SQLAlchemy / SQLModel"
status: "to-do"
associated_task: "s01e05"
demo_id: "01_05_agent & 01_05_confirmation"
---

# Karta Dema: Analiza Dem s01e05 (Agent API & Interactive Confirmation)

## 📌 Krótki Opis
Dema dla lekcji `s01e05` prezentują produkcyjną architekturę autonomicznego agenta wielomodelowego (z obsługą OpenAI i Gemini) oraz wzorce bezpieczeństwa podczas wykonywania akcji krytycznych. Pierwsze demo (`01_05_agent`) implementuje pełny serwer agenta w Hono z nieblokującą maszyną stanów, przycinaniem kontekstu (Pruning & Summarization), protokołem MCP i rekurencyjną delegacją pod-agentów. Drugie demo (`01_05_confirmation`) przedstawia interaktywną pętlę REPL z wyznaczonym progiem bezpieczeństwa (Human-in-the-Loop), potwierdzaniem wysyłki e-maili, listą zaufania w ramach sesji oraz weryfikacją odbiorców poprzez białą listę (whitelist).

## 💻 Technologia

### Trudność Przepisania
**Ocena: Średnia.** Przepisanie architektury na Pythona w ramach `aid4u` jest przejrzyste i bezpieczne:
- Hono → FastAPI / AsyncIO.
- Drizzle ORM → SQLAlchemy / SQLModel / SQLite.
- Pętla nieblokująca i stany (`waiting` / `deliverResult`) są łatwe do odwzorowania za pomocą klasycznej pętli async w Pythonie lub kolejki zadań background.
- Pruning i skracanie tool outputs w Pythonie wymagają jedynie pomocniczych funkcji liczników tokenów (np. `tiktoken` lub szacowanie heurystyczne).

### Kompatybilność z `aid4u`
- **Konflikty / Braki**: `aid4u` posiada moduł `core/llm` bazujący na adapterach LLM. Dema używają OpenAI Responses API i Gemini Interactions API bezpośrednio. Przy adaptacji należy wykorzystać istniejącą klasę `LLMClient` z `aid4u`.
- **Spójność**: Mechanizmy przycinania kontekstu (Pruning) oraz asynchronicznego oczekiwania na akcje zewnętrzne doskonale wpisują się w architekturę agentową `aid4u`.

## ⚙️ Serce Algorytmu

### 1. Zarządzanie Limitami Tokenów (Pruning & Summarization)
Gdy historia konwersacji przekracza zdefiniowany próg (np. 80% okna kontekstowego):
1. **Truncation wyników narzędzi**: Jeśli pojedynczy result narzędzia przekracza `maxToolOutputChars` (np. 4000 znaków), jest przycinany od środka: `[... X characters truncated ...]`.
2. **Turn-based Pruning**: Pogrupowanie wiadomości w tury (user query -> assistant thoughts -> tool calls -> outputs). Zawsze zachowaj: Turę 0 (początkowy kontekst) oraz N najnowszych tur (`minRecentTurns`). Usuwaj najstarsze tury ze środka konwersacji, aż szacowana liczba tokenów zmieści się w budżecie.
3. **Synteza skasowanego kontekstu (Summarization)**: Usunięte tury są przekazywane do modelu LLM w celu wygenerowania podsumowania. Podsumowanie jest zapisywane w sesji i wstrzykiwane na sam początek kontekstu jako wiadomość systemowa: `[Context Summary — Earlier conversation was compacted]`.

### 2. Interaktywne Potwierdzanie i Safety Loops (Human-in-the-Loop)
Wykonywanie akcji wrażliwych (np. `send_email`) podlega kontroli:
1. **Wykrycie narzędzia krytycznego**: Agent rozpoznaje wywołanie narzędzia z grupy `TOOLS_REQUIRING_CONFIRMATION`.
2. **Sprawdzenie sesyjnej listy zaufanych (`trustedTools`)**: Jeśli narzędzie zostało wcześniej zatwierdzone z flagą `[T]rust` w tej sesji -> Auto-approval.
3. **Prezentacja UI i pauza (Human-in-the-Loop)**: Wyświetlenie sformatowanej ramki z parametrami (Odbiorca, Temat, Treść e-maila). Opcje dla użytkownika:
   - `[Y] Send` -> Jednorazowa zgoda, kontynuacja pętli.
   - `[T] Trust` -> Zgoda + dodanie narzędzia do `trustedTools` dla danej sesji.
   - `[N] Cancel` -> Odrzucenie, zwrócenie do agenta błędu `"User rejected the action"`.
4. **Weryfikacja Białej Listy (Whitelist Enforcement)**: Przed wysyłką następuje sprawdzanie adresu w `workspace/whitelist.json`. Obsługa dokładnych adresów (`user@domain.com`) oraz reguł domenowych (`@domain.com`).

### 3. Nieblokujący Agent & Rekurencyjna Delegacja (Sub-Agents & Waiting State)
1. **Stan "Waiting" dla wywołań asynchronicznych**: Gdy agent napotka wywołanie narzędzia zewnętrznego lub pod-agenta, przechodzi ze stanu `running` w stan `waiting`. Serwer HTTP natychmiast zwraca `202 Accepted` z obiektem `waitingFor`.
2. **Dedykowany endpoint dostarczania wyników (`deliverResult`)**: Po zakończeniu zewnętrznej akcji klient wysyła `POST /api/chat/agents/:id/deliver`. Wynik jest dopisywany do historii agenta, stan zmienia się na `running`, a pętla agenta jest wznawiana.
3. **Pod-agenci (Sub-agent Delegation)**: Wywołanie narzędzia `delegate(agent, task)` tworzy instancję dziecka z poziomem `depth + 1` (max depth = 5). Po zakończeniu dziecka wynik jest automatycznie przekazywany w górę do agenta rodzica.

## 📐 Architektura (Mermaid)

```mermaid
graph TD
    Client["Użytkownik / API Client"] -->|POST /api/chat/completions| AgentRunner["Agent Runner (Agentic Loop)"]
    
    subgraph Context_Management ["Zarządzanie Kontekstem"]
        AgentRunner -->|Check Token Budget| NeedsPruning{"Czy przekroczono budżet?"}
        NeedsPruning -->|Tak| Truncate["1. Truncate Tool Outputs"]
        Truncate --> DropTurns["2. Drop Middle Turns"]
        DropTurns --> Summarize["3. Generate LLM Summary & Inject"]
        Summarize --> LLMCall["LLM Inference Call"]
        NeedsPruning -->|Nie| LLMCall
    end

    subgraph Tool_Execution ["Obsługa Wywołań Narzędzi"]
        LLMCall -->|Function Call Output| ToolRouter{"Typ Narzędzia?"}
        
        ToolRouter -->|Sync / MCP Tool| MCP["MCP / Native Tool Execution"]
        MCP -->|Result| AgentRunner

        ToolRouter -->|Sub-Agent Delegate| ChildAgent["Spawn Child Agent (Depth + 1)"]
        ChildAgent -->|Recursive Run| AgentRunner
        
        ToolRouter -->|Sensitive Action e.g. send_email| SafetyLoop{"Human-in-the-Loop / Whitelist"}
        
        SafetyLoop -->|Check Whitelist| WhitelistCheck{"Adres na Białej Liście?"}
        WhitelistCheck -->|Nie| RejectError["Błąd: Address Blocked"] --> AgentRunner
        WhitelistCheck -->|Tak| TrustCheck{"W liście trustedTools?"}
        
        TrustCheck -->|Nie| PromptUser["Wyświetl UI Potwierdzenia (Y/T/N)"]
        PromptUser -->|User Approved Y/T| ExecAction["Execute send_email"] --> AgentRunner
        PromptUser -->|User Rejected N| RejectUser["Błąd: User Rejected"] --> AgentRunner
        TrustCheck -->|Tak (Auto-approve)| ExecAction
    end
```

## 🔗 Powiązania i Zastosowania
- **Przydatność dla zadań kursowych**:
  - Koncepcja **Pruningu kontekstu i podsumowywania** jest niezbędna przy długich konwersacjach oraz zadaniach przetwarzających duże pliki lub ograniczone okna kontekstowe.
  - **Human-in-the-Loop i Lista Zaufania** przydają się w zadaniach wymagających bezpiecznej interakcji z zewnętrznymi API (np. e-mail, płatności, modyfikacja baz danych).
  - **Maszyna stanów `waiting` i `deliverResult`** stanowi fundament architektury agentowej reagującej na zdarzenia asynchroniczne i hooki.
- **Powiązane dema**:
  - `01_01_*` / `01_04_*`: Podstawowe interakcje z LLM oraz protokół MCP.
