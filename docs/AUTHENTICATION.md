# Uwierzytelnianie / Authentication

Aktualna wersja nie ma logowania Google. Audyt nie wykazał oficjalnego OAuth scope
przeznaczonego do odczytu lokalizacji konta Find Hub. Nieoficjalne przepływy
pozyskują cookie/tokeny o szerokim zakresie i wymagają odszyfrowania materiału
kluczowego konta, więc helper i runtime Google pozostają **BLOCKED**.

UI przyjmuje jedynie nowe lokalne hasło Vault. Nie podawaj hasła Google, cookie,
tokenów, pliku `secrets.json` ani kluczy w UI, terminalu agenta, issue lub czacie.
W stanie LOCKED coordinator nie odpytuje adaptera i nie publikuje świeżych danych.

Przyszły helper musi być osobnym, ręcznie uruchamianym programem na zaufanym
urządzeniu użytkownika; używać wspieranego mechanizmu o minimalnym zakresie;
zapisywać wynik bez stdout; importować go bezpośrednio do Vault; usuwać kopie
tymczasowe i nigdy nie być zależnością runtime. Zwykłe usunięcie na SSD nie jest
gwarantowanym fizycznym wymazaniem.

No unattended mode is implemented. Storing a decryption key next to ciphertext
would not provide meaningful encryption at rest.

