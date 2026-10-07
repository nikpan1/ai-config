# Rozwiązania: kod plus istniejąca wiedza

## 1. Litho / `sopaco/deepwiki-rs` — najpełniejszy hybrydowy pipeline

- Repozytorium: [sopaco/deepwiki-rs](https://github.com/sopaco/deepwiki-rs) ·
  MIT; projekt nazywa dziś generator „Litho”, a równolegle rozwija następcę
  Terrain [źródło pierwotne](https://github.com/sopaco/deepwiki-rs#litho-deepwiki-rs).
- Wejście: kod wielojęzyczny, komentarze/docstringi i adnotacje; dodatkowo
  zewnętrzne materiały, w tym PDF, Markdown oraz SQL
  [źródło pierwotne](https://github.com/sopaco/deepwiki-rs#features--capabilities).
- Pipeline: preprocessing wyodrębnia strukturę, oryginalne dokumenty, wnioski
  z kodu i zależności; etap researchu ma wyspecjalizowanych agentów, a etap
  kompozycji tworzy hierarchiczną dokumentację C4 i diagramy
  [źródło pierwotne](https://github.com/sopaco/deepwiki-rs#core-process).
- Kontrola: końcowy etap sprawdza diagramy i pokrycie dokumentacji oraz tworzy
  indeks/spis treści
  [źródło pierwotne](https://github.com/sopaco/deepwiki-rs#validation-and-enhancement-stage).
- Dopasowanie: najlepszy znaleziony przykład przepływu, w którym legacy
  materiały wzbogacają analizę kodu zamiast być ignorowane.
- Ryzyko: deklarowane możliwości pochodzą z README; przed użyciem produkcyjnym
  należy uruchomić POC na prywatnym repo i sprawdzić rzeczywistą obsługę
  formatów, koszt tokenów oraz kierunek utrzymania po rozwoju Terrain.

## 2. `BinarCode/aidocs-cli` — kod, żywy interfejs i istniejące docs

- Repozytorium: [BinarCode/aidocs-cli](https://github.com/BinarCode/aidocs-cli) · MIT.
- Trzy deklarowane źródła prawdy: zrzuty ekranu analizowane wizualnie, analiza
  frontendu/backendu oraz aktywna eksploracja UI (kliknięcia, formularze i
  warianty warunkowe)
  [źródło pierwotne](https://github.com/BinarCode/aidocs-cli#how-it-works).
- Workflow: discover → plan → execute/batch; aktualizacja pobiera `git diff`,
  mapuje zmienione pliki na istniejącą dokumentację i ją aktualizuje. Obsługuje
  też RAG/MCP dla katalogu docs i ponowne chunkowanie po zmianach
  [źródło](https://github.com/BinarCode/aidocs-cli#docsupdate),
  [RAG/MCP](https://github.com/BinarCode/aidocs-cli#docsrag-vectors).
- Wynik: dokumentacja użytkowa ze zrzutami albo techniczna, do tego eksport PDF.
- Dopasowanie: szczególnie wartościowy dla aplikacji webowych, gdy różnica
  między kodem a faktycznym ekranem użytkownika jest istotna.
- Granica: „legacy docs” nie są tu pełnoprawnym źródłem faktów w procesie
  generacji; są przeszukiwane i aktualizowane. Wymaga Claude Code, a scenariusze
  ze screenshotami — Playwright MCP.

## 3. Dokken jako wzorzec uzupełniający

`Dokken` nie importuje plików legacy, lecz dołącza wiedzę, której w kodzie nie
ma: odpowiedzi człowieka o intencji architektury. Potem porównuje kod z tym
baseline’em w CI [źródło pierwotne](https://github.com/mortenkrane/dokken#why-dokken).
Jest to wartościowy komponent koncepcyjny dla systemu łączącego dokumenty
legacy z kodem: trzeba jawnie określić, które źródło ma pierwszeństwo, gdy są
sprzeczne.

## Wniosek

Spośród ocenionych projektów tylko Litho wyraźnie opisuje użycie dokumentów
zewnętrznych *wewnątrz* procesu analizy kodu. `aidocs-cli` lepiej rozwiązuje
natomiast problem zgodności dokumentacji produktu z żywym UI i zmianami w Git.
Wybór zależy więc od rodzaju dokumentu: C4/architektura → Litho; instrukcje
użytkownika i flow webowe → aidocs-cli.
