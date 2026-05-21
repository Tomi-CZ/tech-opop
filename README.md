# TECH OPOP - Integrace pro Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![Project Maintenance][maintenance-shield]][maintainer]

Integrace Home Assistant pro kotle **OPOP Biopel** komunikující přes cloudové API [emodul.eu](https://emodul.eu).

Vyvinuto a testováno na kotli **OPOP Biopel mini** s typem kontroléru **ST-581v9**. Může fungovat i s jinými modely kotlů řady OPOP Biopel - hlášení o funkčnosti vítána.

## Funkce

- Konfigurace přes UI
- Tile senzory (teploty, tlaky, stavy) s automatickým pojmenováním z eModul API
- Climate entity reprezentující topné zóny
- Menu entity (tlačítka, čísla, výběry, přepínače) pro parametry kotle
- Podpora sekcí menu chráněných PINem (servisní menu, kalibrace podavače) přes options flow
- Stabilní `entity_id` odvozené z ID dlaždice/menu a slugu názvu

**Platformy:**

| Platforma       | Popis                                        |
| --------------- | -------------------------------------------- |
| `sensor`        | Tile senzory (teploty, stavy, ...)           |
| `binary_sensor` | Binární tile senzory                         |
| `climate`       | Termostaty topných zón                       |
| `button`        | Akční tlačítka menu                          |
| `number`        | Číselné parametry menu                       |
| `select`        | Výběrové parametry menu                      |
| `switch`        | Přepínačové parametry menu                   |

## Instalace

### HACS (doporučeno)

1. Otevři HACS → **Integrace** → menu (tři tečky) → **Vlastní repozitáře**.
2. Přidej `https://github.com/Tomi-CZ/tech-opop` jako typ **Integrace**.
3. Vyhledej `Tech OPOP` a nainstaluj.
4. Restartuj Home Assistant.
5. Jdi do **Nastavení → Integrace → Přidat integraci** a vyhledej `Tech OPOP`.
6. Zadej uživatelské jméno a heslo pro [emodul.eu](https://emodul.eu).
7. Vyber kontrolér, který chceš importovat.

### Manuální

1. Stáhni nebo naklonuj tento repozitář.
2. Zkopíruj `custom_components/tech_opop/` do adresáře s konfigurací HA pod `custom_components/`.
3. Restartuj Home Assistant.
4. Jdi do **Nastavení → Integrace → Přidat integraci** a vyhledej `Tech OPOP`.
5. Zadej uživatelské jméno a heslo pro [emodul.eu](https://emodul.eu).
6. Vyber kontrolér, který chceš importovat.

## Konfigurace - PINy chráněných menu

Některé sekce menu kotle jsou chráněny PINem (servisní menu, kalibrace podavače). PINy lze zadat po nastavení integrace:

1. Jdi do **Nastavení → Integrace → Tech OPOP → Konfigurovat**.
2. Zadej známé PINy:
   - **PIN servisního menu** - MS root (`group_id=0`)
   - **PIN kalibrace podavače** - MI (`group_id=30297`)
   - **PIN menu ventilátoru** - MS (`group_id=30350`)
3. Klikni na **Odeslat**. Integrace použije PINy při příštím obnovení dat.

## Správce

[@Tomi-CZ](https://github.com/Tomi-CZ)

---

# TECH OPOP - Integracja dla Home Assistant

Integracja Home Assistant dla kotłów **OPOP Biopel** komunikująca przez chmurowe API [emodul.eu](https://emodul.eu).

Opracowana i przetestowana na kotle **OPOP Biopel mini** z typem sterownika **ST-581v9**. Może działać również z innymi modelami kotłów serii OPOP Biopel - zgłoszenia o działaniu są mile widziane.

## Funkcje

- Konfiguracja przez UI
- Czujniki kafelkowe (temperatury, ciśnienia, stany) z automatycznym nazewnictwem z API eModul
- Encje Climate reprezentujące strefy grzewcze
- Encje menu (przyciski, liczby, wybory, przełączniki) dla parametrów kotła
- Obsługa sekcji menu chronionych PIN-em (menu serwisowe, kalibracja podajnika) przez options flow
- Stabilne `entity_id` oparte na ID kafelka/menu i slugu nazwy

**Platformy:**

| Platforma       | Opis                                         |
| --------------- | -------------------------------------------- |
| `sensor`        | Czujniki kafelkowe (temperatury, stany, ...) |
| `binary_sensor` | Binarne czujniki kafelkowe                   |
| `climate`       | Termostaty stref grzewczych                  |
| `button`        | Przyciski akcji menu                         |
| `number`        | Numeryczne parametry menu                    |
| `select`        | Parametry wyboru menu                        |
| `switch`        | Parametry przełącznika menu                  |

## Instalacja

### HACS (zalecane)

1. Otwórz HACS → **Integracje** → menu (trzy kropki) → **Niestandardowe repozytoria**.
2. Dodaj `https://github.com/Tomi-CZ/tech-opop` jako typ **Integracja**.
3. Wyszukaj `Tech OPOP` i zainstaluj.
4. Uruchom ponownie Home Assistant.
5. Przejdź do **Ustawienia → Integracje → Dodaj integrację** i wyszukaj `Tech OPOP`.
6. Wprowadź nazwę użytkownika i hasło do [emodul.eu](https://emodul.eu).
7. Wybierz sterownik, który chcesz zaimportować.

### Ręczna

1. Pobierz lub sklonuj to repozytorium.
2. Skopiuj `custom_components/tech_opop/` do katalogu konfiguracji HA w folderze `custom_components/`.
3. Uruchom ponownie Home Assistant.
4. Przejdź do **Ustawienia → Integracje → Dodaj integrację** i wyszukaj `Tech OPOP`.
5. Wprowadź nazwę użytkownika i hasło do [emodul.eu](https://emodul.eu).
6. Wybierz sterownik, który chcesz zaimportować.

## Konfiguracja - PINy chronionych menu

Niektóre sekcje menu kotła są chronione PINem (menu serwisowe, kalibracja podajnika). PINy można wprowadzić po skonfigurowaniu integracji:

1. Przejdź do **Ustawienia → Integracje → Tech OPOP → Konfiguruj**.
2. Wprowadź znane PINy:
   - **PIN menu serwisowego** - MS root (`group_id=0`)
   - **PIN kalibracji podajnika** - MI (`group_id=30297`)
   - **PIN menu wentylatora** - MS (`group_id=30350`)
3. Kliknij **Zatwierdź**. Integracja użyje PINów przy następnym odświeżeniu danych.

## Opiekun

[@Tomi-CZ](https://github.com/Tomi-CZ)

---

# TECH OPOP - Home Assistant Integration

Home Assistant integration for **OPOP Biopel** pellet boilers, communicating via the [emodul.eu](https://emodul.eu) cloud API.

Developed and tested on **OPOP Biopel mini** with controller type **ST-581v9**. May work with other OPOP Biopel boiler models - feedback welcome.

## Features

- Configuration through UI
- Tile sensors (temperatures, pressures, states) with automatic naming from eModul API
- Climate entities representing heating zones
- Menu entities (buttons, numbers, selects, switches) for boiler parameters
- Support for PIN-protected menu sections (service menu, feeder calibration) via options flow
- Stable `entity_id` based on tile/menu ID and name slug

**Platforms:**

| Platform        | Description                              |
| --------------- | ---------------------------------------- |
| `sensor`        | Tile sensors (temperatures, states, ...) |
| `binary_sensor` | Binary tile sensors                      |
| `climate`       | Heating zone thermostats                 |
| `button`        | Menu action buttons                      |
| `number`        | Numeric menu parameters                  |
| `select`        | Select menu parameters                   |
| `switch`        | Switch menu parameters                   |

## Installation

### HACS (recommended)

1. Open HACS → **Integrations** → menu (three dots) → **Custom repositories**.
2. Add `https://github.com/Tomi-CZ/tech-opop` as type **Integration**.
3. Search for `Tech OPOP` and install.
4. Restart Home Assistant.
5. Go to **Settings → Integrations → Add Integration** and search for `Tech OPOP`.
6. Enter your [emodul.eu](https://emodul.eu) username and password.
7. Select the controller to import.

### Manual

1. Download or clone this repository.
2. Copy `custom_components/tech_opop/` into your HA configuration directory under `custom_components/`.
3. Restart Home Assistant.
4. Go to **Settings → Integrations → Add Integration** and search for `Tech OPOP`.
5. Enter your [emodul.eu](https://emodul.eu) username and password.
6. Select the controller to import.

## Configuration - Protected Menu PINs

Some boiler menu sections are PIN-protected (service menu, feeder calibration). You can enter the PINs after setup:

1. Go to **Settings → Integrations → Tech OPOP → Configure**.
2. Enter the known PINs:
   - **Service menu PIN** - MS root (`group_id=0`)
   - **Feeder calibration PIN** - MI (`group_id=30297`)
   - **Fan menu PIN** - MS (`group_id=30350`)
3. Click **Submit**. The integration will use the PINs on next data refresh.

## Maintainer

[@Tomi-CZ](https://github.com/Tomi-CZ)

## Based on

This integration is a fork of [tech-controllers](https://github.com/mariusz-ostoja-swierczynski/tech-controllers) by [@mariusz-ostoja-swierczynski](https://github.com/mariusz-ostoja-swierczynski) and contributors including [@anarion80](https://github.com/anarion80), [@MichalKrasowski](https://github.com/MichalKrasowski), [@micles123](https://github.com/micles123), [@nedyarrd](https://github.com/nedyarrd) and others.

Many thanks to all original authors for their work.

## Disclaimer

This integration is not supported or endorsed by TECH Sterowniki sp. z o.o. or OPOP s.r.o.

## License

Released under the [MIT](LICENSE) license.

---

[releases-shield]: https://img.shields.io/github/v/release/Tomi-CZ/tech-opop.svg?style=for-the-badge
[releases]: https://github.com/Tomi-CZ/tech-opop/releases
[license-shield]: https://img.shields.io/github/license/Tomi-CZ/tech-opop?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Tomi--CZ-blue.svg?style=for-the-badge
[maintainer]: https://github.com/Tomi-CZ
