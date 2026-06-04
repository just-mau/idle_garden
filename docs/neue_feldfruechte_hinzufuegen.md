# Idle Garden: Neue Feldfrüchte hinzufügen

Diese Datei beschreibt alle Stellen im aktuellen Code, die du anpassen musst, um neue Feldfrüchte wie Hopfen, Wein, Kürbis oder magische Pflanzen hinzuzufügen.

## Überblick

Für eine neue Feldfrucht brauchst du aktuell Anpassungen an vier Stellen:

1. `CROPS`
2. `CROP_ORDER`
3. `inventory`
4. `stats["harvested"]`

Danach funktionieren automatisch:

- Anzeige im Inventar
- Saatgut-Shop
- Verkaufsshop
- Feld-Manager
- Saat-Boy nach Feldtyp
- Erntehelfer
- Unlock-Hinweis
- Verkaufspreise
- Wachstumszeiten

---

## 1. Neue Feldfrucht in `CROPS` hinzufügen

Suche im Code nach:

```python
CROPS = {
```

Dort ergänzt du einen neuen Eintrag.

### Template ohne Unlock

Diese Feldfrucht ist sofort verfügbar:

```python
"crop_id": {
    "name": "Anzeigename",
    "seed_name": "Saatgutname",
    "seed_price": 10,
    "sell_price": 5,
    "symbol": "X",
    "growth_stage_1": 30,
    "growth_stage_2": 30,
},
```

### Template mit Unlock

Diese Feldfrucht wird erst freigeschaltet, wenn eine andere Frucht oft genug geerntet wurde:

```python
"crop_id": {
    "name": "Anzeigename",
    "seed_name": "Saatgutname",
    "seed_price": 10,
    "sell_price": 5,
    "symbol": "X",
    "growth_stage_1": 30,
    "growth_stage_2": 30,
    "unlock_crop": "wheat",
    "unlock_amount": 25,
},
```

### Bedeutung der Felder

| Feld             | Bedeutung                                                   |
| ---------------- | ----------------------------------------------------------- |
| `crop_id`        | Interner Name, z. B. `"hops"` oder `"grape"`                |
| `name`           | Name der geernteten Frucht                                  |
| `seed_name`      | Name des Saatguts                                           |
| `seed_price`     | Kaufpreis für 1 Saatgut                                     |
| `sell_price`     | Verkaufspreis für 1 geerntete Frucht                        |
| `symbol`         | Zeichen, das bei reifer Pflanze im Feld angezeigt wird      |
| `growth_stage_1` | Sekunden von Samen `,` zu Sprössling `i`                    |
| `growth_stage_2` | Sekunden von Sprössling `i` zu reifer Pflanze               |
| `unlock_crop`    | Welche Frucht geerntet werden muss, um diese freizuschalten |
| `unlock_amount`  | Wie oft diese Frucht insgesamt geerntet werden muss         |

---

## 2. Feldfrucht in `CROP_ORDER` eintragen

Suche:

```python
CROP_ORDER = ["wheat", "rye"]
```

Ergänze die neue `crop_id` in der gewünschten Reihenfolge:

```python
CROP_ORDER = ["wheat", "rye", "hops"]
```

Die Reihenfolge beeinflusst:

- Inventar-Anzeige
- Saatgut-Shop
- Verkaufsshop
- Feld-Manager
- Unlock-Reihenfolge

---

## 3. Inventory erweitern

Suche:

```python
inventory = {
```

Für jede neue Feldfrucht brauchst du zwei Einträge:

```python
"crop_id_seed": 0,
"crop_id": 0,
```

Beispiel für Hopfen:

```python
inventory = {
    "wheat_seed": 5,
    "wheat": 0,
    "rye_seed": 0,
    "rye": 0,
    "hops_seed": 0,
    "hops": 0,
}
```

---

## 4. Statistik erweitern

Suche:

```python
stats = {
    "harvested": {
```

Ergänze dort die neue Feldfrucht:

```python
"hops": 0,
```

Beispiel:

```python
stats = {
    "harvested": {
        "wheat": 0,
        "rye": 0,
        "hops": 0,
    }
}
```

Diese Statistik ist wichtig für Unlocks, weil sie zählt, wie oft eine Frucht insgesamt geerntet wurde, unabhängig davon, ob sie später verkauft wurde.

