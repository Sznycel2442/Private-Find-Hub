# Zależności i licencje / Dependencies and licenses

Stan audytu: 2026-11-06. `pip-audit 2.10.1` dla `requirements-ci.txt`: **brak
znanych podatności**. Wynik jest chwilowy i CI powtarza kontrolę przy każdej zmianie.

| Pakiet | Wersja | Cel | Licencja upstream |
|---|---:|---|---|
| argon2-cffi | 25.1.0 | Argon2id Vault | MIT |
| cryptography | 50.0.2 | AES-GCM | Apache-2.0/BSD-3-Clause |
| Home Assistant | ≥2026.11.0 | platforma docelowa, nie vendored | Apache-2.0 |
| pytest | 9.2.0 | testy | MIT |
| coverage | 7.11.3 | pokrycie | Apache-2.0 |
| mypy | 1.18.2 | typowanie | MIT |
| ruff | 0.14.8 | lint | MIT |
| pip-audit | 2.10.1 | audyt podatności | Apache-2.0 |

`probatio` i `cryptography` są zapewniane przez środowisko Home Assistant; manifest
custom integration dodaje tylko dokładnie przypięty `argon2-cffi`. Wersje narzędzi
CI są przypięte, a GitHub Actions używają pełnych hashy commitów. Repozytorium nie
vendoryzuje i nie kopiuje kodu projektów GoogleFindMy-HA ani GoogleFindMyTools
(GPL-3.0); były one wyłącznie materiałem audytowym.

Licenses must be rechecked whenever a dependency or upstream source changes.

