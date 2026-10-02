# Sekretne flagi — czym są i jak się ich szuka

## Purpose
Metoda polowania na flagi sekretne. Sama **polityka** (są poza priorytetem do 20 flag,
zapis pod `sXXeYY_secret`) jest kontraktem i żyje w rootowym `AGENTS.md`, zasada 7 —
tutaj jest to, czego kontrakt nie powinien nieść: sposób postępowania i przykłady.

## Ownership
Kurs AI_Devs 4. **Które flagi sekretne są zdobyte, mówi `.flags.json`** (klucze
`sXXeYY_secret`) i `run.py status` — nie ten plik. Tutaj jest metoda, nie licznik.

## Czym są
Ten sam format `{FLG:...}` co flagi główne, ale zdobywane nieoczywistą, ukrytą drogą,
poza główną ścieżką zadania. Odblokowują dodatkowe materiały edukacyjne. **Nie liczą się
do 20 flag potrzebnych do certyfikatu** — `run.py status` je rozdziela.

## Zasada naczelna
Droga do sekretu **bardzo często prowadzi przez eksplorację, która pomija zwykły cel
zadania, a bywa że wprost łamie jego zasady.**

Z tego wynika reguła operacyjna: **jeśli masz hipotezę pasującą do wskazówki, sprawdź
ją** — nawet gdy łamie zasady zadania albo wymaga nieistniejących elementów. Koszt
sprawdzenia to jedno zgłoszenie; koszt odrzucenia jej „bo się nie da" to cały wątek
w ślepą uliczkę.

## Trzy odruchy do złamania

**„Muszę zrobić jedno i drugie."** Zwykle nie. W `s03e05` trasa po flagę sekretną
**nie dochodzi do celu** — hub przyjmuje ją mimo `does not reach the goal` dla misji
głównej. Połączenie obu było zresztą matematycznie niemożliwe: 17 ruchów przy suficie 12.

**„To łamie reguły zadania, więc nie zadziała."** W zadaniu S02 z robotem magazynowym
(prompt systemowy + wiadomość) sekret dawało wysłanie **samego kodu Konami**, całkowicie
ignorując ściany i kolizje. Rozwiązanie „zgodne z duchem" — objazd na taniec ORAZ dojazd
do celu, zmieszczony w limitach — działało technicznie i **nie dawało nic**.

**„Brakuje wymaganego elementu, więc to nie ta droga."** Ten sam Konami wymaga przycisków
A i B, których robot **nie miał**. Ten brak też należało zignorować.

## Gdzie szukać
- **Podgląd zadania po stronie huba.** W `s03e05` plik `savethem_preview.html` zdradzał
  legendę terenu, nazwy pojazdów ORAZ istnienie sekretu (`beaver_spot`, `beaver_flag`) —
  wszystko przed pierwszym uruchomieniem.
- **Rozbieżności w indeksowaniu.** Tam samo: backend liczył od 1, mapa od 0, więc
  `beaver_spot (2,7)` oznaczał `(1,6)` w tablicy. Dwie próby spaliły się wyłącznie na tym.
- **Komentarze społeczności** — sekret bywa wspominany bez zdradzania mechanizmu; sama
  informacja „tu jest sekret" wystarcza, żeby wiedzieć, że warto szukać.

## Work Guidance
- **Flaga główna najpierw.** Nie zatrzymuj się na polowanie, jeśli główna jest w zasięgu.
- Nie projektuj rozwiązania pod sekret. Jeśli wpada po drodze za darmo — bierzemy.
- Po zdobyciu sekretu przywróć stan misji głównej, jeśli zgłoszenie go nadpisało.

## Verification
- Flagi sekretne w `.flags.json` pod kluczem `sXXeYY_secret`; `run.py status` pokazuje je
  osobno i poza licznikiem.

## Child DOX Index
- None.
