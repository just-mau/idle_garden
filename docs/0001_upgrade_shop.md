# Terminal Farm: Upgrade-Shop

Dieses Dokument beschreibt die Aenderungen nach `docs/0000_initial.md`.
Der neue Stand fuegt einen Upgrade-Shop, zwei kaufbare Helfer und Navigation
mit Pfeiltasten sowie `a`/`d` hinzu.

Die Idee: Gold soll nicht nur eine Zahl sein. Der Spieler kann es jetzt in
Upgrades investieren, die das Idle-Game staerker machen.

## Was neu ist

- Der Upgrade-Shop wird freigeschaltet, sobald der Spieler zum ersten Mal 10
  Gold erreicht.
- Ab dann erscheint rechts im Terminal ein Shop-Panel mit der kompletten
  Upgrade-Liste.
- Die Upgrade-Liste bleibt sichtbar, auch wenn der Shop-Fokus verlassen wird.
- Mit `u` wird der Shop-Fokus aktiviert oder verlassen.
- Im aktiven Shop kann man mit Pfeiltaste hoch/runter oder `a`/`d` navigieren.
- Der aktive Menuepunkt wird farbig markiert.
- Mit Enter oder Space wird das aktive Upgrade gekauft.
- Wenn das Gold nicht reicht, wird der Preis rot angezeigt und zeigt, wie viel
  Gold noch fehlt.
- Upgrades koennen mehrfach gekauft werden und zeigen danach `Lv. 1`, `Lv. 2`
  usw.
- Wenn ein Upgrade das Maximum erreicht, verschwindet der Preis und `Lv. Max`
  wird gruen angezeigt.

## Neue Upgrades

Aktuell gibt es zwei Upgrades:

| Upgrade | Startpreis | Effekt |
| --- | ---: | --- |
| Saat-Boy | 10 Gold | pflanzt alle 5 Sekunden einen Samen |
| Erntehelfer | 20 Gold | erntet alle 5 Sekunden ein erntereifes Feld |

Beide Upgrades sind mehrfach kaufbar. Jeder Kauf erhoeht das Level und damit
auch den Preis fuer den naechsten Kauf.

## Upgrade-Level

Die Level folgen aktuell diesem Muster:

| Level | Intervall | Aktionen pro Intervall |
| ---: | ---: | ---: |
| 0 | kein Upgrade aktiv | 0 |
| 1 | 5 Sekunden | 1 |
| 2 | 4 Sekunden | 1 |
| 3 | 3 Sekunden | 1 |
| 4 | 2 Sekunden | 1 |
| 5 | 1 Sekunde | 1 |
| 6 | 1 Sekunde | 2 |
| 7 | 1 Sekunde | 3 |
| 8 | 1 Sekunde | 4 |
| 9 | 1 Sekunde | 5 |

Level 9 ist das Maximum. Im Shop wird dann `Lv. Max` angezeigt. Der Preis
verschwindet, weil das Upgrade nicht weiter gekauft werden kann.

Fuer den Saat-Boy bedeutet "Aktionen": So viele Samen werden gepflanzt.
Fuer den Erntehelfer bedeutet "Aktionen": So viele erntereife Felder werden
geerntet.

Die Preise steigen linear:

```text
naechster Preis = Startpreis * (aktuelles Level + 1)
```

Beim Saat-Boy sind die Preise also 10g, 20g, 30g usw.
Beim Erntehelfer sind es 20g, 40g, 60g usw.

## Neue Bedienung

Ausserhalb des Shop-Fokus:

| Taste | Wirkung |
| --- | --- |
| `p` | Samen pflanzen |
| `h` | alle erntereifen Pflanzen ernten |
| `b` | normalen Samen fuer Gold kaufen |
| `u` | Upgrade-Shop bedienen, sobald freigeschaltet |
| `q` | Spiel beenden |

Im aktiven Shop:

| Taste | Wirkung |
| --- | --- |
| Pfeiltaste hoch | vorheriges Upgrade auswaehlen |
| Pfeiltaste runter | naechstes Upgrade auswaehlen |
| `a` | vorheriges Upgrade auswaehlen |
| `d` | naechstes Upgrade auswaehlen |
| Enter | aktives Upgrade kaufen |
| Space | aktives Upgrade kaufen |
| `u` | Shop-Fokus verlassen |
| `q` | Spiel beenden |

