# S04+S05 — intel społeczności kursu (materiał źródłowy)

Destylat z ~9 800 linii komentarzy
(`aid4u-private/00-materialy-z-kursu/12_komentarze-do-lekcje-zadania/md/s0[45]e0*_aid4u_comments.md`),
zebrany 2026-08-20. Cytaty są dosłowne, ze wskazaniem pliku i numeru linii — nie streszczam
tam, gdzie mam oryginał.

## Faktyczna trudność i koszt (zgłoszenia uczestników)

| Ep | Trudność | Realny koszt | Zdanie podsumowujące |
|---|---|---|---|
| s05e03 `shellaccess` | 🟢 **najłatwiejsze** | $0.00 – $0.11 | odpowiedź da się wypisać `echo`-em; robiły to modele 14B |
| s04e05 `foodwarehouse` | 🟢 łatwe | $0.04 – $0.05 / „kilka centów" | „poszło od strzała"; agent tu „sztuką dla sztuki" |
| s04e03 `domatowo` | 🟢 łatwe-średnie | $0.0003 – $0.00 | „nie jest zbyt trudne. Złożone, ale nie przekombinowane" |
| s04e04 `filesystem` | 🟡 średnie | $0.15 – $0.26 | dane 2,6 kB, ale polska semantyka rozkłada małe modele |
| s05e04 `goingthere` | 🟡 średnie, **jedna pułapka pojęciowa** | grosze | wszyscy rozbijają się o TEN SAM błąd modelu ruchu |
| s04e01 `okoeditor` | 🟡 średnie, **milcząca weryfikacja** | $0.08 – $0.14 | „spędziłem na tym ze 2 dni"; `update` OK, `done` mimo to odrzuca |
| s05e05 `timetravel` | 🔴 trudne (bez obejścia) | do **$5 za jedno podejście** | „dla mnie najtrudniejsze zadanie" |
| s04e02 `windpower` | 🔴 **najtrudniejsze inżyniersko** | $0.00 – $0.04 | limit 40 s; „po 8 godzinach prób poddaję się" |
| s05e01 `radiomonitoring` | 🔴 trudne + wymaga vision/audio | $0.009 – $0.50, u jednej osoby +300k tokenów | „modeli wspierających i audio, i video jest naprawdę mało" |
| s05e02 `phonecall` | 🔴🔴 **rage-quit sezonu** | **$5 / 5 h**, „12 godzin" ×2 | „zadanie typu »przepal tokeny«… walidator działa raz tak raz siak" |

Uwaga metodologiczna: koszt to tu **mediana zgłoszeń**, nie nasza prognoza. Nasze
rozwiązania S03 wychodziły systematycznie taniej niż mediana społeczności, bo szły
deterministycznie — te same widełki należy czytać jako sufit, nie cel.

---

## s04e01 `okoeditor` — 3 edycje + `done`

**Mechanika (z dumpu `help`, `s04e01_aid4u_comments.md:396-450`):** API wystawia
**tylko trzy akcje**: `help`, `update`, `done`. `update` przyjmuje
`page ∈ {incydenty, notatki, zadania}`, `id` (32-znakowy hex), opcjonalnie
`content`/`title`/`done`. Reguły z `help`:
> `"At least one of \"content\" or \"title\" must be provided."`
> `"\"done\" is allowed only for page \"zadania\"."`
> `"Page \"uzytkownicy\" is read-only and cannot be updated."`

**Konsekwencja: nie ma akcji tworzącej wpis.** Punkt „spraw, aby na liście incydentów
pojawił się raport o Komarowie" realizuje się przez przerobienie istniejącego wpisu.

**Dane czyta się z panelu WWW, nie z API.** Logowanie to zwykły formularz + ciasteczko
sesyjne (`:111`, `:114-171`):
> „strzelam żądaniem do logowania, logowanie jest udane, wyciągam z nagłówka »Set-Cookie«
> id sesji… przy próbie pobrania strony np. notatki ustawiam ciasteczko »oko_session«"

Staff potwierdza, że przeglądarka nie jest potrzebna (`:341`):
> „Tak, część rzeczy musisz pobrać z interfejsu webowego. Nie musisz od razu playwright,
> możesz pobrać html i wyciąć tagi, header, scripts itd"

