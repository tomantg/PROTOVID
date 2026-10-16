# PROTOVID — raport weryfikacji

**System testowy:** Linux x86_64, Python 3, OpenCV, Tkinter, FFmpeg/libx264, pytest, Xvfb. **Nie Windows.**

- **PASS:** kompilacja składni obu modułów.
- **PASS:** regulacja siły Gaussian — porównanie dwóch ustawień, spadek wariancji obrazu przy silniejszym rozmyciu.
- **PASS:** pikselizacja Mosaic — różne ustawienia dają różny wynik.
- **PASS:** niezmienność obrazu poza maską.
- **PASS:** interpolacja manualnych klatek kluczowych z korektami toru śledzenia.
- **PASS:** korelacja fazowa + dopasowanie kontrastowe na przesuniętym obrazie syntetycznym.
- **PASS:** śledzenie rzeczywistej sekwencji zapisanych klatek z manualną kotwicą.
- **PASS:** operacje cięcia, przestawiania i walidacji fragmentów.
- **PASS:** kodowanie nowego MP4 (H.264) z nałożoną maską, przestawionymi fragmentami oraz dźwiękiem AAC; ffprobe wykrył obie ścieżki; zgadza się liczba klatek.
- **PASS:** uruchomienie GUI pod wirtualnym ekranem; wczytanie filmu, regulacja blur, klatka kluczowa, cięcie, zamiana fragmentów, render podglądu.
- **PASS:** pełny test scenariusza GUI: automatyczne śledzenie, klatka kluczowa, cięcie, zmiana kolejności, zapis i ponowne wczytanie projektu oraz końcowy eksport z dźwiękiem.
- **NIE PRZETESTOWANO:** binarnego `PROTOVID.exe` w Windows, podpisu/SmartScreen, rzeczywistego działania eksportu na instalacji Windows, kompatybilności ze wszystkimi formatami i nagraniami o zmiennym FPS.

**Wniosek:** silnik i funkcjonalne przepływy GUI są przetestowane w Linux. Wersja Windows zawiera narzędzia do zbudowania pliku EXE na prawdziwym Windows, lecz gotowy EXE nie jest częścią tego archiwum.
