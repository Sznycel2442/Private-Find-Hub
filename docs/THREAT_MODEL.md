# Model zagrożeń / Threat model

## Chronione zasoby / Protected assets

Materiał uwierzytelniający, klucze urządzeń, współrzędne, czas raportów, lista
urządzeń oraz relacje między nimi. Historia lokalizacji nie jest tworzona przez
integrację.

## Zagrożenia i zabezpieczenia / Threats and controls

| Zagrożenie | Zabezpieczenie | Ryzyko pozostałe |
|---|---|---|
| Kradzież pliku Vault | Argon2id + AES-GCM, brak hasła na dysku | słabe hasło, przejęty proces/host |
| Modyfikacja ciphertextu | AEAD i AAD, fail closed | odmowa usługi |
| Wyciek przez Recorder | PrivacyGate i kontrola każdej encji | dane wcześniej rozesłane przez HA |
| SSRF/redirect | HTTPS, port 443, allowlista hostów, kontrola każdego redirectu | przyszła błędna allowlista |
| Wyciek w logach/diagnostyce | typowane błędy, redakcja, diagnostyka allowlist-only | zewnętrzne komponenty HA |
| Złośliwa zależność | minimalne piny, `pip-audit`, niezmienne SHA Actions | kompromitacja registry lub utrzymującego |
| Fałszywy/stary fix | walidacja UTC/GPS/NaN, AEAD, brak downgrade, próg dokładności | prawidłowo podpisany błędny raport |
| Nieoficjalne API | adapter produkcyjny zablokowany | zmiana polityki/protokołu Google |
| Publiczna mapa/telemetria | brak panelu mapy, kafelków i telemetryki | użytkownik może dodać własną mapę |

Administrator HA i host są granicą zaufania. Złośliwy administrator, root,
przejęty frontend, automatyzacja lub backup mogą odczytać już opublikowane dane.
Integracja nie zapewnia poufności wobec tych podmiotów.

The security claim covers this integration's own storage, network policy and
publication gate. It does not make Home Assistant a multi-tenant secret boundary.

