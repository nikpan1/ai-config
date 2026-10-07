# Rozwiązania: legacy dokumentacja jako źródło

## Konkluzja

Nie znaleziono dojrzałego projektu open source, który bierze wyłącznie zastane
PDF/DOCX/PPTX/HTML, autonomicznie tworzy *wersjonowane pliki Markdown* i
jednocześnie kontroluje prawdziwość każdej tezy. Jest jednak ważny częściowy
wyjątek: aktualny RAGFlow ma funkcję Knowledge Compilation, która tworzy z
dokumentów i datasetów wiki, grafy, drzewa, PageIndex, mapy myśli, osie czasu
i skille. Docling oraz Unstructured rozwiązują wcześniejszy etap: ekstrakcję,
normalizację i retrieval. Żaden z tych projektów nie zastępuje review.

## 1. Docling — rekomendowana warstwa wejściowa

- Repozytorium: [docling-project/docling](https://github.com/docling-project/docling) · MIT.
- Zakres: parser wielu formatów (m.in. PDF, DOCX, PPTX, XLSX, HTML, EPUB,
  e-mail, obrazy i LaTeX), OCR, rozpoznanie układu, tabel i kolejności czytania
  [źródło pierwotne](https://github.com/docling-project/docling#features).
- Wynik: wspólny `DoclingDocument` i eksport m.in. do Markdown, HTML oraz
  JSON; CLI może bezpośrednio zapisać ustrukturyzowany Markdown
  [źródło pierwotne](https://github.com/docling-project/docling#2-convert-a-document-cli).
- Integracja: projekt deklaruje integracje z LangChain, LlamaIndex, CrewAI,
  Haystack i MCP, więc nadaje się do podłączenia do workflow agentowego.
- Ocena: **najlepszy kandydat do konwersji legacy materiałów do tekstu
  wejściowego**. Nie jest generatorem nowej dokumentacji — opisuje przetwarzanie
  i konwersję, nie syntezę lub wersjonowanie wyjścia.

## 2. Unstructured — ETL i partycjonowanie dokumentów

- Repozytorium: [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) · Apache-2.0.
- Zakres: komponenty do ingestionu i preprocessing obrazów oraz dokumentów
  PDF, HTML i Word; celem jest strukturalne wyjście dla workflow LLM
  [źródło pierwotne](https://github.com/Unstructured-IO/unstructured#open-source-pre-processing-tools-for-unstructured-data).
- Ocena: dobry wybór dla pipeline’u, który potrzebuje wielu konektorów,
  partycjonowania i przygotowania danych. Nie należy klasyfikować go jako
  narzędzia generującego dokumentację końcową.

## 3. RAGFlow — kompilacja wiedzy z legacy dokumentacji

- Repozytorium: [infiniflow/ragflow](https://github.com/infiniflow/ragflow) ·
  Apache-2.0.
- Zakres: zrozumienie złożonych dokumentów, chunking, źródła Word,
  prezentacje, arkusze, obrazy, skany i strony WWW oraz cytowania do odpowiedzi
  [źródło pierwotne](https://github.com/infiniflow/ragflow#key-features).
- Knowledge Compilation: konfigurowalne szablony i reguły przetwarzania
  generują z dokumentów/datasetów wiki, grafy, drzewa, PageIndex, mapy myśli,
  osie czasu oraz skille; artefakty można oglądać, aktualizować i regenerować
  [źródło pierwotne](https://github.com/infiniflow/ragflow#knowledge-compilation).
- Ocena: najsilniejszy znaleziony kandydat dla samego legacy, jeśli akceptowalna
  jest duża platforma RAG/agentowa. README nie potwierdza eksportu i
  wersjonowania wyników jako plików Markdown ani weryfikacji każdej tezy; te
  dwa aspekty trzeba potwierdzić w POC.

## Minimalny bezpieczny pipeline dla legacy

1. Konwersja źródła do Markdown/JSON (Docling albo Unstructured), z
   zachowaniem identyfikatora dokumentu, strony/sekcji i tabel.
2. Indeks/RAG (opcjonalnie RAGFlow) wyłącznie do odnajdywania źródeł.
3. Agent tworzący nową strukturę dokumentacji; każde twierdzenie powinno mieć
   pochodzenie do pliku i sekcji.
4. Review człowieka dla decyzji architektonicznych, liczb i procedur.
5. Versioning, diff oraz okresowy re-run, aby źródło i wynik nie rozjechały się
   bez śladu.

Punkty 3–5 są **wnioskiem projektowym**, a nie gotową funkcją któregokolwiek
z trzech repozytoriów.