## Neue Konstanten

In `main.py` wurden neue Konstanten eingefuehrt:

```python
RED = "\033[31m"
CYAN = "\033[36m"
ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")
UPGRADE_UNLOCK_GOLD = 10
SAAT_BOY_INTERVAL = 5
HARVEST_HELPER_INTERVAL = 5
MIN_UPGRADE_INTERVAL = 1
MAX_UPGRADE_ACTIONS = 5
SHOP_PANEL_WIDTH = 42
```

`RED` wird genutzt, um Preise rot zu machen, wenn das Gold nicht reicht.
`CYAN` markiert den aktiven Eintrag im Upgrade-Shop.

`ANSI_ESCAPE` ist ein regulaerer Ausdruck. Er erkennt ANSI-Farbcodes in Texten.
Das ist wichtig, weil solche Codes im Terminal Farben erzeugen, aber keine
sichtbare Breite haben.

Die Balance-Werte:

- `UPGRADE_UNLOCK_GOLD = 10`: Ab 10 Gold wird der Shop freigeschaltet.
- `SAAT_BOY_INTERVAL = 5`: Der Saat-Boy handelt alle 5 Sekunden.
- `HARVEST_HELPER_INTERVAL = 5`: Der Erntehelfer handelt alle 5 Sekunden.
- `MIN_UPGRADE_INTERVAL = 1`: Schneller als 1 Sekunde werden Upgrades nicht.
- `MAX_UPGRADE_ACTIONS = 5`: Ein Upgrade kann maximal 5 Aktionen pro Intervall
  ausfuehren.
- `SHOP_PANEL_WIDTH = 42`: Das rechte Shop-Panel ist 42 Zeichen breit.

## Neuer Shop-Zustand

Das Spiel merkt sich jetzt mehr als nur Garten, Samen und Gold:

```python
shop_unlocked = False
shop_open = False
selected_upgrade = 0
```

Diese drei Variablen steuern den Shop:

- `shop_unlocked`: Wurde der Shop schon freigeschaltet?
- `shop_open`: Ist der Shop gerade im Bedien-Fokus?
- `selected_upgrade`: Welcher Upgrade-Eintrag ist aktuell markiert?

Der Unterschied zwischen `shop_unlocked` und `shop_open` ist wichtig.

`shop_unlocked` bleibt wahr, sobald der Spieler einmal 10 Gold erreicht hat.
Auch wenn danach Gold ausgegeben wird, verschwindet der Shop nicht wieder.

`shop_open` ist jetzt nur der Bedien-Fokus. Die Liste bleibt nach der
Freischaltung sichtbar, egal ob `shop_open` wahr oder falsch ist. Mit `u` kann
man den Fokus aktivieren oder verlassen.

## Die Upgrade-Liste

Die Upgrades werden in einer Liste von Dictionaries gespeichert:

```python
upgrades = [
    {
        "id": "saat_boy",
        "name": "Saat-Boy",
        "base_price": 10,
        "base_interval": 5,
        "level": 0,
        "next_action": None,
    },
    ...
]
```

Jedes Upgrade hat mehrere Informationen:

| Key | Bedeutung |
| --- | --- |
| `id` | technische Kennung fuer die Spiellogik |
| `name` | sichtbarer Name im Shop |
| `base_price` | Startpreis fuer Level 1 |
| `base_interval` | Start-Intervall fuer Level 1 |
| `level` | aktuelles Upgrade-Level |
| `next_action` | Zeitpunkt der naechsten automatischen Aktion |

Das ist ein gutes Muster fuer Spiele: Statt fuer jedes Upgrade eigene Variablen
zu bauen, stehen die Upgrade-Daten gemeinsam in einer Struktur.

## Shop freischalten

Die Funktion `update_shop_unlock()` prueft, ob der Shop freigeschaltet werden
soll:

```python
def update_shop_unlock():
    global shop_unlocked

    if gold >= UPGRADE_UNLOCK_GOLD:
        shop_unlocked = True
```

Sobald `gold` mindestens 10 ist, wird `shop_unlocked` auf `True` gesetzt.

