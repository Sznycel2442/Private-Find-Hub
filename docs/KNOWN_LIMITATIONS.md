# Znane ograniczenia / Known limitations

- Google adapter i bootstrap są BLOCKED; dostępne są wyłącznie dane syntetyczne.
- Nie wykonano manualnego E2E z kontem Google ani prawdziwym tagiem.
- Nie potwierdzono produkcyjnych limitów API ani bezpiecznej metody autoryzacji.
- Brak trybu unattended, push/FCM, panelu mapy i lokalnej historii.
- PrivacyGate nie może cofnąć danych już odebranych przez inne elementy HA.
- Ochrona nie obejmuje przejętego hosta ani złośliwego administratora HA.
- Bezpieczeństwo kasowania nie obejmuje kopii SSD, snapshotów i backupów.
- Parametry Argon2id należy mierzyć na docelowym sprzęcie; obecne 64 MiB/t=3/p=1
  są konserwatywnym punktem startowym, nie uniwersalną gwarancją.
- Testy HA/hassfest muszą przejść w CI na docelowym Pythonie 3.14; lokalny audyt
  w tym środowisku użył Pythona 3.13 dla niezależnego kodu logicznego.

This alpha is suitable for architecture and privacy evaluation only, not for
real-world tracking or safety-critical automations.

