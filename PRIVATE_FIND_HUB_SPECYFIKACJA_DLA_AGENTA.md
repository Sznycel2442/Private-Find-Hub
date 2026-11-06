# PRIVATE FIND HUB — SPECYFIKACJA WYKONAWCZA DLA AGENTA

**Wersja:** 1.0  
**Data weryfikacji założeń:** 2026-11-06  
**Status:** projekt do implementacji, nie gotowa integracja  
**Język interfejsu i dokumentacji:** polski + angielski  
**Platforma docelowa:** Home Assistant Core, instalacja jako custom integration / HACS  
**Priorytet:** bezpieczeństwo i prywatność > poprawność > niezawodność > funkcje dodatkowe

## 0. Instrukcja nadrzędna dla agenta

Jesteś starszym programistą Python i Home Assistant, architektem bezpieczeństwa i audytorem prywatności. W istniejącym repozytorium utwórz kompletną, testowalną, możliwą do audytu integrację o domenie `private_find_hub`. Nie ograniczaj się do opisu: przygotuj kod, testy, konfigurację CI, instrukcję instalacji i dokumenty bezpieczeństwa. Pracuj etapami. Nigdy nie udawaj działania rzeczywistego Google Find Hub, jeżeli połączenie nie zostało potwierdzone na prawdziwym urządzeniu. Nie pytaj o hasło Google, cookies, tokeny, klucze szyfrujące ani plik `secrets.json` w czacie, terminalu agenta ani w issue. Wszystkie czynności na żywym koncie użytkownik wykonuje interaktywnie na swoim zaufanym komputerze.

Na początku oceń wykonalność, aktualne implementacje i licencje. Jeśli bieżący nieoficjalny protokół nie działa albo nie można go użyć bez nieakceptowalnego ryzyka, dostarcz bezpiecznie działający szkielet i adapter mock wraz z czytelnym raportem blokera — nie obchodź zabezpieczeń Google.

## 1. Cel i granice projektu

**Cel:** odczyt ostatnich znanych lokalizacji lokalizatorów BLE zgodnych z siecią Google Find Hub, należących do zalogowanego użytkownika, przez zaszyfrowany kanał z Google; lokalne odszyfrowanie; publikacja kontrolowanych encji w Home Assistant.

**W zakresie MVP:**

- Jeden własny, autoryzowany profil Google; wiele tagów na tym koncie.
- Pobranie listy tagów oraz ich ostatniej dostępnej pozycji.
- Lokalna deszyfracja E2EE raportów, o ile aktualny protokół i uzyskane legalnie klucze na to pozwalają.
- `device_tracker` dla każdego tagu oraz diagnostyczne sensory czasu ostatniej detekcji, wieku danych, dokładności (gdy jest znana), stanu świeżości oraz kondycji połączenia.
- Konfiguracja i ponowne uwierzytelnienie przez UI Home Assistant, przy czym bootstrap Google może wymagać odizolowanego narzędzia uruchomionego lokalnie przez użytkownika.
- Mechanizm blokady prywatności przed pierwszą publikacją współrzędnych.
- Bezpieczne odświeżanie danych, kontrola błędów, testy, dokumentacja, HACS.

**Poza MVP:** sterowanie dźwiękiem, tworzenie tagów, BLE triangulacja, własne serwery map, historia śladów, eksport GPS, MQTT, Webhook, powiadomienia push, inne chmury, udostępnianie map publicznymi linkami. Nie dodawaj ich bez osobnego przeglądu bezpieczeństwa.

**Zakazy:** skryte śledzenie cudzych tagów; obchodzenie ostrzeżeń anty-stalkingowych; przejmowanie cudzych kont lub sesji; wyłączanie weryfikacji TLS; omijanie CAPTCHA, 2FA lub atestacji urządzenia; wysyłanie tokenów do pośredników; niejawne modyfikowanie `configuration.yaml`; telemetryka i automatyczne zgłaszanie wyjątków do usług zewnętrznych.

## 2. Fakty i zależności zewnętrzne