Wichtig: Es gibt keine Stelle, die `shop_unlocked` wieder auf `False` setzt.
Darum bleibt der Shop nach der ersten Freischaltung sichtbar.

## Shop anzeigen

Die Anzeige wurde aufgeteilt:

- `build_garden_lines()` baut die linken Garten-Zeilen.
- `build_upgrade_shop_lines()` baut die rechten Shop-Zeilen inklusive
  Upgrade-Liste.
- `draw_garden()` setzt beides nebeneinander, wenn das Terminal breit genug ist.

Damit der Shop rechts am Terminalrand stehen kann, wird die Terminalbreite
ermittelt:

```python
terminal_width = shutil.get_terminal_size((80, 24)).columns
```

Wenn genug Platz vorhanden ist, berechnet `draw_garden()` den Abstand zwischen
Garten und Shop:

```python
spacing = max(2, terminal_width - SHOP_PANEL_WIDTH - visible_length(left))
```

So beginnt das Shop-Panel an einer festen rechten Position.

Wenn das Terminal zu schmal ist, wird der Shop unter dem Garten angezeigt.
Das verhindert, dass Text ineinander laeuft.

Wichtig: `build_upgrade_shop_lines()` zeigt die Upgrade-Liste immer, sobald
`shop_unlocked` wahr ist. `shop_open` entscheidet nur noch, ob die Liste
bedienbar ist und ob ein aktiver Eintrag hervorgehoben wird.

## ASCII-Screenshots

Da das Spiel komplett aus Terminal-Text besteht, lassen sich Zustaende gut als
Markdown-Codeblock zeigen. Die echten Farben sind hier als normaler Text
dargestellt.

Shop freigeschaltet, aber nicht im Shop-Fokus:

```text
=== IDLE GARDEN ===                   +----------------------------------------+
Samen: 5 | Gold: 10                   |UPGRADE-SHOP                            |
                                      +----------------------------------------+
. . . . .                             |u: Shop bedienen                        |
. . . . .                             |Gold: 10                                |
. . . . .                             +----------------------------------------+
. . . . .                             |  Saat-Boy                           10g|
. . . . .                             |  pflanzt alle 5s 1 Samen               |
                                      |                                        |
[p] Samen pflanzen                    |  Erntehelfer              20g fehlt 10g|
[h] Ernten                            |  erntet alle 5s 1 Feld                 |
[b] Samen kaufen (3 Gold)             |                                        |
[u] Upgrade-Shop bedienen             +----------------------------------------+
[q] Beenden
```

Shop-Fokus aktiv, erster Menuepunkt ausgewaehlt:

```text
=== IDLE GARDEN ===                   +----------------------------------------+
Samen: 5 | Gold: 10                   |UPGRADE-SHOP                            |
                                      +----------------------------------------+
. . . . .                             |Shop aktiv                              |
. . . . .                             |Up/Down oder a/d: Auswahl               |
. . . . .                             |Enter/Space: kaufen                     |
. . . . .                             |u: Fokus verlassen                      |
. . . . .                             +----------------------------------------+
                                      |> Saat-Boy                           10g|
[p] Samen pflanzen                    |  pflanzt alle 5s 1 Samen               |
[h] Ernten                            |                                        |
[b] Samen kaufen (3 Gold)             |  Erntehelfer              20g fehlt 10g|
[u] Upgrade-Shop Fokus verlassen      |  erntet alle 5s 1 Feld                 |
[q] Beenden                           |                                        |
                                      +----------------------------------------+
```

Shop mit vorhandenen Leveln:

```text
=== IDLE GARDEN ===                   +----------------------------------------+
Samen: 5 | Gold: 50                   |UPGRADE-SHOP                            |
                                      +----------------------------------------+
. . . . .                             |Shop aktiv                              |
. . . . .                             |Up/Down oder a/d: Auswahl               |
. . . . .                             |Enter/Space: kaufen                     |
. . . . .                             |u: Fokus verlassen                      |
. . . . .                             +----------------------------------------+
                                      |> Saat-Boy Lv. 1                     20g|
[p] Samen pflanzen                    |  pflanzt alle 5s 1 Samen               |
[h] Ernten                            |                                        |
[b] Samen kaufen (3 Gold)             |  Erntehelfer Lv. 4       100g fehlt 50g|
[u] Upgrade-Shop Fokus verlassen      |  erntet alle 2s 1 Feld                 |
[q] Beenden                           |                                        |
                                      +----------------------------------------+
```