**Pułapki:**
- **Kod ticketu.** Wielokrotny błąd (`:356`, `:641`):
  > `{"code": -720, "message": "Incorrect ticket code for Skolwin - Is the word "Skolwin" in the title there?"}`

  Wyjaśnienie od uczestnika (`:278`):
  > „w notatkach na stronie jest wykaz numerów tiecketów jakie powinny być przypisane dla
  > poszczególnych rodzajów incydentów — zakładam że Twój agent tego nie przeczytał"

  Czyli: strona `notatki` zawiera tabelę mapującą typ incydentu → prefiks (`MOVE03`,
  `MOVE04`…), a nazwa miasta musi zostać w tytule.
- **Milcząca weryfikacja.** Wszystkie trzy `update` zwracają `code:110 "Entry updated
  successfully."`, a `done` i tak odrzuca — kilka osób siedziało nad tym godzinami
  (`:1075`, `:1081`, `:795`). Nie ma feedbacku, który warunek nie przeszedł.
- **Debug huba jest ratunkiem** (`:278`): panel debug na `hub.ag3nts.org` pokazuje, co
  faktycznie doszło.

**Zero-LLM potwierdzone** (`:723`):
> „Kurcze, zrobiłam zadanie ale bez llm'a i mam dyskomfort :D czy aby to było uczciwe?"

i (`:326`):
> „Choć do scrapowania nie użyłam modelu, bo stwierdziłam, że nie ufam"

**Koszty agentowe:** `qwen3.6` — 16 kroków, $0.08; `gemini3.1` — 9 kroków, $0.14 (`:58`).

---

## s04e02 `windpower` — 40 sekund

**Najtwardsze ograniczenie w obu sezonach.** Zadanie samo ostrzega: „Liniowe wykonywanie
wszystkich akcji nie umożliwi Ci ukończenia zadania".

**Kluczowe zdanie całego rekonesansu** (`s04e02_aid4u_comments.md:116`):
> „Zadanie w którym użycie LLM jest dość naciągane… **Bez LLM zadanie pękło w 26 sekund.**"

potwierdzone niezależnie (`:128`):
> „26.3s — ale bez llm, skryptem"

i (`:101`, odpowiedź na pytanie „jak zejść poniżej 30 s?"):
> „takie szybkie to są rozwiązania programistycznie — bez LLM :D"

**Konkretne parametry rozwiązania** — staff w odpowiedzi na zgłoszony „bug" (`:549`):
> „3 stormy (tyle jest w danych). Każdy timestamp z wiatrem **> 14 m/s** musi być
> zabezpieczony (idle), inaczej turbina się zepsuje (błąd -830). W tych danych są dokładnie
> 3 takie momenty: 04-03 18:00 → 25 m/s, 04-06 18:00 → 22 m/s, 04-07 18:00 → 28 m/s.
> 1 production"

Stąd komunikat `{'code': -860, 'message': 'Invalid configuration set. Exactly 4 config
points are required.'}` (`:155`) — **4 = 3 storm-idle + 1 production**. ⚠️ Daty są z edycji
kursu (kwiecień 2026); w żywych danych mogą być inne — patrz lista weryfikacji.

**Co ludzie skracali czas na czym** (`:89`, `:341`):
> „Kluczowe rzeczy które pomogły: Cache danych statycznych (help, dokumentacja) **poza
> sesją** — zero straconego czasu w oknie 40s; Równoległe odpytywanie API"
> „turbinecheck równoległy zaoszczędził ~12s, deterministyczna analiza zaoszczędziła ~10
> kroków agenta LLM. Z 77s timeout zeszliśmy do 28s."

`turbinecheck` można (i trzeba) wywołać **przed** wysłaniem configu, mimo że treść zadania
sugeruje kolejność odwrotną (`:170`).

**Cena wejścia w wariancie agentowym** (`:303`):
> „Po 8 godzinach prób poddaje się. […] jakim cudem ludzie schodzą poniżej 35 sekund jeżeli
> samo pobranie pogody to 25s a pobranie turbiny 11s?"

i (`:26`):
> „Ewidentnie najtrudniejsze zadanie… dziś mija dokładnie tydzień od 1 próby"

Restarty są darmowe (`start` otwiera nowe okno serwisowe), więc ryzyko to **czas, nie pieniądze**.

---

## s04e03 `domatowo` — mapa 11×11, 300 punktów akcji

**Ocena społeczności** (`s04e03_aid4u_comments.md:254`):
> „Fajne zadanko — Da się podejść na wiele sposobów, ale nie jest zbyt trudne. Złożone, ale
> nie przekombinowane ;)"

