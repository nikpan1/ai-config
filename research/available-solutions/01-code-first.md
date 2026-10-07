# Rozwiązania: kod jako źródło prawdy

## 1. `divar-ir/ai-doc-gen` — najbliżej modelu „skills + pipeline”

- Repozytorium: [GitHub](https://github.com/divar-ir/ai-doc-gen) · licencja
  MIT.
- Wejście: repozytorium; analizowane są struktura, zależności, data flow,
  request flow oraz API.
- Pipeline: pięciu wyspecjalizowanych agentów zapisuje analizy do `.ai/docs/`;
  kolejni agenci generują README oraz `CLAUDE.md`, `AGENTS.md` i reguły Cursor.
  W repozytorium są też trzy skille (`analyze-codebase`, `generate-readme`,
  `generate-ai-rules`) i plugin Claude Code
  [źródło pierwotne](https://github.com/divar-ir/ai-doc-gen#features).
- Automatyzacja: CLI, konfiguracja warstwowa, współbieżność, retry,
  obserwowalność, kontener/Helm oraz cronjob GitLab tworzący merge requesty
  [źródło pierwotne](https://github.com/divar-ir/ai-doc-gen#quick-start).
- Dopasowanie: najlepszy kandydat do analizy jako referencja dla produktu
  opartego o skille i powtarzalny workflow.
- Granica: deklarowany wynik to przede wszystkim README i instrukcje dla
  agentów, a nie pełna wielostronicowa dokumentacja użytkownika; jakość i
  pokrycie należy zmierzyć na reprezentatywnym repozytorium.

## 2. `AsyncFuncAI/deepwiki-open` — gotowa wiki kodu

- Repozytorium: [GitHub](https://github.com/AsyncFuncAI/deepwiki-open) · MIT.
- Wejście: repozytoria GitHub, GitLab lub Bitbucket.
- Funkcje: analizuje strukturę kodu, generuje dokumentację, diagramy i
  codemap, a wynik układa w interaktywną wiki
  [źródło pierwotne](https://github.com/AsyncFuncAI/deepwiki-open#deepwiki-open-grok-wiki).
- Dopasowanie: dobry wybór, jeśli odbiorca potrzebuje szybko przeglądać i
  zadawać pytania o obce repozytorium, a nie włączać dokumentację do własnego
  procesu review.
- Granica: README nie pokazuje zestawu skillów ani sprawdzania każdego
  twierdzenia względem kodu; należy traktować wynik jako pomoc do odkrywania,
  nie automatycznie zaakceptowaną dokumentację referencyjną.

## 3. `dshills/clarion` — generacja oparta na faktach (Go)

- Repozytorium: [GitHub](https://github.com/dshills/clarion) · MIT.
- Wejście: repozytorium Go oraz `SPEC.md` i `PLAN.md`.
- Pipeline: AST skanera tworzy `FactModel`; LLM dostaje wyłącznie model faktów
  i dwa dokumenty wejściowe, tworzy Markdown/Mermaid, a weryfikator wiąże
  twierdzenia z modelem
  [źródło pierwotne](https://github.com/dshills/clarion#how-it-works).
- Utrzymanie: `verify`, `drift`, generacja pojedynczej sekcji i przykładowy
  workflow CI są częścią narzędzia
  [źródło pierwotne](https://github.com/dshills/clarion#ci-integration).
- Dopasowanie: najlepszy wzorzec redukcji halucynacji w dokumentacji kodowej
  oraz jawnego kryterium „nie umiem tego udowodnić”.
- Granica: skaner jest przeznaczony dla Go. Model nie dostaje surowego kodu,
  więc bez dobrego `SPEC.md`/`PLAN.md` nie opisze wiarygodnie decyzji
  projektowych.

## 4. `mortenkrane/dokken` — dokumentacja intencji i kontrola driftu

- Repozytorium: [GitHub](https://github.com/mortenkrane/dokken) · MIT.
- Wejście: kod modułu i odpowiedzi człowieka na pytania o odpowiedzialność,
  granice oraz ograniczenia architektury.
- Pipeline: `generate` tworzy baseline, `check --all` może blokować CI po
  wykryciu driftu, a `--fix` aktualizuje dokumentację. Projekt zachowuje
  ręczne sekcje i deklaruje cache dla niezmienionego kodu
  [źródło pierwotne](https://github.com/mortenkrane/dokken#why-dokken).
- Dopasowanie: ważny wzorzec dla informacji „dlaczego”, których sam kod nie
  wyraża; nadaje się do utrzymania dokumentacji architektury po bootstrapie.
- Granica: autor oznacza projekt jako wczesną alphę; nie jest to importer
  legacy dokumentacji ani gotowy zestaw skillów.

## Wniosek dla tej kategorii

Rynek ma już dobre generatory „code-first”, ale różnią się **dowodem jakości**:
wiki i README są najłatwiejsze do wygenerowania, natomiast Clarion wyróżnia się
modelem faktów i weryfikacją. Przy wyborze warto wymagać oddzielnego etapu
faktów oraz driftu, nawet jeśli interfejs pozostanie oparty o skille.