Shop mit maximalen Upgrades:

```text
=== IDLE GARDEN ===                   +----------------------------------------+
Samen: 5 | Gold: 999                  |UPGRADE-SHOP                            |
                                      +----------------------------------------+
. . . . .                             |Shop aktiv                              |
. . . . .                             |Up/Down oder a/d: Auswahl               |
. . . . .                             |Enter/Space: kaufen                     |
. . . . .                             |u: Fokus verlassen                      |
. . . . .                             +----------------------------------------+
                                      |> Saat-Boy Lv. Max                     |
[p] Samen pflanzen                    |  pflanzt alle 1s 5 Samen               |
[h] Ernten                            |                                        |
[b] Samen kaufen (3 Gold)             |  Erntehelfer Lv. Max                   |
[u] Upgrade-Shop Fokus verlassen      |  erntet alle 1s 5 Felder               |
[q] Beenden                           |                                        |
                                      +----------------------------------------+
```

## Warum `visible_length()` noetig ist

Farbcodes wie `"\033[31m"` stehen im String, nehmen im Terminal aber keinen
sichtbaren Platz ein.

Darum waere `len(text)` fuer farbige Texte falsch. Beispiel:

```python
RED + "20g" + RESET
```

Der sichtbare Text ist nur `20g`, aber der String enthaelt zusaetzlich
unsichtbare Steuerzeichen.

`visible_length()` entfernt diese Steuerzeichen vor dem Messen:

```python
def visible_length(text):
    return len(ANSI_ESCAPE.sub("", text))
```

Das sorgt dafuer, dass Boxen und Abstaende trotz Farben richtig ausgerichtet
bleiben.

## Preise formatieren

Die Funktion `format_upgrade_price(upgrade)` entscheidet, wie ein Preis im Shop
angezeigt wird:

```python
def format_upgrade_price(upgrade):
    price = get_upgrade_price(upgrade)

    if price is None:
        return ""

    price_text = f"{price}g"

    if gold < price:
        missing_gold = price - gold
        return RED + f"{price_text} fehlt {missing_gold}g" + RESET

    return price_text
```

Die Logik:

- Ist das Upgrade auf Maximum, gibt es keinen Preis mehr.
- Reicht das Gold nicht, wird der Preis rot und zeigt den fehlenden Betrag.
- Reicht das Gold, wird der Preis normal angezeigt.

Der eigentliche Preis wird in `get_upgrade_price()` berechnet:

```python
def get_upgrade_price(upgrade):
    if is_upgrade_maxed(upgrade):
        return None

    return upgrade["base_price"] * (upgrade["level"] + 1)
```

`None` bedeutet hier: Dieses Upgrade kann nicht mehr gekauft werden.

## Namen und Level anzeigen

Die Funktion `format_upgrade_name(upgrade)` baut den Namen fuer den Shop:

```python
def format_upgrade_name(upgrade):
    name = upgrade["name"]

    if is_upgrade_maxed(upgrade):
        return name + " " + GREEN + "Lv. Max" + RESET

    if upgrade["level"] > 0:
        return f"{name} Lv. {upgrade['level']}"

    return name
```

Die Logik:

- Level 0 zeigt nur den Namen.
- Ab Level 1 steht `Lv. N` hinter dem Namen.
- Beim Maximum steht gruen `Lv. Max` hinter dem Namen.

## Aktiven Menuepunkt markieren

Der aktive Eintrag wird in `build_upgrade_item_line()` markiert:

```python
selector = "> " if is_active else "  "
name = selector + format_upgrade_name(upgrade)

if is_active:
    name = CYAN + name + RESET
```

Wenn ein Eintrag aktiv ist, bekommt er:

- ein `>` als Auswahlmarker
- eine cyanfarbene Darstellung

Die eigentliche Auswahl wird ueber `selected_upgrade` gespeichert. Der Eintrag
wird nur farbig hervorgehoben, wenn der Shop-Fokus aktiv ist.