**Deterministycznie wychodzi najlepiej** (`:413`):
> „Tak 'deterministycznie' szło u mnie też najlepiej, Agent czasem wysyłał w losowe miejsca."

Twarde liczby z porównania trzech wariantów przez jedną osobę (`:504-520`):
- misja deterministyczna: 249/300 punktów zostało
- misja LLM (`gpt-4o-mini`): 256/300 zostało, **koszt $0.000273**
- misja lokalna (`qwen3.5-9b`): 126/300 zostało, koszt $0

**Jedyny realny sposób przegrania** (`:314`):
> „Łatwo przepalić 300 punktów, jeśli np. agent zasuwa jednym zwiadowcą na piechotę i nie
> zapamiętuje już sprawdzonych lokalizacji :P"

Ruch zwiadowcy pieszo = 7 pkt/pole, transporterem = 1 pkt/pole. Cała optymalizacja to:
dowieźć transporterem, wysadzić (0 pkt), inspekcjonować (1 pkt).

**Wskazówka z przechwyconego sygnału** (treść zadania): „Ukryłem się w jednym z
**najwyższych bloków**" — zawęża przeszukiwanie do konkretnego typu terenu, zanim
cokolwiek wyślemy w teren. Jeden uczestnik użył k-means do klastrowania celów (`:218`),
co jest już przesadą przy 121 polach.