1. Google Find Hub wykorzystuje szyfrowanie end-to-end raportów lokalizacyjnych i sieć urządzeń Android do wykrywania tagów. Nie jest to GPS w czasie rzeczywistym; raporty mogą być opóźnione lub nieobecne.
2. Dokumentacja Google dla producentów akcesoriów opisuje protokół tagów, a nie publiczne API odczytu pozycji konta dla Home Assistant. Nie zakładaj istnienia oficjalnego, wspieranego API użytkownika.
3. Przeanalizuj, ale **nie ufaj bez audytu** projektom:
   - https://github.com/BSkando/GoogleFindMy-HA (GPL-3.0 — sprawdź pełną licencję i bieżącą wersję),
   - https://github.com/leonboe1/GoogleFindMyTools (sprawdź licencję, zależności i bieżącą obsługę protokołu),
   - https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn,
   - https://developers.google.com/nearby/fast-pair/landing-page-find-hub.
4. Istniejące rozwiązania wykorzystują m.in. bootstrap w przeglądarce i poufne dane typu `shared_key`; nie kopiuj do MVP mapy udostępnianej długowiecznym tokenem ani nieprzejrzystych mechanizmów odświeżania sesji.
5. Jeśli wykorzystujesz czyjś kod, przestrzegaj jego licencji i atrybucji; nie nazywaj kodu niezależnym, jeżeli jest pochodny. W raporcie podaj dokładny commit/tag audytowanego upstreamu oraz własne zmiany.

## 3. Model bezpieczeństwa (obowiązkowy przed kodowaniem)

**Zasoby chronione:** dokładne współrzędne i czas lokalizacji; historia tras i strefy dom/praca; konto Google i pochodne tokeny; klucze do E2EE; identyfikatory tagów; kopie zapasowe.

**Potencjalne zagrożenia:** złośliwa zależność; złośliwy commit upstream; wyciek `secrets.json`; logi wyjątków z danymi; naruszenie konta HA; dostęp innych użytkowników HA do encji; dostęp do plików `.storage` i backupów; pomyłki w konfiguracji `recorder`; przekierowanie HTTP poza allowlistę; nieautoryzowany dashboard mapowy; map tiles wysyłające otoczenie lokalizacji do obcego dostawcy; przypadkowe udostępnienie danych przez automatyzacje; zmiany protokołu Google; błędny raport lokalizacji powodujący fałszywą automatyzację.

**Granice zaufania:** tag → cudze telefony Android → usługa Google (raport zaszyfrowany) → jedyny kontrolowany klient sieciowy → lokalny dekoder → pamięć procesu HA → encje HA → użytkownicy i automatyzacje HA. Bezpieczna integracja nie oznacza ochrony przed złośliwym administratorem lub przejęciem hosta; te ryzyka są jawnie opisane.

**Wymagania P0:**

- Wychodzący ruch runtime tylko do zweryfikowanych, potrzebnych hostów Google; brak własnego backendu, analytics, Sentry, zewnętrznych map i CDN.
- Wymagana walidacja certyfikatu TLS oraz nazw hostów; brak `verify=False`, brak downgrade do HTTP. Każde przekierowanie przechodzi ponowną kontrolę hosta/protokołu. Brak arbitralnych URL-i konfigurowanych przez użytkownika.
- Stały rejestr zależności, minimalny zestaw uprawnień i audyt pakietów; brak `curl | bash` i wykonywania kodu pobranego dynamicznie.
- Nie zapisuj haseł Google; nie wyświetlaj pełnych tokenów, cookies, kluczy i surowych raportów w logach, tracebackach, diagnostyce, UI, testach ani raportach agenta.
- Usuń i redaguj poufne wartości także z wyjątków, nazw plików, nagłówków HTTP i URL-i. Diagnostyka domyślnie wyłączona; eksport wyłącznie z jawnie dozwolonymi polami.
- Żadnych publicznych endpointów mapy, REST, WebSocket, anonimowych linków, bearer tokenów w query string ani frontendowych skryptów z CDN.
- Konsekwentne `owner-only`: tylko urządzenia legalnie dostępne dla uwierzytelnionego właściciela; żadnych innych kont przez cookies przeglądarki.
- Bez prób obchodzenia kontroli Google, anti-stalking i rate-limitów.

## 4. Sekrety i uwierzytelnianie

### 4.1 Bootstrap (wyłącznie wykonywany przez użytkownika)

