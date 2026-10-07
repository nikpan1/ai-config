# Angular: stan dostępnych rozwiązań

## Konkluzja

Nie znaleziono publicznego projektu open source, który łączyłby jednocześnie:

- generację dokumentacji przez LLM,
- parser/semantykę charakterystyczną dla Angulara,
- zestaw skillów lub pełny pipeline utrzymania dokumentów.

To jest wynik ograniczonego przeglądu publicznych repozytoriów GitHub, a nie
dowód, że taki projekt nie istnieje. Najbliższe, wiarygodne klocki są
komplementarne, nie konkurencyjne.

## 1. Compodoc — najlepsza deterministyczna baza kodowa

- Repozytorium: [compodoc/compodoc](https://github.com/compodoc/compodoc) · MIT.
- Generuje dokumentację dla Angulara (oraz Nest/Stencil) na podstawie kodu:
  komponenty, dyrektywy, pipe’y, moduły, DI, guardy, interceptory, klasy,
  interfejsy i routing
  [źródło pierwotne](https://github.com/compodoc/compodoc#features).
- Obsługuje nowoczesny Angular: standalone APIs, signal inputs, `provideRouter`,
  lazy routes i grafy zależności. Daje raport coverage dla CI oraz eksport JSON
  i Markdown gotowy dla LLM
  [źródło pierwotne](https://github.com/compodoc/compodoc#features).
- **Nie używa AI.** Właśnie dlatego jest wartościowy jako faktograficzna warstwa
  wejściowa albo weryfikator pokrycia przed wywołaniem modelu.

## 2. Oficjalne Angular Skills — kontekst dla agenta, nie generator docs

- Repozytorium: [angular/skills](https://github.com/angular/skills).
- Dostarcza skille `angular-developer` oraz `angular-new-app`; opisują one
  nowoczesne praktyki, m.in. komponenty, serwisy, HTTP, signals, formularze,
  DI, routing, SSR, a11y i testy
  [źródło pierwotne](https://github.com/angular/skills#available-skills).
- Skille są przeznaczone dla agentowych narzędzi codingowych i można je
  instalować przez `npx skills add`
  [źródło pierwotne](https://github.com/angular/skills#using-agent-skills).
- **Nie generują dokumentacji.** Mogą jednak ograniczyć błędy frameworkowe w
  własnym skillu „document-angular-app”.

## Praktyczna kompozycja dla Angulara

    kod TypeScript + szablony + routing
                  │
                  ├──► Compodoc: API, grafy, coverage, JSON/Markdown
                  │
                  ├──► Angular Skills: reguły i słownik frameworka
                  │
                  └──► agent dokumentujący: README / architektura / guide
                                      │
                           kontrola źródeł + diff + review

To **proponowana architektura**, nie istniejąca integracja. Dla dokumentacji
zastanej należy przed nią dodać konwersję Docling oraz warstwę rozstrzygania
konfliktów „kod kontra legacy opis”.

## Co warto zweryfikować w POC

1. Czy Compodoc rzeczywiście rozpoznaje wersję Angulara i użyte wzorce
   routingu w docelowym projekcie.
2. Czy agent cytuje pliki/linie albo przynajmniej symbole z wyjścia Compodoc,
   zamiast tworzyć niezweryfikowany opis komponentów.
3. Czy przy zmianie szablonu HTML i stylów proces oznacza instrukcję użytkową
   do aktualizacji; sam AST TypeScript nie ujmuje całej semantyki UI.
4. Czy skill ma rozdzielone artefakty: API/reference, architektura i guide
   użytkownika — to ogranicza mieszanie faktów i interpretacji.
