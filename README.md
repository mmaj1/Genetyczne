# Życie kolonii — laboratorium ACO / TSP

Interaktywna aplikacja na przedmiot **Algorytmy inteligentne inspirowane naturą**. Mrówki szukają krótkiej trasy z mrowiska przez wszystkie punkty pożywienia i z powrotem. Używamy Ant System ze strategią elitarną. To heurystyka: wynik nie musi być optymalny.

## Dokumentacja i przygotowanie prezentacji

- [Pełna dokumentacja projektu](dokumentacja/aktualna/Dokumentacja_ACO_TSP_aktualna.docx) — cel, model, wzory, architektura, obsługa, wyniki, testy i ograniczenia.
- [Scenariusz wystąpienia na 8–10 minut](dokumentacja/aktualna/Scenariusz_prezentacji_ACO_TSP.docx) — gotowe wypowiedzi, kolejność pokazu, interpretacja wykresów i odpowiedzi na pytania.

## Uruchomienie

Python 3.10+ i zależności z `requirements.txt`.

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python aplikacja.py --okno
```

Windows: uruchom `uruchom.bat` lub użyj `.venv\Scripts\python.exe`. Bez `--okno` aplikacja działa na pełnym ekranie. F11 przełącza tryb wyświetlania.

## Plansza i śledzenie mrówki

Turkusowe ślady pokazują feromon. Silniejsze ścieżki świecą jaśniej; zmiana jasności jest płynna, a parowanie wygasza ślady. Najlepsza trasa jest złota. Po poprawie wyniku pojawia się podświetlenie i procent skrócenia.

Kliknij mrówkę albo **Śledź mrówkę** (`F`). Panel pokazuje rzeczywiście wylosowany ruch i szanse zapisane w chwili wyboru. Złoty znacznik oznacza wybór mrówki — nie zawsze wygrywa najwyższe prawdopodobieństwo.

- **Start / Pauza**, `Spacja`: uruchamia lub zatrzymuje całą kolonię.
- **Następny ruch**, `N`: zatrzymuje kolonię i prowadzi do kolejnego punktu śledzonej mrówki. Pozostałe mrówki pokonują taką samą odległość. Gdy śledzona mrówka zakończyła podróż, krok kończy podróże pozostałych; kolejny rozpoczyna nową rundę.
- **Iteracja**, `S`: natychmiast kończy jedną rundę i pozostawia symulację w pauzie.
- Feromon zmienia się po zakończeniu wszystkich podróży. Mrówki, które utknęły, nie odkładają feromonu.
- Suwaki wyboru zmienione w czasie animacji dotyczą następnej rundy. Prędkość odtwarzania działa od razu.

## Gotowe eksperymenty

Wybór scenariusza resetuje mapę, parametry, feromon, historię, porównanie i śledzenie. Ustalone ziarno losowania pozwala powtórzyć pokaz przy tym samym rozmiarze planszy.

| Scenariusz | Co pokazuje |
|---|---|
| Pierwsza kolonia | Powstawanie śladów i rzeczywiste wybory mrówek. |
| Pułapka najbliższego sąsiada | Zachłanna trasa jest o ponad 25% dłuższa od optimum. Użyj porównania. |
| Bez feromonu | α = 0: feromon powstaje, ale nie wpływa na wybory. |
| Zablokowana droga | Znajdź trasę, kliknij **Zablokuj drogę**, następnie wybrany odcinek złotej trasy. Kolonia zachowa feromon i poszuka obejścia. |

Blokada jest zakazem przejścia w obu kierunkach, również przy β = 0. Jej zmiana odrzuca niezatwierdzone podróże i wybór mrówki. Najlepsza trasa zawierająca zamknięty odcinek zostaje unieważniona. Brak znalezionej trasy nie dowodzi, że rozwiązanie nie istnieje.

## Wyścig algorytmów i podsumowanie

**Wyścig (V)** otwiera trzy plansze: ACO, najbliższego sąsiada i 2-opt. Korzystają z jednej niezmiennej kopii bieżącej mapy i blokad. ACO wykonuje 100 iteracji, najbliższy sąsiad buduje trasę punkt po punkcie, a 2-opt poprawia trasę początkową najbliższego sąsiada. Po zakończeniu metoda pozostaje widoczna, gdy pozostałe jeszcze pracują.

- **Start / Pauza** steruje wszystkimi trzema planszami. **N / S** wykonuje jeden wspólny krok prezentacji.
- Pod każdą planszą znajdują się długość dopuszczalnej trasy i zsumowany czas jej obliczania. Czas nie obejmuje animacji, oczekiwania ani tworzenia wykresów.
- Do 10 punktów pożywienia optimum jest liczone osobno przeglądem zupełnym. Odchylenie od optimum pojawia się tylko wtedy, gdy znane są optimum i dopuszczalna trasa.
- Wspólny krok prezentacji nie oznacza równej liczby operacji. To demonstracja trzech metod o różnych zasadach działania.
- Zmiany parametrów dotyczą **nowego wyścigu**. **V** wraca do kolonii; edycja mapy lub blokad unieważnia poprzedni wyścig.

W scenariuszu **Zablokowana droga** kliknięcie odcinka uruchamia szukanie obejścia. Czerwony baner pokazuje liczbę zakończonych iteracji od zamknięcia. Zielony baner podaje pierwszą iterację, w której znaleziono dopuszczalne obejście, i czas obliczeń do tego momentu. Pierwsze obejście nie musi być najlepszym możliwym.

Po zakończeniu wyścigu lub znalezieniu obejścia symulacja zatrzymuje się, a po krótkiej chwili pojawia się podsumowanie. **Wykresy (G)** pozwala też zapisać bieżące wyniki wcześniej lub wrócić z wykresów do planszy.

Każdy eksport trafia do osobnego folderu w `wyniki/eksperymenty/`:

- `podsumowanie.png` — długości tras, czasy obliczeń i zbieżność ACO; dla blokady przebieg przed i po zamknięciu oraz mapa zmienionej trasy.
- `wyniki.csv` — wartości do dalszej analizy; `postep_aco.csv` dodatkowo dla wyścigu.
- `dane.json` — wyniki, przebieg, mapa, blokady i ustawienia.

Przykładowe kompletne raporty bez otwierania okna: `python3 narzedzia/demo_eksperymenty.py`.

## Edycja i objaśnienia

| Akcja | Działanie |
|---|---|
| LPM na pustym miejscu | Dodaje pożywienie i resetuje kolonię. |
| Przeciągnięcie punktu | Przesuwa punkt lub mrowisko i resetuje kolonię. |
| PPM na pożywieniu | Usuwa punkt. |
| R / C | Losuje punkty / czyści planszę. |
| B | Włącza edycję blokad; kliknij odcinek. |
| I | Pokazuje wzory i klasyfikację ACO. |
| W | Pokazuje prawdopodobieństwa dla wskazanego punktu. |
| K | Podgląd zachłanny: najwyższa szansa w każdym kroku. To osobny podgląd, nie podróż śledzonej mrówki. |
| A | Przełącza animację i szybkie obliczenia, porzucając niezatwierdzoną rundę. |
| P | Porównuje ACO (100 iteracji), najbliższego sąsiada, 2-opt i przegląd zupełny do 10 punktów pożywienia. Kliknięcie wiersza pokazuje trasę. |
| V | Otwiera wyścig lub wraca do kolonii. |
| G | Zapisuje i pokazuje wykresy bieżącego eksperymentu / wraca do planszy. |
| Esc | Zamyka aplikację. |

## Moduły

- `aplikacja.py` — uruchomienie i konfiguracja okna.
- `algorytmy.py` — ACO, decyzje i podróże oraz metody porównawcze; bez Pygame.
- `mrowisko/symulacja.py` — stan eksperymentu, pauza, ruch według czasu, krok, blokady i poprawa trasy; bez Pygame.
- `mrowisko/scenariusze.py` — definicje map i parametrów.
- `mrowisko/wyscig.py`, `widok_wyscigu.py` — krokowy model wyścigu i trzy plansze.
- `mrowisko/eksperyment.py`, `raporty.py` — zapis obserwacji oraz eksport wykresów i danych.
- `mrowisko/interfejs.py` — zdarzenia i polecenia użytkownika.
- `mrowisko/plansza.py` — światło, mrówki i panel śledzenia.
- `mrowisko/panel.py`, `kontrolki.py`, `objasnienia.py`, `motyw.py` — pozostałe widoki i wspólne elementy.
- `porownanie.py` — eksperymenty, CSV i wykresy w `wyniki/`.
- `GLOSSARY.md`, `docs/adr/` — pojęcia i decyzja o oddzieleniu losowania od animacji.
- `dokumentacja/` — dotychczasowe materiały i zrzuty poprzedniego interfejsu.

## Weryfikacja

```bash
python3 -m unittest discover -s tests -v
python3 narzedzia/sprawdz_interfejs.py
python3 porownanie.py --szybko
```

Testy sprawdzają rzeczywiste interfejsy kolonii, sesji i scenariuszy. Skrypt interfejsu uruchamia Pygame bez okna, sprawdza zdarzenia i zapisuje zrzuty do `wyniki/podglad/`. Pełne eksperymenty: `python3 porownanie.py`.