- Przed wykonaniem wybierz/audytuj aktualnie działającą metodę pozyskania danych dostępowych. Preferuj oficjalne OAuth, **jeśli istnieje wspierany zakres umożliwiający dokładnie ten odczyt**; nie imituj dostępności takiego zakresu. Jeśli brak, przygotuj osobny, odizolowany i jawnie oznaczony helper do interaktywnej autoryzacji na maszynie użytkownika.
- Bootstrap nie może wymagać wysyłania danych do autora projektu, GitHub Actions, hosta agenta ani serwera pośrednika. Narzędzie nie może ukradkiem czytać istniejących profili przeglądarki, zabijać innych sesji Chrome ani zapisywać haseł.
- Preferuj dedykowany profil przeglądarki i jednorazowy kontener z ograniczonym dostępem; jeśli narzędzie pomocnicze wystawia pulpit przez noVNC, bind do `127.0.0.1`, dostęp tylko przez tunel SSH/VPN, nigdy na publicznym interfejsie. Użytkownik musi widzieć i zatwierdzić logowanie.
- Nie zakładaj, że Google pozwala uzyskać klucze z innego hosta/IP; przetestuj zależność od źródła logowania i opisz ograniczenie.
- Wynik helpera zapisuj bez wypisywania na stdout, w bezpiecznym miejscu z dostępem tylko dla użytkownika. Po udanym imporcie wyczyść kopie tymczasowe w możliwym zakresie; jasno wyjaśnij, że zwykłe skasowanie pliku na SSD nie gwarantuje bezpowrotnego wymazania.
- Nie wysyłaj zawartości `secrets.json` do modelu AI. W testach używaj wyłącznie sztucznych danych.

### 4.2 Magazyn sekretów

Zaimplementuj warstwę `SecretVault` oddzieloną od transportu i UI:

- **Tryb STRICT — domyślny:** klucze i tokeny zaszyfrowane na dysku AEAD (np. AES-GCM lub ChaCha20-Poly1305 z dojrzałej biblioteki), klucz wyprowadzony z hasła użytkownika przez Argon2id z parametrami uzasadnionymi w dokumentacji. Hasło nie może być nigdzie utrwalane. Po każdym restarcie użytkownik musi odblokować vault z UI. W stanie locked nie wykonuj zapytań ani nie publikuj świeżych danych.
- **Tryb UNATTENDED — opcjonalny:** automatyczne uruchamianie jedynie z rzeczywiście niezależnym źródłem klucza (np. poprawnie chroniony magazyn systemowy, TPM lub świadomie skonfigurowany secret manager lokalny). Jeśli środowisko HA tego nie umożliwia, nie deklaruj szyfrowania-at-rest i nie włączaj takiego trybu przez pozorne szyfrowanie kluczem obok ciphertextu.
- Zwykły Home Assistant `.storage` nie jest z definicji szyfrowanym sejfem. W dokumentacji wymagaj ochrony hosta, dysku, uprawnień, kopii zapasowych. Traktuj szyfrowane kopie HA jako osobną warstwę ochrony.
- Stosuj unikalne nonce, integralność danych, wersjonowanie formatu, bezpieczną migrację oraz powiadomienie o uszkodzeniu sejfu. Nie zapisuj współrzędnych w vault.
- Rotacja/reautoryzacja atomowa; nie nadpisuj poprawnych tokenów przy przejściowej awarii sieci.
- Przy usunięciu integracji zaoferuj usunięcie sekretów i cache; nie obiecuj gwarantowanego fizycznego wymazania z SSD lub backupów.

## 5. Architektura

```
[Google Find Hub / Google FCM]
           | zaszyfrowany transport HTTPS (i ewentualne push)
           v
[GoogleTransport: allowlista, TLS, timeouts, retry, rate-limit]
           |
           v
[FindHubAdapter: prywatny protokół; izolacja od API HA]
           |
           v
[Decryptor: lokalne E2EE; tylko autoryzowane klucze]
           |
           v
[Normalizer + PrivacyFilter: sanity check, timestamp, accuracy]
           |
           v
[HA DataUpdateCoordinator / push event coordinator]
           |
           v
[PrivacyGate] --> [device_tracker + sensor + diagnostyka HA]
      ^
[SecretVault LOCKED/UNLOCKED]
```

Zalecane repozytorium:

