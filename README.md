# PROTOVID | Windows Field Video Editor

**Platforma docelowa: Windows 10/11, 64-bit**. Interfejs: ciemny, techniczny, żółte pasy imitujące przetartą farbę. Działa lokalnie — pliki nie są wysyłane do internetu.

## Funkcje

- Rozmycie Gaussian i pikselizacja (Mosaic), **realne sterowanie siłą 1–100** i podgląd na żywo.
- Rysowanie masek myszką, przesuwanie i skalowanie rogami; wiele masek w jednym filmie.
- Tracking oparty na **lokalnej korelacji fazowej na mapie krawędzi** z dopasowaniem wzorca kontrastowego.
- Klatki kluczowe: korekta maski w dowolnej klatce, automatyczna interpolacja, zachowanie manualnych kotwic podczas śledzenia.
- Prosty montaż bez zmiany oryginału: dzielenie w pozycji głowicy, usuwanie fragmentów, zamiana ich kolejności.
- H.264 MP4 + AAC: **dźwięk zachowywany również po cięciu i przestawieniu fragmentów** (dla pliku z dźwiękiem).
- Zapis i ponowne otwarcie projektu (`*.protovid.json`), detekcja twarzy na bieżącej klatce, przewijanie, odtwarzanie i eksport.

## Plik EXE — budowanie na Windows

**Ważne:** to archiwum zawiera działający kod oraz skrypt budowania, ale **nie gotowy plik PROTOVID.exe**. Środowisko, w którym powstał projekt, to Linux; nie można tam wiarygodnie utworzyć ani sprawdzić natywnego Windows EXE.

1. Na komputerze z Windows 10/11 zainstaluj **Python 3.12 64-bit**, zaznaczając `Add python.exe to PATH` (lub zainstaluj z opcją `py launcher`). Potrzebny dostęp do internetu przy pierwszym budowaniu.
2. Rozpakuj archiwum do folderu, np. `C:\PROTOVID`.
3. Dwukrotnie kliknij **`build_windows.bat`**. Skrypt sam tworzy odizolowane środowisko, instaluje biblioteki, wykonuje testy i buduje aplikację.
4. Gotowy do przeniesienia na inne komputery z Windows plik znajdziesz w **`dist\PROTOVID.exe`**. Na docelowym komputerze Python nie jest wymagany.
5. Do uruchamiania z folderu możesz też użyć **`run_windows.bat`**.

### Alternatywnie: kompilacja online na Windows w GitHub Actions

Po umieszczeniu zawartości tego katalogu w repozytorium GitHub workflow `.github/workflows/windows-build.yml` pozwala uruchomić **Actions → PROTOVID Windows EXE → Run workflow**. Wynik to artefakt `PROTOVID-Windows-exe` zawierający plik `.exe`. To wymaga repozytorium GitHub i połączenia z internetem. Sam workflow nie został tutaj wykonany.

### Praca z programem

1. Kliknij **OTWÓRZ FILM** i wskaż plik.
2. Narysuj maskę bezpośrednio na podglądzie. Zaznacz maskę z listy.
3. Ustaw **SIŁA ROZMYCIA 1–100** i tryb Blur/Mosaic.
4. Ustaw pierwszą klatkę, naciśnij **ŚLEDŹ OD TEJ KLATKI →**. Przy zmianie pozycji obiektu przesuń maskę na odpowiedniej klatce — ta poprawka jest zapisywana jako klatka kluczowa.
5. Aby skrócić/montować, ustaw głowicę i kliknij **ROZETNIJ W TYM MIEJSCU**, następnie wybierz fragment z listy i użyj ▲/▼/USUŃ.
6. Kliknij **EKSPORTUJ H.264 / MP4**. Dźwięk źródłowy zachowuje się w finalnym pliku, również przy przestawionych fragmentach.
7. Przy większym projekcie korzystaj z **ZAPISZ PROJEKT**. Przy przenoszeniu źródła podczas otwierania projekt poprosi o jego odnalezienie.

### Klawisze

- `Spacja`: odtwarzanie/pauza (poza polami edycji).
- `Ctrl+S`: zapis projektu.
- `Ctrl+O`: otwarcie filmu.

## Wymagania i ograniczenia

- Windows 10/11 64-bit; bez dodatkowego Pythona po poprawnym zbudowaniu `PROTOVID.exe`.
- Przygotowane do lokalnego przetwarzania plików. Materiał wideo może być bardzo duży; śledzenie i eksport są czasochłonne i wykorzystują CPU.
- **Podgląd podczas odtwarzania nie odtwarza dźwięku**. Eksport ma ścieżkę audio.
- Eksport klatek jest realizowany według FPS źródła; najlepszą zgodność dźwięku mają materiały ze **stałą liczbą klatek na sekundę (CFR)**.
- Automatyczna detekcja twarzy opiera się na klasycznym kaskadowym detektorze i wymaga sprawdzenia masek. Śledzenie może się pomylić przy zasłonięciu obiektu lub gwałtownym ruchu.
- Projekty przechowują **bezwzględną ścieżkę filmu** (przy przenoszeniu projektu wskaż plik ponownie).
- Nie ma podpisu kodu; Windows SmartScreen może wyświetlać ostrzeżenie o nieznanym wydawcy.
- **Nie potwierdzono działania gotowego `.exe` na rzeczywistym Windows** — testy przeprowadzono w Linux (szczegóły w `TEST_REPORT.md`).

## Testy lokalne (dla programistów)

```
python -m pip install -r requirements.txt pytest
python -m pytest -q tests
```

Testy GUI (Linux z serwerem X): `xvfb-run -a python tests/gui_smoke.py` oraz `xvfb-run -a python tests/gui_full_smoke.py`.
