# Plan testów / Test plan

## Automatyczne / Automated

Jedno polecenie `python -m pytest` sprawdza AEAD i tampering, walidację czasu i
GPS, brak downgrade fixu, częściową awarię wielu tagów, Vault locked/unlock,
rotację i plaintext, PrivacyGate, redakcję, politykę sieciową, zablokowany adapter
Google, manifest, tłumaczenia i skan sekretów. CI dodatkowo uruchamia ruff, mypy,
coverage ≥85%, `pip-audit` i kontrolę repozytorium.

## Manualne E2E — warunek odblokowania adaptera

1. Użytkownik potwierdza tag we własnej oficjalnej aplikacji Find Hub.
2. Audytowana autoryzacja odbywa się lokalnie, interaktywnie, bez ujawniania sekretów.
3. Ruch jest rejestrowany lokalnie i ograniczony do zatwierdzonej allowlisty; brak
   przekierowań, telemetryki, map i pośrednika.
4. Pozycja i rzeczywisty `observed_at` są orientacyjnie porównane z aplikacją.
5. Testowane są: dwa tagi, brak raportu, tampering, zły klucz, 429/backoff, timeout,
   restart, LOCKED, reauth, rotacja, zmiana listy oraz brak duplikatów.
6. Włączenie Recorder natychmiast zamyka PrivacyGate; baza i backup są sprawdzone.
7. Odłączenie sieci zachowuje jedynie wiek ostatniego fixu w pamięci, bez udawania
   świeżości. Test geofence odrzuca stary lub niedokładny pomiar.

Wyniki zapisuje się bez tokenów, identyfikatorów i współrzędnych. Dopiero pełny
wynik pozytywny pozwala zmienić status z BLOCKED.

