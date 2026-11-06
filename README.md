# Private Find Hub

> **Status: bezpieczny prototyp z mockiem; Google adapter BLOCKED.** Wersja
> `0.1.0-alpha.1` nie loguje się do Google, nie odczytuje prawdziwych tagów i nie
> może być przedstawiana jako działająca integracja Google Find Hub.

Private Find Hub jest prywatną integracją Home Assistant przygotowaną wokół
kontraktu lokalnego odszyfrowywania raportów. Aktualny audyt nie znalazł
oficjalnego, wspieranego API konta do odczytu pozycji. Znane implementacje
wykorzystują nieoficjalne endpointy i materiał uwierzytelniający o zbyt szerokim
zakresie, dlatego adapter produkcyjny oraz helper logowania są celowo zablokowane.

Obecna wersja pozwala bezpiecznie ocenić architekturę: dwa jednoznacznie oznaczone
tagi `[MOCK]`, `device_tracker`, sensory diagnostyczne, asynchroniczny coordinator,
PrivacyGate i lokalny Vault STRICT. Mock nie wykonuje ruchu sieciowego.

## Instalacja / Installation

W HACS dodaj repozytorium jako **Custom repository → Integration**, zainstaluj
`Private Find Hub`, zrestartuj Home Assistant i wybierz **Ustawienia → Urządzenia
i usługi → Dodaj integrację**. Minimalna wersja to Home Assistant `2026.11.0`.
Ręcznie można skopiować katalog `custom_components/private_find_hub` do katalogu
`config/custom_components`.

Add the repository to HACS as **Custom repository → Integration**, install it,
restart Home Assistant, then use **Settings → Devices & services → Add
integration**. Home Assistant `2026.11.0` or newer is required.

Podczas konfiguracji tworzysz wyłącznie lokalne hasło Vault. Nigdy nie wpisuj w
integracji hasła Google, cookie, tokenu ani klucza. Hasło Vault nie jest zapisywane
i po każdym restarcie HA trzeba odblokować sejf w opcjach integracji.

## Recorder i prywatność / Recorder and privacy

Przed publikacją współrzędnych tryb STRICT wymaga skutecznego wykluczenia encji:

```yaml
recorder:
  exclude:
    entity_globs:
      - "device_tracker.private_find_hub_*"
      - "sensor.private_find_hub_*"
```

Po zmianie `entity_id` sprawdź wykluczenia ponownie. Integracja kontroluje
zarejestrowane encje przy każdym odświeżeniu i zamyka bramkę, jeżeli Recorder je
obejmuje. Standardowa mapa HA może wysyłać zakres mapy do dostawcy kafelków;
integracja nie dostarcza mapy ani publicznych endpointów.

STRICT mode checks every registered integration entity against Recorder before
publishing coordinates. An explicit acknowledgement only permits an unverified
result; it never overrides a confirmed inclusion in Recorder.

## Testy / Tests

```text
python -m pytest
ruff check custom_components tests
mypy
coverage run -m pytest
coverage report
python scripts/validate_repository.py
```

Testy używają wyłącznie danych syntetycznych. Ręczny E2E z własnym tagiem jest
warunkiem usunięcia statusu BLOCKED; procedura znajduje się w
[`docs/TEST_PLAN.md`](docs/TEST_PLAN.md).

## Usunięcie / Uninstall

Usuń wpis integracji w HA, następnie integrację w HACS i zrestartuj HA. Usunięcie
wpisu kasuje bieżący plik Vault, ale nie gwarantuje fizycznego wymazania danych z
SSD, snapshotów ani backupów. Usuń stare backupy świadomie i sprawdź bazę Recorder.

Szczegóły: [wykonalność](docs/FEASIBILITY.md),
[architektura](docs/ARCHITECTURE.md), [model zagrożeń](docs/THREAT_MODEL.md),
[prywatność](docs/PRIVACY.md), [uwierzytelnianie](docs/AUTHENTICATION.md),
[ograniczenia](docs/KNOWN_LIMITATIONS.md).

## License

Kod tego repozytorium jest niezależną implementacją na licencji GPL-3.0. Nie zawiera
kodu skopiowanego z audytowanych projektów GPL-3.0.