---

## Beispiel: Hopfen hinzufügen

### `CROPS`

```python
"hops": {
    "name": "Hopfen",
    "seed_name": "Hopfensamen",
    "seed_price": 20,
    "sell_price": 10,
    "symbol": "H",
    "growth_stage_1": 45,
    "growth_stage_2": 45,
    "unlock_crop": "rye",
    "unlock_amount": 25,
},
```

### `CROP_ORDER`

```python
CROP_ORDER = ["wheat", "rye", "hops"]
```

### `inventory`

```python
inventory = {
    "wheat_seed": 5,
    "wheat": 0,
    "rye_seed": 0,
    "rye": 0,
    "hops_seed": 0,
    "hops": 0,
}
```

### `stats`

```python
stats = {
    "harvested": {
        "wheat": 0,
        "rye": 0,
        "hops": 0,
    }
}
```

---

## Beispiel: Wein hinzufügen

### `CROPS`

```python
"grape": {
    "name": "Weintrauben",
    "seed_name": "Weinreben",
    "seed_price": 50,
    "sell_price": 25,
    "symbol": "G",
    "growth_stage_1": 60,
    "growth_stage_2": 60,
    "unlock_crop": "hops",
    "unlock_amount": 25,
},
```

### `CROP_ORDER`

```python
CROP_ORDER = ["wheat", "rye", "hops", "grape"]
```

### `inventory`

```python
"grape_seed": 0,
"grape": 0,
```

### `stats`

```python
"grape": 0,
```

---

## Beispiel: Magische Pflanze

### `CROPS`

```python
"moonflower": {
    "name": "Mondblume",
    "seed_name": "Mondsamen",
    "seed_price": 250,
    "sell_price": 150,
    "symbol": "*",
    "growth_stage_1": 120,
    "growth_stage_2": 120,
    "unlock_crop": "grape",
    "unlock_amount": 50,
},
```

---

## Balancing-Vorschlag

Eine einfache Progression könnte so aussehen:

| Frucht      | Gesamtwachstum | Saatpreis | Verkaufspreis | Unlock         |
| ----------- | -------------: | --------: | ------------: | -------------- |
| Weizen      |            30s |        3g |            2g | sofort         |
| Roggen      |            60s |        8g |            4g | 25 Weizen      |
| Hopfen      |            90s |       20g |           10g | 25 Roggen      |
| Weintrauben |           120s |       50g |           25g | 25 Hopfen      |
| Mondblume   |           240s |      250g |          150g | 50 Weintrauben |

---

## Wichtiger Hinweis zu `crop_id`

Die `crop_id` sollte kurz, eindeutig und klein geschrieben sein.

Gute Beispiele:

```python
"wheat"
"rye"
"hops"
"grape"
"moonflower"
```

Vermeide Leerzeichen oder Umlaute in der `crop_id`.

Nicht ideal:

```python
"wein trauben"
"MondBlume"
"goldene-karotte"
```

Besser:

```python
"grape"
"moonflower"
"golden_carrot"
```

---

## Optional: Dev-Modus erweitern

Wenn du neue Feldfrüchte im `--dev` Modus direkt testen möchtest, ergänze in `apply_dev_mode()`:

```python
inventory["hops_seed"] = 25
inventory["hops"] = 25
stats["harvested"]["rye"] = 25
```

Beispiel mit Hopfen-Unlock:

```python
def apply_dev_mode():
    global gold, shop_unlocked

    gold = 100000

    inventory["wheat_seed"] = 100
    inventory["wheat"] = 100
    inventory["rye_seed"] = 25
    inventory["rye"] = 25
    inventory["hops_seed"] = 25
    inventory["hops"] = 25

    stats["harvested"]["wheat"] = 25
    stats["harvested"]["rye"] = 25

    shop_unlocked = True
```

---

## Checkliste

Für jede neue Feldfrucht:

```text
[ ] Eintrag in CROPS ergänzt
[ ] crop_id in CROP_ORDER ergänzt
[ ] crop_id_seed in inventory ergänzt
[ ] crop_id in inventory ergänzt
[ ] crop_id in stats["harvested"] ergänzt
[ ] Optional: Dev-Modus erweitert
[ ] Spiel mit python3 main.py --dev getestet
```
