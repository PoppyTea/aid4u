# Centrum Wiedzy: 4th-devs Dema (Dashboard)

Ten dokument jest punktem startowym (matką) spajającym wszystkie Karty Projektów - Demo. Działa w oparciu o silnik bazodanowy wtyczki **Dataview**.

> **Uwaga:** Aby poniższe tabele działały, musisz mieć zainstalowaną i włączoną wtyczkę Dataview w Obsidianie.

---

## 🗺️ Tabela Główna - Zestawienie Dem

```dataview
TABLE 
    associated_task AS "Powiązane Zadanie",
    difficulty_python AS "Trudność (Python)",
    join(core_tech_ts, ", ") AS "Stack TS",
    join(core_tech_py, ", ") AS "Odp. Python",
    status AS "Status"
FROM "AID4U-era/30_Projects/02_4th-Devs"
WHERE contains(tags, "#demo")
SORT file.name ASC
```

---

## 🔗 Analiza Powiązań (Krawędzie)

Wykaz wszystkich symbiotycznych powiązań między różnymi rozwiązaniami (Skąd -> Dokąd) oraz typu krawędzi (np. rozszerza, współpracuje, dziedziczy).

```dataview
TABLE edge.to AS "Węzeł Docelowy (Dziecko)", edge.type AS "Typ Krawędzi"
FROM "AID4U-era/30_Projects/02_4th-Devs"
WHERE edges != null
FLATTEN edges AS edge
SORT file.name ASC
```

---

*Tutaj można dodać graf z użyciem np. wtyczki Obsidian Juggl, która potrafi natywnie zwizualizować powiązania z powyższych tabel Dataview do interaktywnego Canvasa, lub oprzeć się na wbudowanym grafie Obsidiana (który czyta linki z frontmatter).*
