# Open-source AI do generowania dokumentacji — podsumowanie

> Stan researchu: 7 października 2026 r. Zakres: publicznie dostępne repozytoria
> open source, w których faktycznie istnieje kod, pipeline lub zestaw skillów
> związany z tworzeniem albo utrzymaniem dokumentacji. To nie jest ranking ani
> test jakości wygenerowanych dokumentów.

## Konkluzja

**Najbliżej gotowego, przenośnego rozwiązania o architekturze „skills +
pipeline” jest `divar-ir/ai-doc-gen`.** Ma pięć równoległych agentów analizy,
trzy instalowalne skille Claude Code, artefakty pośrednie i automatyzację
GitLab; generuje README oraz instrukcje dla agentów
[źródło](01-code-first.md#1-divar-irai-doc-gen--najblizej-modelu-skills--pipeline).

Jeżeli dokumentacja ma powstawać **z kodu i istniejących materiałów**,
najpełniejszym kandydatem jest **Litho / `sopaco/deepwiki-rs`**: jego pipeline
wyodrębnia kod i dokumenty wejściowe, a następnie tworzy wiki C4. Dla
dokumentacji produktu webowego warto rozważyć **`BinarCode/aidocs-cli`**, bo
łączy kod z obserwacją działającego interfejsu, zrzutami ekranu i eksploracją
UI [źródło](03-code-and-existing-docs.md).

W kategorii **wyłącznie legacy dokumentacji** nie znaleziono porównywalnego,
dojrzałego projektu, który autonomicznie pisałby nową dokumentację jako
wersjonowane pliki Markdown z kontrolą faktów. **RAGFlow** jest dziś istotnym
wyjątkiem częściowym: ma „Knowledge Compilation”, która z dokumentów i
datasetów tworzy wiki, grafy, drzewa i skille. **Docling** i **Unstructured**
pozostają warstwą ekstrakcji/ETL. Żaden z nich nie zwalnia z redakcji i review
wyniku [źródło](02-legacy-documentation.md).

Nie znaleziono też otwartego narzędzia AI wyspecjalizowanego *bezpośrednio* w
generowaniu dokumentacji aplikacji Angular. Istnieje dojrzały, lecz
deterministyczny generator **Compodoc** oraz oficjalne **Angular Skills**, które
są dobrym komponentem kontekstowym dla uniwersalnego agenta
[źródło](04-angular.md).

## Mapa wyboru

| Potrzeba | Najlepszy punkt startowy | Dlaczego | Główne zastrzeżenie |
| --- | --- | --- | --- |
| Repozytorium i instrukcje dla agentów | `divar-ir/ai-doc-gen` | Skille, pięciu agentów, artefakty `.ai/docs/`, GitLab/CI | Skupia się na README i plikach instrukcji; należy ocenić go na własnym kodzie. |
| Interaktywna wiki z diagramami z dowolnego repo | `AsyncFuncAI/deepwiki-open` | Samoobsługowa wiki, diagramy i codemap, wiele forge’ów | Aplikacja wiki, a nie pakiet skillów czy proces kontroli jakości dokumentów. |
| Dokumentacja architektury C4, także z materiałami zewnętrznymi | `sopaco/deepwiki-rs` (Litho) | Wieloetapowy pipeline, C4, PDF/Markdown/SQL jako wiedza zewnętrzna | Projekt rozwinął się w Terrain; warto zweryfikować kierunek utrzymania. |
| Udowadnialne dokumenty Go | `dshills/clarion` | Fact Model, wskazania plik/linia, weryfikator i drift | Tylko Go; opis „dlaczego” wymaga `SPEC.md`/`PLAN.md`. |
| Strony/flow użytkownika aplikacji webowej | `BinarCode/aidocs-cli` | Kod + zrzuty + eksploracja UI + aktualizacja po diffie | Wymaga Claude Code i dla pełnego trybu Playwright MCP; nie jest Angular-only. |
| Zachowanie intencji architektonicznej | `mortenkrane/dokken` | Wywiad o „dlaczego”, drift w CI, zachowuje sekcje ręczne | Wczesna alpha, nie importer zastanej dokumentacji. |
| Materiał legacy (PDF, DOCX, PPTX, skany) | RAGFlow albo Docling → własny agent | RAGFlow kompiluje wiedzę do wiki/skillów; Docling daje lokalny Markdown/JSON | RAGFlow to cięższa platforma, a żadna opcja nie zastępuje zatwierdzenia treści. |
| Aplikacja Angular | Compodoc + Angular Skills + generator ogólny | AST/API i coverage z Compodoc; aktualne reguły Angulara jako kontekst LLM | To kompozycja komponentów, nie jeden istniejący pipeline AI. |

## Co oznacza „dostępne rozwiązanie” w tym researchu

Włączono projekty, dla których README i struktura repozytorium potwierdzają co
najmniej jeden z elementów: analizę kodu, transformację legacy materiałów,
generację dokumentacji, aktualizację po zmianach, workflow/skill albo
mechanizm weryfikacji. Gwiazdki i forki nie są kryterium jakości — są jedynie
zmiennym sygnałem widoczności.

Rozdział „legacy” celowo zawiera też **komponenty**, a nie wyłącznie pełne
generatory. Parser dokumentu może dać wiarygodną treść wejściową, ale nie
gwarantuje poprawnej syntezy, struktury docelowej ani utrzymywania wersji.

## Rekomendowany kierunek dla nowego rozwiązania

Jeżeli celem jest generator dokumentacji technicznej dla realnego, często
zmienianego systemu, najbardziej uzasadniona jest architektura hybrydowa:

    legacy PDF/DOCX/HTML ──► parser (np. Docling) ─┐
                                                     ├─► faktów/model domeny
    kod + testy + kontrakty ──► AST/analityka ──────┘       ↓
                                              agent redakcyjny + cytowania
                                                           ↓
                                          Markdown/diagramy + weryfikacja driftu

To jest **rekomendacja wynikająca z analizy**, nie deklarowana kompletna
funkcja jednego repozytorium. Ogranicza dwa rodzaje błędów: halucynacje o
kodzie (wzorzec Fact Model z Clarion) oraz utratę wiedzy, której kod nie
zawiera (wzorzec human-intent z Dokken i dokumenty zewnętrzne w Litho).

## Zawartość katalogu

- [01 — Kod jako źródło prawdy](01-code-first.md)
- [02 — Legacy dokumentacja](02-legacy-documentation.md)
- [03 — Kod i istniejąca dokumentacja / stan aplikacji](03-code-and-existing-docs.md)
- [04 — Angular](04-angular.md)
- [05 — Rejestr źródeł](05-sources.md)
