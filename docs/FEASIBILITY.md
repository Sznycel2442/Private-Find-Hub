# Private Find Hub — audyt wykonalności

Data audytu: 2026-11-06  
Zakres: Faza A specyfikacji 1.0  
Audyt wykonano bez konta Google, prawdziwych tokenów, cookies, kluczy i danych lokalizacyjnych.

## Decyzja

**BLOCKED — produkcyjny adapter Google i deklaracja „działa z Google Find Hub”.**

Na dzień audytu Google nie udostępnia publicznego, wspieranego API ani zakresu OAuth pozwalającego aplikacji Home Assistant pobrać listę należących do użytkownika tagów i ich zaszyfrowane raporty lokalizacji. Działające projekty społecznościowe używają nieudokumentowanych usług Google, imitują klienta Android oraz pozyskują tokeny i klucz `shared_key` przez interaktywny przepływ przeglądarkowy. Nie ma stabilnego kontraktu, gwarancji zgodności z warunkami usługi ani bezpiecznego mechanizmu unieważnienia całego przejętego materiału kluczowego.

**GO — niezależny szkielet, adapter mock, warstwa bezpieczeństwa i prywatności.**

Dozwolone są fazy B, C w zakresie lokalnego importu syntetycznego pakietu i Strict Vault, E oraz F. Adapter sieciowy Google pozostaje wyłączony i nie może być przedstawiany jako działający. Faza D może zawierać jedynie kontrakt adaptera, lokalny dekoder syntetycznych raportów i testy. Odblokowanie adaptera wymaga ponownego audytu, zaakceptowanej metody autoryzacji i ręcznego E2E użytkownika na własnym tagu.

## Podsumowanie dowodów

### Oficjalny stan Google