```
custom_components/private_find_hub/
  __init__.py
  manifest.json
  const.py
  config_flow.py
  coordinator.py
  device_tracker.py
  sensor.py
  diagnostics.py
  repairs.py
  strings.json
  translations/pl.json
  translations/en.json
  api/client.py
  api/transport.py
  api/models.py
  api/exceptions.py
  api/decoder.py
  security/vault.py
  security/redaction.py
  security/network_policy.py
  privacy/gate.py
  privacy/validation.py
  privacy/recorder_checks.py
scripts/bootstrap/README.md
scripts/bootstrap/ (minimalny kod helpera, osobno od runtime HA)
tests/unit/
tests/integration/
tests/security/
tests/fixtures/ (wyłącznie syntetyczne dane)
docs/ARCHITECTURE.md
docs/THREAT_MODEL.md
docs/PRIVACY.md
docs/AUTHENTICATION.md
docs/TEST_PLAN.md
docs/KNOWN_LIMITATIONS.md
README.md
LICENSE
CHANGELOG.md
hacs.json
pyproject.toml
.github/workflows/ci.yml
```

Wymagania architektury: Python async, `DataUpdateCoordinator`, nowoczesne `ConfigFlow`/`OptionsFlow`/`reauth`, `ConfigEntryNotReady`, `ConfigEntryAuthFailed`, czyste wyładowanie (`async_unload_entry`), brak blokujących operacji w event loop, stabilne identyfikatory urządzeń (nie rotujące adresy BLE/MAC), możliwie proste zależności. Wersje HA i pakietów dobierz po sprawdzeniu aktualnej zgodności; zapisz minimalną wersję, pin/testuj zależności. Wydziel interfejs adaptera, by awaria nieoficjalnego protokołu nie wymagała zmian całej integracji.

## 6. Kontrakt danych

Wewnętrzny obiekt `LocationFix` ma minimum:

- `device_id`: stabilny identyfikator z konta Google, nie rotujący MAC;
- `latitude`, `longitude`: `float` zweryfikowane w granicach geograficznych;
- `observed_at`: rzeczywisty czas raportu po stronie sieci (UTC), jeśli znany;
- `retrieved_at`: czas pobrania przez HA (UTC), zawsze osobno;
- `accuracy_m`: `float | None`, tylko gdy dostawca rzeczywiście raportuje dokładność;
- `source_type`: np. `crowd_network`, `last_known` lub `unknown`, jeśli można wiarygodnie ustalić;
- `quality`: `fresh | aging | stale | unknown`; granice konfigurowalne;
- `report_id` lub hash deduplikacyjny, bez ujawniania surowych identyfikatorów w logach.

Waliduj NaN, infinities, brak daty, przyszły timestamp, brak współrzędnych, błędne dane binarne, poprawność i autentyczność kryptograficzną oraz ewentualne współrzędne podejrzane. Nie zamieniaj braku raportu w `(0,0)` ani w domową lokalizację. Nie myl czasu pobrania z czasem pomiaru. Nie zastępuj świeższego, wiarygodnego fixu starszym. Gdy nowy fix jest skrajnie niedokładny, nie wymuszaj geofence; pokaż stan `unknown`/diagnostykę zamiast nieuzasadnionej pewności.

Wartości startowe (do weryfikacji): `fresh <= 60 min`, `aging <= 6 h`, `stale > 6 h`. Dla automatyzacji strefowych ostrzegaj przed pojedynczym starym/nieprecyzyjnym pomiarem; przygotuj przykładowy filtr wieku i dokładności.

## 7. Encje i UI

- `device_tracker.private_find_hub_<slug>`: ostatnie znane współrzędne i metadane dokładności zgodne z kontraktem HA; tylko po otwarciu PrivacyGate.
- `sensor.<tag>_last_seen`: czas `observed_at`, o ile istnieje.
- `sensor.<tag>_location_age`: wiek raportu, bez udawania ciągłego pomiaru.
- `sensor.<tag>_location_quality`: fresh / aging / stale / unknown.
- `sensor.private_find_hub_connection_status`: connected / authentication_required / locked / rate_limited / unavailable; bez sekretów.
- Encja diagnostyczna licznika błędów może istnieć, ale nie powinna ujawniać pełnych URL ani danych lokalizacji.

Wszystkie encje muszą mieć stabilne `unique_id`, `device_info`, nazwy i tłumaczenia PL/EN. Urządzenia nie mogą zostać zdublowane po restarcie, reauth i odświeżeniu listy. Użytkownik może wybrać konkretne tagi; nie publikuj automatycznie wszystkich urządzeń, dopóki nie zaakceptuje ich w konfiguracji.

