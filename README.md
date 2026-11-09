# Algorytm mrówkowy (ACO) dla problemu komiwojażera

Projekt z przedmiotu *Algorytmy inteligentne inspirowane naturą*.
Mrówki z mrowiska szukają najkrótszej trasy, która odwiedza wszystkie punkty z pożywieniem i wraca do mrowiska.

## Wymagania
- Python 3.10 lub nowszy
- biblioteki pygame, numpy, matplotlib – instalowane w środowisku wirtualnym `.venv`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`uruchom.bat` robi to sam przy pierwszym uruchomieniu. Polecenia poniżej zakładają aktywne środowisko
(`.\.venv\Scripts\Activate.ps1`) albo wywołanie `.\.venv\Scripts\python.exe` zamiast `python`.

## Uruchomienie
- **Aplikacja:** `python aplikacja.py` (albo dwuklik na `uruchom.bat`) – uruchamia się na pełnym ekranie;
  `python aplikacja.py --okno` uruchamia ją w oknie, którego rozmiar można zmieniać
- **Eksperymenty i wykresy:** `python porownanie.py` (wyniki w katalogu `wyniki/`, ok. 1–2 min);
  `python porownanie.py --szybko` robi mniej powtórzeń

## Obsługa aplikacji
| Akcja | Co robi |
|---|---|
| LPM na pustym miejscu | dodaje punkt z pożywieniem |
| LPM + przeciągnięcie | przesuwa punkt lub mrowisko |
| PPM na punkcie | usuwa punkt |
| Spacja / „Start” | uruchamia lub zatrzymuje algorytm mrówkowy |
| S / „Krok” | wykonuje jedną iterację |
| R / „Losuj punkty” | losuje tyle punktów, ile ustawiono suwakiem |
| C / „Wyczyść” | zostawia samo mrowisko |
| B / „Blokowanie” | w tym trybie kliknięcie odcinka blokuje lub odblokowuje ścieżkę |
| I / „Wzory (I)” | panel: grupa algorytmu, użyty wariant, wzory i bieżące parametry |
| W / „Wybór (W)” | kliknięcie punktu pokazuje prawdopodobieństwa wyboru kolejnego punktu (wzór p_ij na żywo) |
| K / „Kroki (K)” | w trybie wyboru: najbardziej prawdopodobna trasa mrówki krok po kroku (1., 2., 3., …) z szansą każdego kroku, drugą opcją i szansą całej trasy |
| A / „Mrówki (A)” | animacja mrówek przechodzących swoje trasy; feromon zmienia się po powrocie wszystkich |
| F11 | przełącza pełny ekran i okno |
| Esc | zamyka aplikację |
| P / „Porównaj algorytmy” | liczy trasę ACO, najbliższym sąsiadem, 2-opt i przeglądem zupełnym (do 10 punktów); kliknięcie wiersza tabeli pokazuje trasę |
| „Feromon” | włącza lub wyłącza rysowanie śladów feromonu |
| „Reset feromonu” | zaczyna działanie kolonii od nowa |

Suwaki zmieniają parametry algorytmu w trakcie działania: liczbę mrówek, α (waga feromonu), β (waga odległości),
ρ (parowanie) i prędkość animacji.

## Pliki
- `algorytmy.py` – algorytm mrówkowy, przegląd zupełny, najbliższy sąsiad, 2-opt
- `aplikacja.py` – interfejs w pygame
- `porownanie.py` – eksperymenty, tabele CSV i wykresy
- `dokumentacja/` – dokumentacja (`Dokumentacja_ACO_TSP.docx` + PDF), prezentacja (`Prezentacja_ACO_TSP.pptx` + PDF) i rysunki
- `dokumentacja/narzedzia/` – skrypty generujące: `zrzuty.py` (zrzuty ekranu), `wzory.py` (wzory),
  `dokumentacja.js` i `prezentacja.js` (wymagają Node.js i pakietów `docx` / `pptxgenjs`)
- `wyniki/` – wyniki eksperymentów  

## Zmiany najważniejsze  
Aplikacja pokazuje teraz, jak mrówki podejmują decyzje: po kliknięciu punktu widać, z jakim prawdopodobieństwem mrówka pójdzie do każdego kolejnego punktu, a przycisk „Kroki” rozpisuje całą najbardziej prawdopodobną trasę krok po kroku (1., 2., 3., …) z szansą każdego ruchu. Doszedł też panel ze wzorami algorytmu i bieżącymi parametrami oraz animacja mrówek chodzących po planszy, w której feromon zmienia się dopiero, gdy wszystkie mrówki wrócą do mrowiska.