- [Find Hub Network Accessory Specification v1.3](https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn) opisuje zachowanie akcesorium BLE, kryptografię, GATT i zabezpieczenia DULT. Nie opisuje API konsumenckiego do odczytu pozycji z konta.
- [Partner Integration Guide](https://developers.google.com/nearby/fast-pair/landing-page-find-hub) mówi wprost, że Google nie zapewnia konkretnego SDK ani API dla tej integracji. Proces dotyczy producentów urządzeń, wymaga zatwierdzenia urządzenia, Model ID oraz umów z Google.
- [Google Security Blog](https://security.googleblog.com/2024/04/find-my-device-network-security-privacy-protections.html) potwierdza E2EE raportów, agregację, ochronę domu, throttling i rate limiting. Google deklaruje, że raport może odszyfrować właściciel lub osoba, której właściciel udostępnił tag.
- Nie znaleziono oficjalnego zakresu OAuth ani dokumentacji API umożliwiającej odczyt listy tagów lub raportów lokalizacji przez klienta Home Assistant.

Wniosek: specyfikacja akcesorium nie stanowi autoryzacji do wywoływania wewnętrznych usług konta. Nie należy utożsamiać publicznego opisu kryptografii tagu z publicznym API użytkownika.

### Audytowane upstreamy

| Projekt | Snapshot | Licencja | Ocena |
|---|---|---|---|
| [BSkando/GoogleFindMy-HA](https://github.com/BSkando/GoogleFindMy-HA) | `26a836da20d3a3f97fafd63ee2f7d27d1a83a5f6`, commit 2026-10-30 | plik `LICENSE`: GPL-3.0; `pyproject.toml`: sprzeczna deklaracja `MIT` | Nie kopiować bez wyjaśnienia licencji i pełnego audytu pochodzenia |
| [leonboe1/GoogleFindMyTools](https://github.com/leonboe1/GoogleFindMyTools) | `660be5395702ff7f1a6174f4ec4c865a57c7b527`, commit 2026-10-23 | GPL-3.0 | Eksperymentalny upstream referencyjny, nie biblioteka runtime |

Commity ustalono przez `git ls-remote`, następnie wykonano lokalny audyt płytkich kopii. Kod Private Find Hub ma być niezależną implementacją. Żaden plik upstreamu nie może być kopiowany bez osobnej decyzji licencyjnej, atrybucji i przeglądu bezpieczeństwa.

## Mechanizm stosowany przez upstreamy

1. Selenium z `undetected-chromedriver` otwiera `https://accounts.google.com/EmbeddedSetup`.
2. Narzędzie odczytuje cookie `oauth_token`, a `gpsoauth` wymienia je na token AAS i tokeny usług `android_device_manager` oraz `spot`.
3. Drugi interaktywny przepływ otwiera `https://accounts.google.com/encryption/unlock/android?kdi=...` i przechwytuje wynik interfejsu JavaScript `setVaultSharedKeys`, z którego wyprowadzany jest `shared_key`.
4. Lista urządzeń i działania są realizowane przez nieudokumentowane `https://android.googleapis.com/nova/...`.
5. Raporty i operacje FMDN korzystają z nieudokumentowanego gRPC `https://spot-pa.googleapis.com/google.internal.spot.v1.SpotService/...`.
6. Upstream używa także FCM/GCM, między innymi `android.clients.google.com`, `fcm.googleapis.com`, `fcmregistrations.googleapis.com` i `firebaseinstallations.googleapis.com`.
7. Odpowiedzi zawierają zaszyfrowane dane, które są lokalnie odszyfrowywane przy użyciu materiału właściciela.

To jest odtworzenie zachowania klienta Google, nie oficjalny OAuth dla integracji zewnętrznej. Zmiana schematu, atestacji, tokenów, powiązania IP lub polityki serwera może przerwać działanie bez uprzedzenia.

## Audyt bezpieczeństwa

### Uwierzytelnianie i sekrety

- `GoogleFindMyTools/Auth/token_cache.py` zapisuje `Auth/secrets.json` jako zwykły JSON, bez szyfrowania i bez jawnego ustawienia restrykcyjnych uprawnień pliku.
- `GoogleFindMy-HA` migruje tokeny i klucze do Home Assistant `Store`; są one utrwalane w `.storage`, ale nie są szyfrowane kluczem pochodzącym z hasła użytkownika.
- README `GoogleFindMy-HA` instruuje kopiowanie całej zawartości `secrets.json` do formularza HA i opisuje watcher plików z sekretami. To zwiększa liczbę miejsc, w których wrażliwy pakiet może trafić do schowka, logów UI, backupu lub naruszonego hosta.
- `shared_key` i później `owner_key` umożliwiają odszyfrowanie lokalizacji. Brak udokumentowanego przez Google sposobu niezależnej rotacji tych kluczy wymaga traktowania wycieku jako długotrwałego.
- Bootstrap zależy od Chrome/ChromeDriver i nieudokumentowanego `EmbeddedSetup`. `undetected-chromedriver` i automatyczne zarządzanie sterownikiem znacząco zwiększają łańcuch dostaw.
- Upstream wskazuje praktyczną zależność od publicznego IP/regionu logowania. Nie jest to oficjalny kontrakt i wymaga ręcznego potwierdzenia na środowisku użytkownika.

Wniosek: nie wolno importować tego mechanizmu do runtime Home Assistant. Ewentualny przyszły helper musi być oddzielny, interaktywny, lokalny, nie może odczytywać istniejących profili przeglądarki ani wypisywać sekretów i musi zapisywać wynik atomowo z prawami tylko dla użytkownika.

### Sieć i TLS

- Biblioteki upstreamów domyślnie korzystają z systemowej walidacji TLS; nie znaleziono aktywnego `verify=False`, `CERT_NONE` ani wyłączenia `check_hostname` w audytowanym runtime.
- `GoogleFindMyTools` nie ma centralnej polityki hostów. `requests.post` korzysta z domyślnego zachowania przekierowań, więc sam kod nie gwarantuje ponownej kontroli hosta każdego hopu.
- `GoogleFindMy-HA` wyłącza automatyczne przekierowania dla żądań Nova, ale cały projekt obejmuje wiele klientów i hostów, a nie pojedynczy kontrolowany transport.
- Integracja upstream ma widok mapy pobierający kafelki z `tile.openstreetmap.org` oraz lokalny endpoint historii. Jest to sprzeczne z wymaganiami Private Find Hub.
- FCM może wymagać dodatkowego stałego połączenia i portu TCP 5228. Push nie jest potrzebny w MVP i zwiększa powierzchnię egress.

Wniosek: przyszły transport musi mieć jedną zamkniętą allowlistę HTTPS, blokować przekierowania lub walidować każdy hop i nie może obsługiwać URL-i dostarczonych przez użytkownika. W prototypie mock cały egress pozostaje wyłączony.

### Prywatność Home Assistant

- Upstream publikuje GPS do encji, korzysta z danych Recorder i oferuje Map View/history. README potwierdza, że historia lokalizacji może znajdować się w `home-assistant_v2.db` i backupach.
- Map View pobiera publiczne kafelki OSM, ujawniając dostawcy zakres oglądanej mapy i pośrednio obszar lokalizacji.
- Samo nieprowadzenie własnego cache GPS nie zapobiega zapisowi aktualnych atrybutów encji przez Recorder.

Wniosek: Private Find Hub nie może dziedziczyć mapy ani historii upstreamu. W STRICT współrzędne pozostają nieopublikowane, dopóki PrivacyGate nie potwierdzi wykluczenia Recorder lub administrator jawnie nie zaakceptuje stanu „niezweryfikowane”.

### Zależności i podatności

Audyt wykonano `pip-audit 2.10.1` na zakresach zależności runtime z obu upstreamów, rozwiązanych 2026-11-06. Oba zestawy rozwiązały `ecdsa==0.19.2` i zostały oznaczone przez `PYSEC-2026-1325` / `CVE-2024-23342` / `GHSA-wj6h-64fc-37mp`: podatność czasowa Minerva dotycząca operacji P-256, bez dostępnej wersji naprawionej. W audytowanym `GoogleFindMy-HA` P-256 jest obsługiwane przez `cryptography`, a `python-ecdsa` służy głównie do arytmetyki SECP160R1, więc bezpośrednia wykorzystywalność tej konkretnej podatności nie została potwierdzona. Sama obecność zależności bez poprawki jest jednak nieakceptowalna dla nowego komponentu bezpieczeństwa bez zawężenia zastosowania lub usunięcia pakietu.

Dodatkowe problemy łańcucha dostaw:

- zależności upstreamów są deklarowane jako dolne granice `>=`, a manifest HA nie przypina wersji dokładnie, wbrew aktualnemu zaleceniu dokumentacji Home Assistant;
- `GoogleFindMyTools` wciąga ciężkie narzędzia o szerokich uprawnieniach, między innymi Selenium, `undetected-chromedriver` i Frida;
- brak lockfile w `GoogleFindMyTools` uniemożliwia odtwarzalną instalację;
- wynik audytu zależy od wersji rozwiązanych w dniu skanu i nie zastępuje skanu artefaktu wydania.

Private Find Hub nie będzie używać `ecdsa`, Frida, Selenium ani `undetected-chromedriver` w runtime. Dla Strict Vault wystarczy utrzymywana biblioteka `cryptography` oraz `argon2-cffi`, przypięte i ponownie audytowane w CI.

## Home Assistant i zgodność

- Aktualna stabilna linia w dniu audytu to Home Assistant 2026.11, opublikowana 2026-11-04: [release notes](https://www.home-assistant.io/blog/2026/11/04/release-202611).
- Implementacja prototypu będzie celować w `Home Assistant >= 2026.11.0` i Python `>= 3.14`.
- Konfiguracja będzie wyłącznie przez Config Flow/Options Flow; stabilny `unique_id` konta zapobiega duplikatom.
- Runtime ma używać `DataUpdateCoordinator`, rozróżniać błędy uwierzytelnienia, transportu i protokołu oraz poprawnie wyładowywać wpis.
- Manifest custom integration musi przypinać każdą zewnętrzną zależność do dokładnej wersji: [Home Assistant manifest requirements](https://contributors.home-assistant.io/core/integrations/manifest/#requirements).

## Warunki odblokowania adaptera Google

Wszystkie poniższe warunki są wymagane łącznie:

1. Google udostępni wspierane API użytkownika i odpowiedni zakres OAuth albo niezależny audyt prawny i bezpieczeństwa zaakceptuje konkretny lokalny mechanizm nieoficjalny.
2. Metoda nie omija 2FA, CAPTCHA, atestacji, rate limitów ani zabezpieczeń anti-stalking.
3. Bootstrap jest lokalny, interaktywny, odseparowany od HA i nie przekazuje sekretów autorowi, CI, agentowi ani pośrednikowi.
4. Lista dokładnych hostów, endpointów, zakresów tokenów i formatów odpowiedzi jest udokumentowana i pokryta testami blokującymi egress poza allowlistę.
5. Każda zależność kryptograficzna i bootstrapowa przechodzi audyt po przypięciu wersji; brak znanych, niewyjaśnionych podatności w używanych ścieżkach.
6. Użytkownik ręcznie potwierdzi E2E na własnym koncie i tagu: listę urządzeń, odszyfrowaną pozycję, oryginalny czas obserwacji, restart, reauth, utratę sieci i Recorder.
7. Wynik testu nie jest przesyłany do agenta; wystarcza lokalna checklista bez sekretów i dokładnych współrzędnych.

## Zakres dalszej implementacji

| Faza | Status po audycie | Dozwolony zakres |
|---|---|---|
| A | DONE | Ten dokument; ponowny audyt przed każdym realnym adapterem |
| B | GO | Instalowalny szkielet HA, kontrakty, adapter mock, encje i testy offline |
| C | PARTIAL | Strict Vault i syntetyczny import; helper Google pozostaje dokumentacyjnym stubem |
| D | BLOCKED | Brak wywołań Google; wyłącznie syntetyczny dekoder i interfejs adaptera |
| E | GO | PrivacyGate, walidacja Recorder, sanity checks i testy bezpieczeństwa |
| F | GO dla `0.1.0-alpha` | CI, dokumentacja, HACS/Marketplace; wyraźny status bezpiecznego prototypu |

## Ograniczenia audytu

- Nie wykonano logowania ani testu z prawdziwym tagiem.
- Nie wykonano analizy prawnej warunków korzystania z Google; brak oficjalnego API traktowany jest jako blokada techniczna i ryzyko zgodności, a nie rozstrzygnięcie prawne.
- Nie przeprowadzono dynamicznego przechwycenia ruchu upstreamu ani audytu całej historii commitów.
- `pip-audit` sprawdza znane publiczne podatności; nie wykrywa złośliwych pakietów ani błędów logicznych.
- Nowe commity upstreamu, zmiany Google lub nowe advisories unieważniają część ustaleń i wymagają ponownego audytu.

## Rejestr źródeł

- Google, Find Hub Network Accessory Specification v1.3: <https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn>
- Google, Partner Integration Guide: <https://developers.google.com/nearby/fast-pair/landing-page-find-hub>
- Google Security Blog, E2EE i zabezpieczenia sieci: <https://security.googleblog.com/2024/04/find-my-device-network-security-privacy-protections.html>
- Home Assistant 2026.11: <https://www.home-assistant.io/blog/2026/11/04/release-202611>
- Home Assistant Config Flow: <https://contributors.home-assistant.io/core/integrations/config-flow/>
- Home Assistant manifest: <https://contributors.home-assistant.io/core/integrations/manifest/>
- BSkando/GoogleFindMy-HA: <https://github.com/BSkando/GoogleFindMy-HA/tree/26a836da20d3a3f97fafd63ee2f7d27d1a83a5f6>
- leonboe1/GoogleFindMyTools: <https://github.com/leonboe1/GoogleFindMyTools/tree/660be5395702ff7f1a6174f4ec4c865a57c7b527>
- GHSA/CVE wskazane przez `pip-audit`: <https://github.com/advisories/GHSA-wj6h-64fc-37mp>