## Upgrade kaufen

Der Kauf passiert in `buy_selected_upgrade()`:

```python
def buy_selected_upgrade():
    global gold

    upgrade = upgrades[selected_upgrade]
    price = get_upgrade_price(upgrade)

    if price is None or gold < price:
        return

    gold -= price
    upgrade["level"] += 1
    upgrade["next_action"] = time.time() + get_upgrade_interval(upgrade)
```

Zuerst wird das aktuell ausgewaehlte Upgrade geholt:

```python
upgrade = upgrades[selected_upgrade]
```

Dann wird geprueft:

- Ist es schon auf Maximum?
- Reicht das Gold nicht?

Wenn eine dieser Bedingungen stimmt, passiert nichts.

Bei einem erfolgreichen Kauf:

- wird Gold abgezogen
- wird `level` um 1 erhoeht
- wird die erste automatische Aktion geplant

`next_action` ist wieder ein Zeitstempel. Das Upgrade handelt nach dem aktuellen
Intervall. Bei einem weiteren Kauf wird der Timer neu gesetzt, weil sich das
Intervall geaendert haben kann.

## Automatische Aktionen

Die Funktion `run_automation()` laeuft in jedem Game-Loop:

```python
def run_automation():
    now = time.time()

    for upgrade in upgrades:
        ...
```

Sie prueft jedes Upgrade:

1. Ist das Level groesser als 0?
2. Hat es einen naechsten Aktionszeitpunkt?
3. Ist dieser Zeitpunkt erreicht?

Wenn ja, wird anhand der `id` entschieden, was passiert:

```python
for _ in range(get_upgrade_action_count(upgrade)):
    if upgrade["id"] == "saat_boy":
        plant_seed()
    elif upgrade["id"] == "harvest_helper":
        harvest_one()
```

`get_upgrade_action_count(upgrade)` entscheidet, wie oft die Aktion ausgefuehrt
wird. Bis Level 5 ist das immer 1. Danach steigt die Aktionsmenge bis auf 5.

Danach wird der naechste Aktionszeitpunkt gesetzt:

```python
upgrade["next_action"] = now + get_upgrade_interval(upgrade)
```

Das ist dieselbe Grundidee wie beim Pflanzenwachstum: Das Spiel speichert
Zeitpunkte und prueft regelmaessig, ob sie erreicht sind.

## Einzelnes Feld ernten

Vorher konnte `harvest()` alle fertigen Pflanzen auf einmal ernten.
Fuer den Erntehelfer wird aber eine Funktion gebraucht, die nur ein Feld
erntet.

Darum gibt es jetzt:

- `find_ready_fields()`: findet alle erntereifen Felder
- `harvest_plant(row_index, col_index)`: erntet ein bestimmtes Feld
- `harvest_one()`: sucht zufaellig ein erntereifes Feld und erntet es
- `harvest()`: nutzt weiterhin alle erntereifen Felder fuer die manuelle Ernte

`harvest_plant()` ist der gemeinsame Kern. Dadurch nutzen manuelle Ernte und
Erntehelfer dieselbe Ertragslogik.

Das ist wichtig, weil der Ernte-Bonus dadurch fuer beide Wege gilt.

## Pfeiltasten lesen

Normale Buchstaben wie `p` oder `h` sind einzelne Zeichen.
Pfeiltasten sind anders: Das Terminal sendet dafuer mehrere Zeichen
hintereinander, sogenannte Escape-Sequenzen.

Die Pfeiltaste runter sendet zum Beispiel:

```python
"\x1b[B"
```

Die deutsche Tastatur ist dabei normalerweise nicht der entscheidende Punkt.
Pfeiltasten haengen eher davon ab, welche Escape-Sequenz das Terminal sendet.
Darum liest das Spiel jetzt nicht nur eine einzige exakte Sequenz, sondern
wertet das letzte Richtungssymbol aus.

`read_escape_command()` sammelt solche Sequenzen:

```python
def read_escape_command():
    sequence = "\x1b"

    if not select.select([sys.stdin], [], [], 0.05)[0]:
        return None

    sequence += sys.stdin.read(1)

    while select.select([sys.stdin], [], [], 0.02)[0]:
        sequence += sys.stdin.read(1)

        if sequence[-1] in "ABCD~":
            break
```

