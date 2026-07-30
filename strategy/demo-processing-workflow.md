# Workflow przetwarzania kodu referencyjnego z 4th-devs

Zgodnie z protokołem, przed rozwiązaniem trudnego zadania z AI Devs 4, konsultujemy istnienie implementacji lub demo w repozytorium **4th-devs** (lub pokrewnych notatkach z kursu, np. NotebookLM). Kod ten jest zazwyczaj pisany w języku TypeScript i używa frameworków JS/Node (np. `bun`, biblioteki LangChain, itp.).

Celem tego protokołu jest systematyczne przetworzenie archiwów TS do "łatwych do strawienia" dokumentów projektowych w formacie Markdown (zgodnych z Obsidianem), po to, aby podczas pisania kodu w Pythonie (`aid4u`) polegać na wydestylowanej logice z kart, a nie na ręcznym analizowaniu tysięcy linii TS za każdym razem.

## Architektura Procesu:
1.  **Główny Wykonawca**: Gemini Pro 3.x zintegrowany z środowiskiem Antigravity na koncie Google One AI Pro (duży limit kontekstu, zdolność sprawnego czytania całych drzew katalogowych).
2.  **Źródło (Source)**: Podkatalogi w `4th-devs-fork` na lokalnym dysku.
3.  **Docelowy Zapis (Sink)**: Folder Obsidiana `/home/lis/Dokumenty/obsidian/vaults/AID4U-era/30_Projects/02_4th-Devs`.
4.  **Format Danych**: Ustrukturyzowane obiekty zapisane za pomocą "YAML Frontmatter". Krawędzie grafu są zapisywane jako lista obiektów typu `{to: "...", type: "..."}`. Umożliwia to renderowanie grafów przez wtyczkę Dataview bez zaburzania struktury parserów.

## Kroki dla Agenta Przetwarzającego (AI)
1.  **Identyfikacja katalogu z demo**. Określ jaki wzorzec jest realizowany (np. asynchroniczny agent, generowanie audio, vector search).
2.  **Ocena kompatybilności technologicznej**. Agent analizuje, jakie narzędzia Node zostały wykorzystane i podaje ich natywne odpowiedniki w Python (np. `zod` -> `Pydantic`, `bun sqlite` -> `sqlite3 / SQLAlchemy`). Ocenia na ile trudno to przypisać pod Pythona.
3.  **Wydobycie kluczowych punktów "Serce Algorytmu"**. Pozbywamy się boilerplate'u z Typescripta. Agent wyciąga najważniejszy wniosek: "To demo działa tak: pobiera dokument -> rozdziela po tokenach -> wrzuca do FAISS z flagą X". 
4.  **Generacja diagramów Mermaid**. Zobrazowanie współpracy klas.
5.  **Generacja YAML i mapowanie relacji**. Agent sprawdza czy obecne demo korzysta z logiki zadeklarowanej w starszym demo. Zapisuje tę krawędź do tablicy `edges:` we frontmatter.
6.  **Zapis pliku na dysku** według konwencji: `s0Xe0Y-nazwa_dema-karta-projektu.md`.

W ten sposób z repozytorium kodu powstaje zintegrowana z Obsidianem, przeszukiwalna, grafowa baza wiedzy, służąca agentom piszącym kod w `aid4u` jako natychmiastowe wsparcie w trybie *Efficiency Mode*.
