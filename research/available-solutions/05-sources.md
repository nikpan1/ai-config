# Rejestr źródeł

> Dostęp i weryfikacja: 7 października 2026 r. Linki prowadzą do README lub
> bezpośrednio do opisu funkcji w repozytorium autora. GitHub i README są
> źródłem pierwotnym dla deklarowanego zakresu, licencji i sposobu działania,
> lecz nie są niezależnym testem jakości.

| ID | Źródło | Co potwierdza |
| --- | --- | --- |
| S1 | [`divar-ir/ai-doc-gen` — README](https://github.com/divar-ir/ai-doc-gen#features) | Pięć agentów, artefakty `.ai/docs/`, generację README/rules, skille Claude Code, GitLab i konfigurację. |
| S2 | [`AsyncFuncAI/deepwiki-open` — README](https://github.com/AsyncFuncAI/deepwiki-open#deepwiki-open-grok-wiki) | Analizę kodu, dokumentację, diagramy, codemap i wiki dla repozytoriów GitHub/GitLab/Bitbucket. |
| S3 | [`dshills/clarion` — How it works](https://github.com/dshills/clarion#how-it-works) | Pipeline Scanner → Fact Model → LLM → Verifier oraz brak surowego kodu w promptach. |
| S4 | [`dshills/clarion` — CI integration](https://github.com/dshills/clarion#ci-integration) | Generację, weryfikację i drift w CI. |
| S5 | [`mortenkrane/dokken` — Why Dokken](https://github.com/mortenkrane/dokken#why-dokken) | Wywiad o intencji, baseline, drift, CI, ręczne sekcje i status wczesnej alphy. |
| S6 | [`sopaco/deepwiki-rs` — README](https://github.com/sopaco/deepwiki-rs#features--capabilities) | Litho, wejścia zewnętrzne, C4 i deklarowany pipeline generacji. |
| S7 | [`sopaco/deepwiki-rs` — Core process](https://github.com/sopaco/deepwiki-rs#core-process) | Rozdzielenie preprocessingu, researchu, kompozycji oraz walidacji/eksportu. |
| S8 | [`BinarCode/aidocs-cli` — How it works](https://github.com/BinarCode/aidocs-cli#how-it-works) | Trzy źródła prawdy: screenshoty, kod i eksploracja UI. |
| S9 | [`BinarCode/aidocs-cli` — docs:update](https://github.com/BinarCode/aidocs-cli#docsupdate) | Aktualizację dokumentacji w oparciu o `git diff`, mapowanie zmian i Playwright. |
| S10 | [`docling-project/docling` — Features](https://github.com/docling-project/docling#features) | Obsługiwane formaty, OCR, eksporty i integracje agentowe. |
| S11 | [`docling-project/docling` — CLI](https://github.com/docling-project/docling#2-convert-a-document-cli) | Konwersję dokumentu do Markdown. |
| S12 | [`Unstructured-IO/unstructured` — README](https://github.com/Unstructured-IO/unstructured#open-source-pre-processing-tools-for-unstructured-data) | Charakter open-source ETL/preprocessing dla danych LLM. |
| S13 | [`infiniflow/ragflow` — Key Features](https://github.com/infiniflow/ragflow#key-features) | RAG, cytowania, heterogeniczne źródła, chunking oraz Knowledge Compilation do wiki, grafów i skillów. |
| S14 | [`compodoc/compodoc` — Features](https://github.com/compodoc/compodoc#features) | Zakres generatora Angular, routing, coverage i eksport. |
| S15 | [`angular/skills` — Available Skills](https://github.com/angular/skills#available-skills) | Oficjalne skille oraz ich zakres. |

## Metoda i ograniczenia

Przeszukano GitHub po kombinacjach: „AI documentation generator”, „codebase”,
„legacy documentation”, „documentation drift”, „skills”, „pipeline” i
„Angular”. Każde ujęte repozytorium otwarto i przeczytano w zakresie funkcji,
architektury lub workflow; nie oparto klasyfikacji wyłącznie na fragmencie
wyniku wyszukiwania.

Badanie nie obejmuje prywatnych repozytoriów, produktów zamkniętych ani
pełnego audytu kodu i bezpieczeństwa każdego projektu. „Nie znaleziono”
oznacza więc brak wiarygodnego kandydata w tym, celowo ograniczonym, przeglądzie
publicznego GitHub na wskazaną datę.
