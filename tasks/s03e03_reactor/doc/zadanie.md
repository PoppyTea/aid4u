## Zadanie

Twoim zadaniem jest doprowadzenie robota transportującego urządzenie chłodzące w
pobliże reaktora. Do sterowania robotem służy specjalnie przygotowane API, które
przyjmuje polecenia: `start`, `reset`, `left`, `wait` oraz `right`. Możesz wysłać
tylko jedno polecenie jednocześnie. Zadanie uznajemy za zaliczone, jeśli robot
przejdzie przez całą mapę, nie będąc przy tym zgniecionym przez elementy reaktora.
Bloczki reaktora poruszają się w górę i w dół, a status ich aktualnego kierunku,
podobnie jak ich pozycja są zwracane przez API.

Napisz aplikację, która na podstawie aktualnej sytuacji na planszy będzie
decydowała, jakie kroki powinien podjąć robot. Aby uprzyjemnić Ci pracę,
przygotowaliśmy też graficzny podgląd sytuacji wewnątrz reaktora.

Podgląd sytuacji w reaktorze: https://hub.ag3nts.org/reactor_preview.html

Zadanie nazywa się: **reactor**

Komendy dla robota wysyłasz do **/verify**:

### Mechanika zadania

- Plansza ma wymiary 7 na 5 pól.
- Robot porusza się zawsze po najniższej kondygnacji, czyli jego pozycja startowa
  to pierwsza kolumna i 5 wiersz.
- Miejsce instalacji modułu chłodzenia (Twój punkt docelowy) to 7 kolumna i 5 wiersz
  (dobrze widać to na podglądzie graficznym podlinkowanym wyżej).
- Każdy blok reaktora zajmuje dokładnie 2 pola i porusza się cyklicznie góra/dół.
  Gdy dojdzie do pozycji skrajnie wysokiej, zaczyna wracać na dół, a gdy osiągnie
  pozycję najniższą, wraca do góry.
- Bloki poruszają się tylko, gdy wydajesz polecenia. Oznacza to, że odczekanie np.
  10 sekund nie zmieni niczego na planszy. Jeśli chcesz, aby stan planszy zmienił
  się bez poruszania robotem, wyślij komendę `wait`.

### Oznaczenia na mapie

- `P` — to pozycja startowa
- `G` — to pozycja do której masz doprowadzić robota
- `B` — to bloki reaktora
- `.` — to puste pola. Nic się na nich nie znajduje (to kropka)

### Jak powinna wyglądać implementacja Twojego algorytmu?

1. Na początek zawsze wysyłasz polecenie `start`
2. Rozglądasz się, jak wygląda plansza i podejmujesz decyzję, czy możesz wykonać
   krok do przodu
3. Jeśli nie możesz wykonać kroku lub jest to zbyt niebezpieczne (np. zbliża się
   bloczek), to czekasz
4. Jeśli czekanie nie wchodzi w grę (bo w kolumnie, w której stoisz, też zbliża się
   bloczek), to uciekasz w lewo
5. Wykonujesz odpowiednie kroki za każdym razem podglądając mapę, tak długo, aż
   osiągniesz punkt docelowy

---

### Format API — USTALONY EMPIRYCZNIE, nie z treści zadania

Treść lekcji (powyżej, cytowana 1:1 przez NotebookLM) **nie podaje** żadnego
przykładu JSON ani formatu odpowiedzi — potwierdzone dwukrotnym zapytaniem do
NotebookLM. Poniższe zmierzono sondą (`scripts/probe_api.py`,
`data/input/s03e03_reactor/`, 2026-08-17):

- `POST /verify` body: `{"apikey": "...", "task": "reactor", "answer": {"command": "start"}}`
  — **`answer` musi być obiektem `{"command": ...}`**, nie gołym stringiem (hub
  zwraca `code: -21`/`-22`/`-990` na inne warianty).
- Odpowiedź: `{"code", "message", "board": [[...]×5], "player": {"col","row"},
  "goal": {"col","row"}, "blocks": [{"col","top_row","bottom_row","direction"}],
  "reached_goal": bool}`. `board` jest 5×7 (wiersz×kolumna), 1-indeksowane
  `col`/`row` w polach `player`/`goal`/`blocks`.
- Zgniecenie: HTTP 409, `{"code": -920, "message": "Robot was crushed :("}`.
- **Kolizja sprawdzana PO przesunięciu bloków, nie przed** — potwierdzone
  eksperymentalnie w obie strony (ruch w kolumnę pustą-teraz-ale-zajętą-po-ticku
  = zgniecenie; ruch w kolumnę zajętą-teraz-ale-pustą-po-ticku = sukces). Pełny
  opis modelu fizyki: docstring `reactor.py`.