Danach wird die Sequenz in einen lesbaren Befehl uebersetzt:

```python
arrow_keys = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
}
```

So muss der Rest des Spiels nicht mit rohen Terminal-Zeichen arbeiten. Er sieht
nur noch Befehle wie `"up"` oder `"down"`.

Zusaetzlich funktionieren im Shop `a` und `d`. Das ist ein einfacher Fallback,
falls ein Terminal Pfeiltasten anders behandelt als erwartet.

## Shop-Befehle verarbeiten

`handle_command()` unterscheidet jetzt zwischen zwei Modi:

- Shop-Fokus aktiv
- Shop-Fokus nicht aktiv

Wenn der Shop-Fokus aktiv ist, bedeuten die Befehle etwas anderes:

```python
if shop_open:
    if command in ("up", "left", "a"):
        selected_upgrade = (selected_upgrade - 1) % len(upgrades)
    elif command in ("down", "right", "d"):
        selected_upgrade = (selected_upgrade + 1) % len(upgrades)
    elif command in ("enter", "space"):
        buy_selected_upgrade()
    elif command == "u":
        shop_open = False
```

Das `% len(upgrades)` sorgt dafuer, dass die Auswahl am Ende wieder zum Anfang
springt.

Beispiel:

- Es gibt 2 Upgrades.
- Aktuell ist Eintrag 0 aktiv.
- Pfeiltaste hoch macht daraus `-1 % 2`.
- Das Ergebnis ist 1.

Dadurch kann man rund durch das Menue navigieren.

Wenn der Shop-Fokus nicht aktiv ist, gelten die normalen Spielbefehle:

```python
elif command == "u" and shop_unlocked:
    shop_open = True
```

`u` aktiviert den Shop-Fokus also nur, wenn der Shop vorher freigeschaltet
wurde. Die Liste ist aber schon vorher sichtbar, sobald `shop_unlocked` wahr
ist.

## Neuer Game-Loop

Der Game-Loop macht jetzt mehr als vorher:

```python
while running:
    grow_plants()
    run_automation()
    update_shop_unlock()
    clear_screen()
    draw_garden()

    command = read_command()

    if command is not None:
        running = handle_command(command)
        update_shop_unlock()
```

Die Reihenfolge ist wichtig:

1. Pflanzen wachsen.
2. Gelevelte Helfer handeln.
3. Der Shop wird bei genug Gold freigeschaltet.
4. Die Anzeige wird neu gezeichnet.
5. Eingaben werden gelesen.
6. Befehle werden ausgefuehrt.
7. Nach einem Befehl wird nochmal geprueft, ob der Shop freigeschaltet wurde.

Der letzte Punkt ist nuetzlich, weil eine manuelle Ernte sofort Gold bringen
kann.

## Lernpunkte aus diesem Schritt

Dieses Feature bringt mehrere neue Python- und Spielentwicklungs-Ideen:

- Listen von Dictionaries eignen sich gut fuer mehrere aehnliche Spielobjekte.
- Ein Spiel kann unterschiedliche Bedienmodi haben.
- Terminal-Farben brauchen Sonderbehandlung bei Textbreiten.
- Pfeiltasten sind Escape-Sequenzen, keine einfachen Buchstaben.
- Fallback-Tasten wie `a` und `d` machen Terminal-Bedienung robuster.
- Automatische Helfer funktionieren gut ueber Zeitstempel.
- Eine zentrale Funktion wie `harvest_plant()` vermeidet doppelte Logik.
- Level-Systeme lassen sich gut aus wenigen Basiswerten berechnen.
- `None` kann genutzt werden, um "kein Preis mehr vorhanden" auszudruecken.

## Moegliche naechste Schritte

Auf diesem Shop-System lassen sich gut weitere Features aufbauen:

- Im Shop kleine Status-Timer anzeigen.
- Pro Level anzeigen, was der naechste Kauf konkret verbessert.
- Verschiedene Preisformeln testen, zum Beispiel exponentielle Preise.
- Unterschiedliche Pflanzenarten verkaufen.
- Einen Speichern/Laden-Mechanismus einfuehren, damit gekaufte Upgrades
  erhalten bleiben.