`ConfigFlow`: wprowadzenie, audytowane lokalne logowanie/import, weryfikacja dostępności, lista tagów, PrivacyGate, konfiguracja czasu aktualizacji, podsumowanie zgody. `OptionsFlow`: wybór tagów, częstotliwość, progi świeżości, tryb szyfrowania, tryb prywatności; zmiana trybu wymagająca osłabienia ochrony wymaga wyraźnego ostrzeżenia. Obsługa `reauth` i naprawy uszkodzonej konfiguracji.

## 8. Prywatność Home Assistant — krytyczna bramka

**Domyślnie nie twórz historii GPS.** `recorder` HA może zapisywać stany i atrybuty encji bez udziału integracji. Samo pominięcie zapisu w naszej bibliotece nie rozwiązuje problemu.

- Tryb STRICT (domyślny) nie publikuje współrzędnych dopóki administrator nie skonfiguruje i nie potwierdzi wykluczenia **wszystkich encji integracji** z `recorder`; gdzie jest dostępne stabilne API — weryfikuj filtr. Jeśli nie można zweryfikować skuteczności, pokaż stan „niezweryfikowane” i wymagaj jawnej akceptacji, nie deklaruj gwarancji.
- W UI pokaż do skopiowania poprawny fragment `recorder: exclude: entity_globs:` obejmujący `device_tracker.private_find_hub_*` i `sensor.private_find_hub_*`. Nie edytuj `configuration.yaml` automatycznie. Uwaga: zmiana nazw encji przez użytkownika może ominąć glob — wykrywaj to tam, gdzie jest możliwe, a w dokumentacji zalecaj wykluczenia po konkretnych encjach lub politykę przy zmianach.
- W trakcie działania obserwuj możliwe zmiany polityki `recorder`; jeśli można je wiarygodnie wykryć, zatrzymaj publikację współrzędnych w trybie STRICT. Zaznacz, że stan już wypchnięty do HA może nadal istnieć w innych integracjach i klientach.
- Wyłącz wszelkie wewnętrzne pliki historii, mapy, cache fixów, zapisywanie pozycji w logach i diagnostyce.
- Nie twórz własnych paneli mapowych w MVP. Standardowa mapa HA może pobierać kafelki od zewnętrznych dostawców; ujawnianie zakresu mapy jest osobnym ryzykiem. Mapę offline z lokalnymi kafelkami rozważ dopiero jako osobny moduł po audycie.
- Brak eksportu współrzędnych do zewnętrznych serwisów. Użytkownik musi wiedzieć, że automatyzacje, aplikacje mobilne, konta HA, REST/WebSocket HA, backupy i proxy mogą mieć dostęp do stanów zgodnie z ich uprawnieniami i konfiguracją.
- Jeśli administracja HA nie jest w pełni zaufana, nie można zagwarantować pełnej poufności lokalizacji w tej architekturze. Udokumentuj tę granicę wprost.

Przykład do dokumentacji (schemat wymagający potwierdzenia rzeczywistych entity_id):

```yaml
recorder:
  exclude:
    entity_globs:
      - "device_tracker.private_find_hub_*"
      - "sensor.private_find_hub_*"
```

Nie zapisuj geograficznych współrzędnych w długoterminowych statystykach. Wyraźnie odróżnij „brak historii w recorder” od „braku współrzędnych w bieżącym stanie HA”.

## 9. Sieć, aktualizacje i niezawodność

- Domyślny polling: ostrożny, np. co 15 minut; minimum i limit dopasuj do empirycznie potwierdzonych ograniczeń Google. Bez obietnic „real time”. Push/FCM tylko po audycie rzeczywistej implementacji, nie jako wymaganie MVP.
- Wspólny scheduler na konto; sekwencyjne lub ograniczone równoległe żądania; brak osobnych pętli dla każdego sensora.
- Zaimplementuj timeouty, backoff wykładniczy z jitterem, honorowanie `429` i `Retry-After` jeśli występuje, globalny limit żądań, deduplikację, politykę nienadmiernego ponawiania po `401/403`.
- Używaj strukturalnych typów błędów: auth vs przejściowy błąd sieci vs niezgodny protokół vs brak raportu vs błąd odszyfrowania. Nie uruchamiaj reauth tylko na podstawie dopasowania tekstu wyjątku.
- Zachowaj ostatni wiarygodny fix w **pamięci procesu** w czasie przejściowego problemu, ale pokaż jego wiek i jakość; po restarcie bez zaakceptowanego, świeżego raportu nie przedstawiaj starej pozycji jako bieżącej.
- Komenda odświeżenia na żądanie może istnieć tylko z cooldown i uwierzytelnionym dostępem HA; nie pozwalaj jej omijać limitów.
- Rejestruj tylko zdarzenia techniczne o niskiej czułości, np. `last_successful_sync` i klasę błędu; żadne adresy ani GPS.

