# s02e04_mailbox Module

## Purpose
Przeszukanie aktywnej skrzynki mailowej operatora systemowego (API `zmail`) w
poszukiwaniu wiadomości od donosiciela "Wiktora" (domena `proton.me`), żeby
wydobyć trzy wartości: `date` (data planowanego ataku), `password` (hasło do
systemu pracowniczego), `confirmation_code` (format `SEC-` + 32 znaki = 36 razem).

## Ownership
- `solution.py`: (do utworzenia) klasa zarejestrowana przez
  `@task("s02e04", hub_name="mailbox")`.
- Dane wejściowe: **żywe, nie statyczny plik** — `POST /api/zmail` przez
  `hub.post_api()` (już generyczna metoda w `HubClient`, nic nowego do dodania).
  Skrzynka jest cały czas w użyciu — nowe maile mogą wpływać w trakcie pracy, więc
  brak wyniku nie znaczy że informacji nie ma (spróbować ponownie).
- `doc/`: treść zadania — materiał referencyjny, nieużywany w runtime.

## Local Contracts
- Dokładny protokół `zmail` (akcje dostępne, kształt search/get-by-content) jest
  nieznany — trzeba go odkryć przez akcję `help` na start, analogicznie do
  `s01e05_railway`, zanim da się zaimplementować `solve()`.
- (reszta — uzupełnić po zaimplementowaniu `solution.py`)

## Work Guidance
- Wskazówka źródłowa: podejście agentowe z function calling (szukaj → czytaj →
  wyciągaj wnioski → szukaj dalej) pasuje tu lepiej niż sztywny skrypt. Tańszy
  model (np. `google/gemini-3-flash-preview`) wystarcza — zadanie to ekstrakcja
  faktów, nie złożone rozumowanie.

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
