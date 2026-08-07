# s02e04 (mailbox) — destylat z komentarzy kursu

Źródło: `aid4u-private/00-materialy-z-kursu/12_komentarze-do-lekcje-zadania/md/s02e04_aid4u_comments.md`
(oryginał nieprzetrzebiony, ~1050 linii). Poniżej tylko sygnał, nie cały wywód.

## Protokół `zmail` — akcje potwierdzone przez społeczność

Odkryte przez różne rozwiązania (nadal odkryj live przez `help`, to tylko punkt startowy):
`help`, `getInbox`, `search` (parametr `query`, np. `{"action":"search","query":"from:proton.me"}`),
plus czytanie pełnej treści pojedynczej wiadomości po ID (dokładna nazwa akcji nieznana z
komentarzy — różni ludzie nazywali ją różnie: `getThread`, `getMessages`, `getMessage`;
ustalić z odpowiedzi `help`).

**Składnia wyszukiwania** — jak Gmail (`from:`, `to:`, `subject:`, `AND`, `OR`), ale
**BEZ nawiasów i BEZ wildcardów/glob** (`*`) — potwierdzone wprost przez organizatora kursu po
pytaniu uczestnika, który próbował `from:proton.me (atak OR planowanie)`. Budować proste,
płaskie zapytania.

## Skąd biorą się poszukiwane wartości

- Mail od Wiktora (`from:proton.me`) zawiera informacje o planowanym ataku (→ `date`).
- `password` i `confirmation_code` mogą siedzieć w **innych** wątkach/nadawcach niż Wiktor
  (np. wewnętrzny mail o haśle do systemu pracowniczego, osobny ticket działu bezpieczeństwa) —
  nie ograniczać całego przeszukiwania do `from:proton.me`, trzeba przeszukać szerzej.

## Feedback z huba — co naprawdę mówi

- Błędna odpowiedź → `{"code": -970, "message": "Invalid answer payload"}` (zły format/długość
  pola, najczęściej `confirmation_code` != 36 znaków) albo `{"code": -960, ...}` (wartości
  merytorycznie niepoprawne).
- **Hub NIE mówi, które konkretnie pole jest złe** — trzeba mieć wszystkie trzy poprawne naraz,
  zanim przyjdzie flaga. Potwierdzone wielokrotnie (kilka osób utknęło dokładnie na tym
  nieporozumieniu).
- `confirmation_code`: prefiks `SEC-` + 32 znaki = **36 znaków łącznie** (treść zadania to
  podaje explicite; jeden komentarz podał błędnie "28 chars = 32 total" we własnym
  system-prompcie — nie ufać temu, ufać oficjalnej treści zadania).

## Skrzynka jest żywa — realne konsekwencje

- Potwierdzone wielokrotnie: stary/błędny mail (np. z niepoprawnym kodem) może zniknąć, a nowy
  (z poprawką) wpłynąć w trakcie pracy — jeśli czegoś brakuje po pełnym przeszukaniu, spróbować
  ponownie zamiast zakładać że info nie istnieje.
- Zadanie bywało też aktualizowane w treści w trakcie trwania kursu (jeden uczestnik zgłosił, że
  po 15 próbach okazało się, że treść zadania się zmieniła) — jeśli coś nie zgadza się z lokalną
  kopią `doc/zadanie.md`, zweryfikować `help`/`getInbox` live, nie ufać ślepo statycznej kopii.

## Modele i koszt

- Rekomendacja z lekcji: `google/gemini-3-flash-preview` — tanio, zadanie to ekstrakcja faktów
  z tekstu, nie złożone rozumowanie; wielu uczestników potwierdziło że tańsze/mniejsze modele
  (gpt-4o-mini, gemini flash, nawet lokalne 8-9B) radzą sobie w 9-20 iteracjach.
  OpenAI-rodzina (4o, gpt-5 warianty) wypadała u części ludzi gorzej/wolniej niż Gemini na tym
  konkretnym zadaniu (spekulacja: gorsze dotrenowanie na Gmail-owej składni wyszukiwania).
- Koszt orientacyjny: powinno zamknąć się wyraźnie poniżej $1, typowo $0.10–$0.25. Jedna osoba
  zgłosiła $2.5 (Sonnet jako główny model) i dostała feedback, że to "zdecydowanie za dużo" —
  sygnał, żeby nie sięgać od razu po najdroższy model w drabinie.
- Architektura, która się sprawdziła wielokrotnie: prosta pętla agentowa z 2 narzędziami
  (interakcja z API + wysyłka do huba) w 9-15 krokach — nie trzeba komplikować orchestratorem
  wieloagentowym, choć kilka osób to zrobiło (sub-agent per pole) i też zadziałało.

## Pułapki, które kosztowały ludziom czas

- Ślepe poleganie na samym temacie maila zamiast pobrania pełnej treści (task doc już to
  ostrzega explicite — potwierdzone jako realny błąd w praktyce).
- Wysyłka `answer` z pustymi stringami "żeby zobaczyć strukturę błędu" — hub odpowiada tym samym
  `-970` co przy złym formacie, myląco sugerując że to problem ze schematem payloadu, a nie
  brakiem wartości.
- Zbyt wąskie zapytania na starcie (samo `from:proton.me`) pomijające maile z hasłem/kodem w
  innych wątkach — patrz sekcja wyżej.