## 10. Testy i CI (wymagane)

**Offline unit/integration:** `pytest` + testy HA z mockowanym backendem, `ruff`, `mypy`/pyright, `hassfest` jeśli środowisko dostępne, audyt zależności oraz skan sekretów w repozytorium. Sztuczne fixture'y, nigdy realne tokeny.

Scenariusze obowiązkowe:

1. Pierwsza konfiguracja, wykrycie wielu tagów, usunięcie, ponowny restart, reauth, brak duplikatów.
2. Zaszyfrowany poprawny raport → poprawne współrzędne; niepoprawny podpis/tag AEAD → odrzucenie bez publikacji.
3. `401`, `403`, `429`, błędy TLS, timeout, pusty raport, nieznana odpowiedź i zmiana schematu.
4. Brak możliwości połączenia przez dłuższy czas; brak spamowania Google i logów.
5. Daty w przyszłości, stare raporty, niska dokładność, niepoprawne geokoordynaty; brak fałszywej obecności w domu.
6. `SecretVault` locked po restarcie; brak sekretów w `.storage` w plaintext w trybie STRICT; brak hasła w config entry.
7. Odmowa hosta spoza allowlisty, przekierowanie HTTP i wyłączenie TLS.
8. Recorder nie wykluczony → PrivacyGate zamknięty; zaakceptowana i zweryfikowana polityka → publikacja; zmiana encji/konfiguracji → poprawna ponowna kontrola.
9. Diagnostyka, wyjątki, logi, debug, kopie testowe i nazwy URL nie zawierają kluczy, tokenów, e-maila ani współrzędnych.
10. Brak dodatkowego ruchu sieciowego poza dozwolonymi domenami po uruchomieniu; helper logowania wyłączony z runtime.
11. Odinstalowanie usuwa własne pliki i zatrzymuje połączenia, nie niszczy niezwiązanej konfiguracji.
12. Integracja zachowuje się poprawnie przy błędach pojedynczego tagu oraz przy wielu tagach naraz.

Pokrycie testami: minimum 85% kodu logicznego, maksymalnie pełne pokrycie ścieżek bezpieczeństwa i błędów. Testy odtwarzalne, możliwe do wykonania jednym poleceniem; CI bez dostępu do prawdziwego konta Google.

**Manualne E2E — wyłącznie na koncie użytkownika:** tag widoczny w oficjalnej aplikacji Google; użytkownik przeprowadza bootstrap bez przekazania sekretów; pozycja w HA zgadza się orientacyjnie z Find Hub i rzeczywistym czasem raportu; wyłączenie sieci i restart HA dają bezpieczne stany; połączenia sieciowe zweryfikowane; użytkownik sprawdza recorder, backupy i uprawnienia.

## 11. Fazy realizacji i kamienie milowe

**Faza A — audyt wykonalności (warunek dalszego rozwoju):** rozpoznaj aktualny mechanizm odczytu, dostępne upstreamy, licencję, wersje HA, potrzebne endpointy, ograniczenia Google, ryzyko przechwycenia sekretów. Wynik: `docs/FEASIBILITY.md` z datą, źródłami, hashami commitów i decyzją GO / BLOCKED. Nie używaj konta użytkownika w analizie repo.

**Faza B — repo, kontrakty i mock:** manifest, konfiguracja, tłumaczenia, API adaptera, modele, mock raportów, coordinator, podstawowe encje, testy. Instalowalny szkielet bez połączenia z Google. Mock nie może podszywać się pod produkcyjne dane.

**Faza C — uwierzytelnianie i vault:** helper, import danych, Strict Vault, odblokowanie po restarcie, rotacja, reauth, usuwanie sekretów, testy redakcji. Zatrzymaj integrację, jeśli aktualnej metody nie da się uzasadnić bezpieczeństwem.

