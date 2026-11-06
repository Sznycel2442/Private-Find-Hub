# Prywatność / Privacy

Domyślny STRICT zaczyna w stanie `locked`. Po odblokowaniu współrzędne nadal są
blokowane, aż Recorder jest nieobecny, wszystkie konkretne encje są zweryfikowane
jako wykluczone albo administrator jawnie zaakceptuje stan nieweryfikowalny.
Potwierdzone objęcie choć jednej encji przez Recorder zawsze zamyka bramkę.

Integracja zachowuje ostatni wiarygodny fix wyłącznie w pamięci procesu, nie
zapisuje cache pozycji, historii ani map. Po restarcie nie ma starego fixu.
Diagnostyka zawiera tylko liczniki i klasy stanów; nie zawiera GPS, identyfikatorów
tagów, adresu konta ani sekretów.

Wykluczenia oparte na globach mogą przestać działać po zmianie nazw encji. Po
każdej zmianie sprawdź Recorder oraz usuń istniejące rekordy zgodnie z dokumentacją
HA. Backup Vault nadal jest wrażliwy mimo szyfrowania; chroń host, dysk i backupy.

STRICT prevents new publication but cannot retract coordinates already consumed
by dashboards, mobile apps, automations or other integrations. Do not expose
trackers to untrusted HA users. Avoid external map tiles and cloud dashboards.

