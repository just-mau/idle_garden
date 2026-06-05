# Idle Garden: Neue Verwerter hinzufuegen

Diese Datei beschreibt, wie du neue Verwerter wie Muehle, Brauerei oder Presse hinzufuegst.

## Ueberblick

Fuer einen neuen Verwerter brauchst du normalerweise nur:

1. Optional: ein neues Produkt in `PRODUCTS`
2. Einen Eintrag in `PROCESSORS`
3. Die `processor_id` in `PROCESSOR_ORDER`

Der Upgrade-Shop und der Laufzeit-State werden automatisch aus `PROCESSORS` und `PROCESSOR_ORDER` erzeugt.

---

## 1. Optional: Produkt anlegen

Wenn der Verwerter ein Produkt erzeugt, das im Inventar und Verkaufsshop auftauchen soll, ergaenze es in `PRODUCTS`:

```python
"flour": {
    "name": "Mehl",
    "sell_price": 3,
},
```

Und in `PRODUCT_ORDER`:

```python
PRODUCT_ORDER = ["flour"]
```

Wenn der Verwerter Gold erzeugt, brauchst du kein Produkt.

---

## 2. Verwerter in `PROCESSORS` anlegen

### Template mit Produkt-Output

```python
"processor_id": {
    "name": "Anzeigename",
    "base_price": 50,
    "inputs": [
        {
            "item_key": "wheat",
            "amount": 1,
        },
        {
            "item_key": "rye",
            "amount": 2,
        },
    ],
    "output": {
        "type": "item",
        "item_key": "flour",
        "amount": 2,
    },
    "duration": 60,
},
```

### Template mit Gold-Output

```python
"market_stall": {
    "name": "Marktstand",
    "base_price": 250,
    "inputs": [
        {
            "item_key": "grape",
            "amount": 3,
        },
    ],
    "output": {
        "type": "gold",
        "amount": 20,
    },
    "duration": 90,
},
```

---

## 3. Verwerter in `PROCESSOR_ORDER` eintragen

```python
PROCESSOR_ORDER = ["mill", "market_stall"]
```

Die Reihenfolge beeinflusst:

- Anzeige im Verwerter-Panel
- Reihenfolge im Upgrade-Shop
- Reihenfolge, in der automatische Verarbeitung startet

---

## Bedeutung der Felder

| Feld | Bedeutung |
| ---- | --------- |
| `processor_id` | Interner Name, z. B. `"mill"` oder `"market_stall"` |
| `name` | Anzeigename im Upgrade-Shop und Verwerter-Panel |
| `base_price` | Kaufpreis im Upgrade-Shop |
| `inputs` | Liste der benoetigten Materialien |
| `item_key` in `inputs` | Inventar-Key eines Saatguts, einer Feldfrucht oder eines Produkts |
| `amount` in `inputs` | Menge, die pro Verarbeitung verbraucht wird |
| `output.type` | `"item"` fuer Produkte/Inventar-Items oder `"gold"` fuer direkte Gold-Erzeugung |
| `output.item_key` | Inventar-Key des erzeugten Produkts, nur bei `"item"` |
| `output.amount` | Menge des Produkts oder Golds |
| `duration` | Dauer einer Verarbeitung in Sekunden |

---

## Beispiel: Muehle

```python
PRODUCTS = {
    "flour": {
        "name": "Mehl",
        "sell_price": 3,
    },
}

PRODUCT_ORDER = ["flour"]

PROCESSORS = {
    "mill": {
        "name": "Muehle",
        "base_price": 50,
        "inputs": [
            {
                "item_key": "wheat",
                "amount": 1,
            },
        ],
        "output": {
            "type": "item",
            "item_key": "flour",
            "amount": 2,
        },
        "duration": 60,
    },
}

PROCESSOR_ORDER = ["mill"]
```

---

## Checkliste

```text
[ ] Optional: Produkt in PRODUCTS ergaenzt
[ ] Optional: product_id in PRODUCT_ORDER ergaenzt
[ ] Eintrag in PROCESSORS ergaenzt
[ ] processor_id in PROCESSOR_ORDER ergaenzt
[ ] Spiel mit python3 main.py --dev getestet
```