**Faza D — realny odczyt i E2EE:** zaimplementuj lub odizoluj zweryfikowany adapter do protokołu Google; testy z nieprawdziwymi fixture'ami; ręczny E2E na jednym własnym tagu.

**Faza E — prywatność HA:** PrivacyGate, recorder checks, strefy/świeżość, bezpieczeństwo UI, brak mapy i publicznych endpointów, testy integracyjne.

**Faza F — wydanie:** CI, skan licencji i zależności, README, instrukcja HACS, instrukcja cofnięcia zmian, raport ograniczeń, wersja `0.1.0-alpha`; stabilne wydanie dopiero po realnym E2E.

## 12. Kryteria akceptacji (Definition of Done)

Projekt można oznaczyć „działa z Google Find Hub” **wyłącznie gdy wszystkie** warunki są spełnione:

- Instalacja w wspieranej wersji Home Assistant bez ręcznego poprawiania źródeł.
- Użytkownik sam uwierzytelnia własne konto bez dzielenia się hasłem lub sekretami z agentem.
- Co najmniej jeden rzeczywisty tag Google Find Hub został wykryty i poprawnie odszyfrowany; współrzędne i oryginalny czas obserwacji w HA odpowiadają rzeczywistemu raportowi.
- Lista tagów, reauth, restart i utrata łączności nie powodują wycieku ani udawania świeżych danych.
- Tryb STRICT uruchamia się jako LOCKED i wymaga odblokowania po restarcie; klucze nie leżą jako plaintext w magazynie integracji.
- Bez potwierdzonej polityki Recorder nie są emitowane współrzędne przez `device_tracker`.
- Brak nieautoryzowanego endpointu i niezależnej chmury; brak danych lokalizacji w logach i telemetryce; brak żądań do zewnętrznych kafelków map z poziomu integracji.
- CI przechodzi, raport zagrożeń i licencje są kompletnymi dokumentami; README uczciwie opisuje ryzyko nieoficjalnego API, HA i Google.

Jeśli nie można uzyskać realnego dostępu, stan pracy to **„bezpieczny prototyp z mockiem; Google adapter BLOCKED”**, a nie „gotowa integracja”. W raporcie podaj, co zostało wykonane, co nie zostało zweryfikowane i czego użytkownik musi dokonać ręcznie.

## 13. Wymagany format końcowego raportu agenta

1. Zrealizowane funkcje + krótkie demo konfiguracji.
2. Lista utworzonych plików i struktura repozytorium.
3. Źródła, wersje, licencje, użyty adapter oraz zakres audytu upstream.
4. Wyniki testów, linterów, statycznego skanowania, E2E i audytu egress.
5. Status każdej fazy (DONE / PARTIAL / BLOCKED) i konkretne ryzyka resztkowe.
6. Polecenia instalacji, odblokowania Vault, konfiguracji Recorder i odinstalowania.
7. Bezpieczna instrukcja, jak użytkownik może wykonać test z realnym tagiem, bez przesyłania poufnych danych do agenta.

## 14. Materiały odniesienia

- Google Security Blog, opis prywatności i E2EE: https://security.googleblog.com/2024/04/find-my-device-network-security-privacy-protections.html
- Google Find Hub Network accessory specification: https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn
- Google partner integration guide: https://developers.google.com/nearby/fast-pair/landing-page-find-hub
- GoogleFindMy-HA: https://github.com/BSkando/GoogleFindMy-HA
- GoogleFindMyTools: https://github.com/leonboe1/GoogleFindMyTools
- Home Assistant Config Flow: https://developers.home-assistant.io/docs/config_entries_config_flow_handler/
- Home Assistant data updates: https://contributors.home-assistant.io/architecture/core/data-updates/
- Home Assistant setup failures: https://contributors.home-assistant.io/core/integrations/setup-failures/
- Home Assistant Recorder: https://www.home-assistant.io/integrations/recorder/
- Home Assistant Backups: https://www.home-assistant.io/common-tasks/general/backups/

**Pierwsza czynność agenta:** utwórz `docs/FEASIBILITY.md`, sprawdź aktualny upstream i przygotuj decyzję GO / BLOCKED wraz z uzasadnieniem. Dopiero potem implementuj moduł autoryzacji i protokół. Nie wymagaj od użytkownika udostępniania sekretów.