⚠️ **$7 z pierwszego komentarza** (`:5`) to **nie** koszt zadania głównego — ta osoba
goniła flagę sekretną (hex-zakodowana zagadka Vigenère'a w logach `inspect`).

---

## s04e04 `filesystem` — notatki Natana → struktura katalogów

**Dane: 2 620 bajtów.** Cały korpus mieści się w jednym promptcie.

**Trudność jest lingwistyczna, nie techniczna** (`s04e04_aid4u_comments.md:184`):
> „Wczoraj je rozwiązywałem na kilka sposobów z lokalnymi modelami nawet **bielik** wleciał
> bo Polska semantyka była trudna dla innych modeli. Niestety żaden nie poradził sobie…
> **Gemini 3 flash wykonał za pierwszym razem.**"

potwierdzone (`:232`, `:235`):
> „przejechałem chyba 6 lokalnych modeli nawet bielika bo najlepiej radzi sobie z polskim i
> nic. Gemini 3 flash za 1 podejściem rozpykał zadanie."
> „o ile radziły sobie z czystą gramatyką to gubiły się w znaczeniu tych notatek"

**Pułapka formatu** (`:364`):
> `400 Bad Request: {"code": -789, "message": "Each li…` — walidacja linków markdown
> wewnątrz plików `/towary`

**Koszty:** $0.26 na `gemini-3-flash` za jednym promptem (`:47`); 15-20 centów per run przy
podejściu wieloagentowym (`:214`); `Qwen3.5-27B` dał radę (`:385`), `Qwen3.5` nie (`:412`).

**Bezpiecznik:** akcja `reset` czyści cały FS, więc błędna próba nie kosztuje nic poza
tokenami. `batch_mode` pozwala zbudować całą strukturę **jednym requestem**.

---

## s04e05 `foodwarehouse` — SQLite + SHA1 + zamówienia

**Najbardziej „nasze" zadanie w S04.** Ocena uczestnika, który podszedł agentowo (`:59`):
> „Po rozpisaniu na kartce rzeczy do zrobienia i próbie wpasowania tego w system agentowy
> nieśmiało stwierdzałem, że **użycie agentów tutaj będzie sztuką dla sztuki**"

i odpowiedź z tego wątku (`:74`):
> „IMHO to używaj LLMa tam, gdzie faktycznie coś wnosi. Jeśli zadanie polega na pobraniu
> danych, przeliczeniu ich i wysłaniu, to po co wplątywać w to model?"

**Jedyna zgłoszona pułapka** (`:120`, z odpowiedzią staffu `:123`):
> „w liscie miast jest **domatowo**, a w tabeli destinations nie ma takiego miasta? Trzeba
> ją pominąć z racji ze jest zniszczone?"
> → „Jesteś pewien że wyciągasz wszystkie wiersze tabeli? **Zwróć uwagę na to co jest
> zwracane z bazy — jakie jeszcze informacje poza danymi z tabeli**"

Czyli odpowiedź `database` niesie metadane (prawdopodobnie paginację / liczbę wierszy) i
naiwny `select * from destinations` zwraca ucięty zbiór.

**Koszty i czasy z benchmarku jednej osoby** (`:327`): `GPT-5.4` — 12-18 s, ~45-50k tokenów,
**$0.04-0.05**, 10-15 tool calls. `Deepseek 3.2` — „bez problemów za kilka centów" (`:83`).
`gemini 2.5 flash` — „za pierwszym razem" (`:198`).

`reset` przywraca stan początkowy. Zamówienia można budować `append` w trybie batch.

---

## s05e01 `radiomonitoring` — strumień transkrypcji i binarek

**Wymaga zdolności, których nie mamy.** Stack, który u ludzi zadziałał (`:176`):
> „- transkrypcja: whisper-fast - OCR: gemma4:e4b - ekstrakcja faktów / odsiew szumu:
> gemma4:26b - reasoning: gemma4:26b"

i (`:29`):
> „z zadaniem poradziłem sobie przygotowując **tool do OCR**"

oraz (`:80`):
> „Bardzo ciekawe jest, że **modeli wspierających i audio, i video jest naprawdę mało**"

**Pułapka merytoryczna** (`:29`):
> „Miałem problem z określeniem liczby magazynów, bo w nagraniu jest mowa o **planowanym**
> 12 i cały czas szła taka wartość"

**Koszt:** od $0.009 (`:341`) do 50 centów (`:230`), plus jeden zgłoszony wypadek
+300k tokenów przez dwie drobne niedoróbki (`:20`). Ktoś dostał też blokadę moderacji na
analizie obrazu (`:23`, prompt injection shields).

---

## s05e02 `phonecall` — rozmowa audio z operatorem

**Najgorszy stosunek wysiłku do flagi w całym kursie.** Cytaty mówią same za siebie:

(`:375`)
> „Dołączam do grona narzekaczy na to zadanie. **Nagroda Smutnego Tokena** dla autora
> pomysłu. **Ponad 5h i $5.** Flaga zdobyta ale totalnie na pałę… Podejście agentowe nijak
> mi się tu nie sprawdzało."

(`:44`)
> „Ja to zadanie robiłem **12 godzin**. Prób wykonałem setki i sam doszedłem do wyniku."

(`:351`)
> „W końcu to zrobiłem… **Po 12 godzinach walki** uzyskałem flagę."

(`:681`)
> „to jest zadanie typu »przepal tokeny« i nic z tego więcej nie wyniesiesz bo **walidator
> działa raz tak raz siak**"

(`:678`)
> „Zostało wyłączenie kamer. **OD 5 godzin.** i szum, i różne tempo, i lokalesy, i
> elevenlabs, i openAI, masakra…"

(`:657`)
> „Zrezygnuję z tego zadania… To nie ma sensu."

**Niedeterminizm potwierdzony** (`:570`, `:495`):
> „nie chciało przejść… a później się okazało, że **audio z cache'a zaliczyło po kilku
> kolejnych próbach bez zmiany niczego**"
> „Przeszło po którejś próbie **bez zmian**."

**Dodatkowa bariera — moderacja** (`:68`):
> „model odmówił współpracy bo jak stwierdził: »nie może pomóc mi w nielegalnych operacjach
> typu **przemyt ludzi**«"

**Merytoryczna wskazówka, gdyby jednak** (`:513`, `:699`): prośba o wyłączenie monitoringu
musi w **jednej** wiadomości zawierać uzasadnienie — mimo że treść zadania mówi „Nie proś o
wiele rzeczy w ramach jednej wiadomości" (`:432`: „co to ma być za wskazówka? to zmyłka").
Co działało: ElevenLabs (`:591`), `gpt-4o-mini-tts` głos „cedar" (`:438`), `edge-tts`
(`:286`), Piper `pl_PL-mc_speech-medium` (`:501`). Co nie działało: `tts-1`/`tts-1-hd`
(angielski akcent przy „RD224"), większość lokalnych.

**Cache nagrań MP3 to jedyna sensowna oszczędność** (`:348`).

---

## s05e03 `shellaccess` — zdalny grep

**Najtańsze zadanie w obu sezonach.** Podpowiedź base64 z treści zadania mówi wprost, że
odpowiedź można po prostu **wypisać**:
> „Poprawną odpowiedź możesz wyprodukować przez JSON, albo poskładać samodzielnie i wykonać:
> `echo '{"date":"2020-01-01","city":"nazwa miasta","longitude":10.000001,"latitude":12.345678}'`
> UWAGA! Pamiętaj, że musisz zwrócić datę **DZIEŃ PRZED** znalezieniem ciała Rafała."

Serwer ma `jq` i `grep`.

**Dowód, że wystarcza mały model** (`s05e03_aid4u_comments.md:137`, `:149`, `:221`):
> „gemma4:26b na Linux też daje radę :p qwen:27b również"
> „Poszło też na **qwen/qwen3-14b** z delikatnie wzmocnionym promptem"
> „google/gemma-4-26b-a4b-it agent one shot, 69 tur, 17 minut 28 sekund, **$0.11**"

**Jedyna pułapka jest w treści, nie w kodzie** (`:206`):
> „Nie bardzo rozumiem — jak model miał wpaść sam na to żeby datę podać **dzień wcześniej**?
> w tekście nie ma nic w stylu 'wczoraj'"

(jest — w podpowiedzi base64, której wielu nie zdekodowało)

Ostrzeżenie o przeinżynierowaniu (`:374`):
> „We over-engineered it. […] gpt-5.4 postanowiło sobie rozwiązać to zadanie wywołując
> `printf '%s'`"

---

## s05e04 `goingthere` — rakieta 3×12

**Wszyscy przegrywają na tej samej rzeczy i to nie są hinty.** Sekwencja z forum:

Skarga (`s05e04_aid4u_comments.md:98`):
> „Czy wy aby dobrze zaimplementowaliście te hinty? One wsadzają na minę rakietę… 'Port is
> open, starboard is open, and the center lane is the bad choice. That stone is dead ahead.'
> — left :( "

Rozwiązanie od staffu, powtarzane pięć razy w wątku (`:101`, `:143`, `:344`, `:824`, `:917`):
> „Rakieta porusza się **najpierw w aktualnej kolumnie** (góra/dół) a potem do przodu. Więc
> jeśli w kolumnie w której jesteś jest kamień i przesuniesz się w jego kierunku, to masz
> zderzenie. Kontroluj nie tylko co przed Tobą"

i wprost (`:431`):
> „komunikaty przychodzą z 2 stron. Jeden informuje Cię gdzie jest kamień w **aktualnej**
> kolumnie, a kolejny co jest **'z przodu'** — musisz oba te komunikaty obsłużyć"

Odpowiedź `/verify` po ruchu zawiera już wszystko, czego trzeba do pierwszego źródła
(`:914`):
> `{"code":120,"message":"Move accepted.","player":{"row":2,"col":5},"currentColumn":{"column":5,"yourRow":2,"stoneRow":1,"freeRows":[2,3]}}`

**Czyli warunek bezpiecznego ruchu do wiersza `r'`:** `r' ∈ freeRows(kolumna bieżąca)`
**oraz** `r' ≠ stoneRow(kolumna następna, z hinta)` **oraz** `r' ∈ [1,3]`.
Staff potwierdza, że hinty nie kłamią (`:164`): „Nie — podpowiedzi nie kłamią."

**Losowe błędy API są zamierzone** (`:59`, `:62`):
> „By design. Wywołaj go wielokrotnie i zobacz jaki jest procent błędów — tak ma być"
> „Wykorzystaj mechanizm retry, który miałeś w poprzednich zadaniach."

Skaner potrafi zwrócić `502 Bad gateway` z pełnym HTML (`:1085`) — walidacja treści
odpowiedzi obowiązkowa, sam kod HTTP nie wystarczy.

**Deterministycznie da się**, choć z zastrzeżeniem (`:629`, `:632`):
> „Zrobiłem dwie wersje rozwiązania — jedno deterministyczne […] i potem agentowe. Jedno i
> drugie działa"
> „Tutaj jednak deterministycznie ciężko było analizować komunikaty, ale można próbować :D"

Modele lokalne: `gemma4:31b` dawała radę (`:113`, `:152`), cała rodzina Qwen nie.
`Gemini 3 Flash` „rozpykał" (`:170`). Wersje `4.1-mini` wystarczały (`:605`).

**Restart po crashu generuje NOWĄ mapę**, więc żadna wiedza nie przenosi się między
podejściami — ale też żadna porażka nic nie kosztuje poza kilkoma requestami.

---

## s05e05 `timetravel` — maszyna czasu

**Bez obejścia to najdroższe zadanie kursu** (`s05e05_aid4u_comments.md:38`):
> „W końcu — dla mnie **najtrudniejsze zadanie** :) Przepaliłem za dużo tokenów, a sam
> **Claude Opus 4.6 na próbę spalił 5$ za jednym podejściem.**"

**Ale front da się ominąć w całości** (`:170`, base64, zdekodowane):
> „Wykorzystaj BE endpoint `https://hub.ag3nts.org/timetravel_backend`.
> Pobranie aktualnej konfiguracji: `GET apikey=tutaj-twoj-klucz`
> Ustawienie parametrów, przykład: `POST {"apikey":"…", "mode":"active", "PTA":true,
> "PTB":false, "PWR":28}`
> Aktywacja podróży kiedy `fluxDensity = 100`: `POST https://hub.ag3nts.org/verify
> {"task":"timetravel","answer":{"action":"timeTravel"}}`"

Endpoint sprawdzony 2026-08-20 — żyje (HTTP 400 `{"code":-1,"message":"Invalid or missing
apikey."}`).

Niezależne potwierdzenie, że automatyzacja bije wariant „człowiek klika" (`:101`):
> „wersja z czekaniem na człowieka okazała się **trudniejsza** niż wersja z dostępem dla
> agenta przez selenium"

i podpowiedź w tym samym wątku (`:104`):
> „Mnie też klikanie pokonało :D Agent zrobił to lepiej. **Tip: da się nawet bez selenium**,
> niech agent poszuka jak :)"

