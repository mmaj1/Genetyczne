# Oddzielenie decyzji kolonii od odtwarzania podróży

Zachowujemy dwufazową iterację ACO: kolonia losuje podróże na początku rundy, a feromon aktualizuje dopiero po zakończeniu wszystkich podróży. Sesja niezależna od Pygame odtwarza zapisane decyzje według czasu; panel śledzenia odczytuje utrwalone prawdopodobieństwa, zamiast liczyć je ponownie z aktualnych suwaków. Zmiana parametrów wyboru dotyczy następnej rundy. Dzięki temu pauza, pojedynczy ruch i zmienna liczba klatek nie zmieniają wyniku losowania. Alternatywa, czyli losowanie przy każdym wizualnym dotarciu do punktu, uzależniałaby przebieg rundy od zmian parametrów w czasie animacji.

Blokada jest zmianą problemu: odrzuca niezatwierdzone podróże i wybór śledzonej mrówki, zachowuje istniejący feromon oraz unieważnia najlepszą trasę, jeżeli zawiera ona zamknięty odcinek. Mrówka, która nie może dokończyć podróży, nie odkłada feromonu. Brak znalezionej trasy nie jest dowodem, że trasa nie istnieje.
