# Architektura / Architecture

**Status:** `0.1.0-alpha.1`, mock-only, Google adapter BLOCKED.

Przepływ zaufania docelowego: tag → telefony Android → Google → adapter sieciowy
→ lokalny dekoder AEAD → pamięć procesu HA → PrivacyGate → encje HA. Obecny mock
zastępuje pierwsze cztery elementy i nie używa sieci.

- `api/`: modele, interfejs `FindHubAdapter`, izolacja błędów per tag, dekoder
  sztucznego AES-GCM, mock i jawnie blokujący adapter Google.
- `security/`: Vault Argon2id + AES-256-GCM, redakcja i polityka egress.
- `privacy/`: walidacja fixów, klasyfikacja świeżości i PrivacyGate Recorder.
- `coordinator.py`: jedyny cykl aktualizacji; brak zapytań w stanie LOCKED.
- platformy HA: stabilne identyfikatory oparte o niezmienny identyfikator mock,
  bez adresów BLE/MAC i bez lokalnej historii.

Vault używa Argon2id (`64 MiB`, `t=3`, `p=1`) i losowych 128-bitowych soli,
następnie AES-256-GCM z losowym nonce oraz AAD wiążącym wersję i `vault_id`.
Zapis jest atomowy i ma uprawnienia właściciela tam, gdzie system je egzekwuje.
Hasło nie trafia do config entry. Python nie pozwala zagwarantować wyzerowania
wszystkich niemutowalnych kopii w pamięci.

The adapter boundary prevents a future protocol change from affecting entity and
privacy code. A production adapter may be enabled only after the conditions in
`FEASIBILITY.md` and the manual E2E gate are satisfied.