**Co i tak trzeba zrobić:** przeczytać `dane/timetravel.md` (26 kB) i zaimplementować
wyliczanie `syncRatio`, tabelę ochrony PWR zależną od roku, `flux density = 100%`,
oczekiwanie na właściwy `internalMode` (zmienia się sam co kilka sekund → polling),
zarządzanie baterią (rozładowanie do zera = zostają tylko `help`/`getConfig`/`reset`).
Trasa: **2238 → dzisiejsza data → 12.11.2024**, przy czym tunel (PT-A i PT-B naraz) je
więcej energii niż zwykły skok.

Ktoś zrobił to półautomatycznie i „poziomy znajdował grep'em" (`:514`).

---

## Obserwacje przekrojowe

1. **Modele, które dowoziły najczęściej w obu sezonach:** `gemini-3-flash-preview`
   (wielokrotnie „za pierwszym razem"), `gpt-5-mini`, `gpt-4.1-nano` (tam gdzie liczyła się
   latencja), `Deepseek 3.2`. **`gemini-3-flash` jest w komentarzach S04/S05 najczęściej
   wymienianym zwycięzcą.**
2. **„Mocniejszy" bywa gorszy** (`s04e04:2`):
   > „Używałem gpt-5.4-mini […] i nie potrafił w wielu podejściach za nic przeskoczyć błędów.
   > […] puściłem gpt-5-mini i rozwalił to w kilku krokach. Co tu się stało? 🤔 **Nie zawsze
   > mocniejszy model**"
3. **Modele lokalne:** dobre w zadaniach wsadowych (s05e03, s04e03), rozkładają się na
   polskiej semantyce (s04e04) i na długich pętlach (s04e02, s05e04). Zgodne z polityką
   przyjętą po S03.
4. **Koszt całego kursu u oszczędnych uczestników:** „poniżej $2.5" (`s05e05:904`),
   „~2$ za całe szkolenie" (`s04e04:56`), „mniej niż $1" (`s05e05:745`). Nasze $0.00 za cały
   S03 nie jest anomalią — to górny koniec tej samej dyscypliny.
5. **Platforma żyje po kursie** (`s05e05:71`):
   > „platforma będzie działała conajmniej rok ;)"

   Potwierdzone niezależnie 2026-08-20: wszystkie sprawdzone URL-e huba zwracają 200.
