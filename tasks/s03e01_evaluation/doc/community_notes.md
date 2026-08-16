# s03e01 (evaluation) — destylat z komentarzy kursu

Źródło: `tasks/s03/requirements/source/community-intel.md` (linie 20-38, 186-197) +
`source/tool-inventory.md` (linie 12, 28, 31, 74, 82-89). Poniżej tylko sygnał
operacyjny, nie cały wywód — pełny kontekst w plikach źródłowych.

## Pułapka pojęciowa (najczęstsza pomyłka w komentarzach)

Reguły anomalii #2 i #3 ("operator mówi OK, dane złe" / "operator zgłasza błąd, dane
dobre") są **niezależne** od reguły #1 (dane poza normą). Plik z idealnymi odczytami,
ale notatką o awarii, **też jest anomalią**. Ludzie odruchowo sprawdzają tylko liczby
i przegapiają tę regułę.

## Punkty kontrolne (liczby do porównania z własnym wynikiem)

- ~**46 plików** wypada z checków deterministycznych (progi + reguła "sensor zwraca
  pole którego nie powinien").
- Tylko ~**6 więcej** dochodzi z klasyfikacji notatek (rules #2/#3).
- Jeśli LLM zwraca setki — prompt za luźny (klasyfikuje zbyt agresywnie).
- Jeśli wychodzi **dokładnie 22 albo 43** — filtr deterministyczny jest zepsuty (dwa
  znane, nazwane tryby awarii z komentarzy — nie "prawie dobrze").

## Cost-optimization — cała jego treść w trzech liczbach

~9953 notatek → ~2000 unikalnych → **~261 unikalnych fraz** po rozbiciu na przecinkach.
Dedup + mapowanie indeksów to cały cost-optimization tego zadania — LLM klasyfikuje
tylko te ~261 fraz, nigdy pojedyncze pliki czy nawet pojedyncze notatki.

## Batching

Batche po **50–200 notatek/fraz**, model zwraca **same indeksy**, nie treść. Wysyłanie
surowych batchy 500+ powoduje timeouty/puste odpowiedzi. Degradacja długiego kontekstu
potwierdzona od ~40–50% okna kontekstowego — kolejny argument za małymi batchami.

## Operacyjne

- ID plików liczone **od 1**, nie od 0.
- Zły host → `-166 task not found: evaluation` (poprawny host w tej edycji:
  `hub.ag3nts.org`).
- `-500` → retry (przejściowy błąd serwera).
- Budżet konsensusu: **< 2 centy**. Więcej ⇒ podejście jest złe (za duże batche, za
  drogi model, brak dedup), nie zadanie trudne.

## Dane pobierane przez `get_public()`

`/dane/sensors.zip` — dodane przy okazji `s02e05_drone`
(`core/hub/client.py:186`, `core/AGENTS.md`). `zipfile` ze stdlib wystarcza.

## Cross-cutting: to jest zadanie o observability/eval z premedytacji

Lekcja S03E01 nazywa się "Obserwowanie i ewaluacja" i to zadanie jest jej praktycznym
ćwiczeniem — teza kursu: "wyniki są niepowtarzalne między ludźmi... traktuj wybór
modelu jak eksperyment". To jest wprost uzasadnienie dla A/B (Haiku vs Gemini Flash)
zamiast zgadywania, który model wybrać — patrz `AGENTS.md` tego folderu, sekcja o
wyniku eksperymentu.
