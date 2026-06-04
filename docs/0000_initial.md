# Terminal Farm: aktueller Stand

Dieses Dokument beschreibt den aktuellen Stand von `main.py`. Es ist so
geschrieben, dass man damit nicht nur das Projekt versteht, sondern nebenbei
auch wichtige Python-Grundlagen lernen kann.

Das Projekt ist ein kleines Garten-Farm-Idle-Game im Terminal. Der Spieler hat
Samen, pflanzt sie auf ein 5x5-Feld, wartet, bis Pflanzen wachsen, und erntet
fertige Pflanzen fuer Gold und neue Samen. Gold kann danach wieder in neue
Samen investiert werden.

## Spiel starten

Das Spiel wird im Terminal aus dem Projektordner gestartet:

```bash
python3 main.py
```

Diese Version ist fuer normale macOS- und Linux-Terminals gedacht. Sie nutzt
Terminal-Funktionen wie `termios`, `tty` und `select`, damit einzelne Tasten
sofort gelesen werden koennen. Unter Windows braeuchte man fuer diesen Teil
wahrscheinlich eine andere Eingabe-Loesung.

## Was das Spiel aktuell kann

- Es zeigt einen Garten mit 25 Feldern im Terminal.
- Leere Felder werden als `.` angezeigt.
- Neue Pflanzen starten als `,`.
- Wachsende Pflanzen werden als gruenes `i` angezeigt.
- Erntereife Pflanzen werden als gelbes `Y` angezeigt.
- Jede Pflanze hat ihren eigenen Wachstumszeitpunkt.
- Das Wachstum laeuft nach echter Zeit weiter.
- Gold kann fuer neue Samen ausgegeben werden.
- Beim Ernten gibt es eine kleine Chance auf einen Bonus: entweder 2 Gold oder
  2 Samen, aber nie beides gleichzeitig.
- Die Anzeige aktualisiert sich automatisch, auch wenn kein Befehl eingegeben
  wird.
- Eingaben funktionieren direkt per Taste:
  - `p`: Samen pflanzen
  - `h`: erntereife Pflanzen ernten
  - `b`: Samen kaufen
  - `q`: Spiel beenden

## Die wichtigsten Python-Ideen in diesem Projekt

### Imports

Am Anfang von `main.py` stehen mehrere `import`-Zeilen:

```python
import time
import random
import select
import sys
import termios
import tty
```

Ein `import` laedt Code aus einem Python-Modul. Ein Modul ist eine Datei oder
Bibliothek mit fertigen Funktionen.

Die Module werden hier so benutzt:

- `time`: liefert die aktuelle Zeit in Sekunden.
- `random`: waehlt zufaellige Zahlen und zufaellige Felder aus.
- `select`: prueft, ob eine Tastatur-Eingabe bereitliegt, ohne das Spiel zu
  blockieren.
- `sys`: gibt Zugriff auf `sys.stdin`, also die Eingabe des Terminals.
- `termios` und `tty`: schalten das Terminal in einen Modus, in dem einzelne
  Tasten sofort gelesen werden koennen.

### Konstanten fuer Farben und Balance-Werte

Direkt nach den Imports stehen mehrere Konstanten:

```python
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
SEED_PRICE = 3
BONUS_HARVEST_CHANCE = 0.1
```

Die ersten drei Werte sind ANSI-Codes. Sie sind keine normalen sichtbaren Texte,
sondern Steuerzeichen fuer das Terminal.

- `GREEN` schaltet die Textfarbe auf Gruen.
- `YELLOW` schaltet die Textfarbe auf Gelb.
- `RESET` setzt die Farbe wieder auf normal zurueck.

Die anderen beiden Werte steuern die Spiel-Balance:

- `SEED_PRICE` legt fest, dass ein gekaufter Samen 3 Gold kostet.
- `BONUS_HARVEST_CHANCE` legt die Chance fuer einen Ernte-Bonus fest.

`0.1` bedeutet hier 10 Prozent. Wenn eine Pflanze geerntet wird, besteht also
eine Chance von 10 Prozent, dass sie einen Bonus bringt.

Solche Werte werden oft wie Konstanten behandelt. Eine Konstante ist eine
Variable, deren Wert sich waehrend des Programms nicht aendern soll. In Python
ist Grossschreibung wie `GREEN` eine Konvention: Sie sagt anderen Entwicklern,
dass dieser Wert nicht veraendert werden sollte.

### Variablen

Eine Variable speichert einen Wert:

```python
seeds = 5
gold = 0
```

`seeds` steht fuer die Anzahl der Samen. `gold` steht fuer die Anzahl der
geernteten Goldpunkte. Gold kann aktuell genutzt werden, um mit `b` neue Samen
zu kaufen.

### Listen

Der Garten ist eine Liste aus Listen:

```python
garden = [
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
]
```

Das ist ein 5x5-Raster. Jede innere Liste ist eine Zeile. Jedes Element in
dieser Zeile ist ein Feld.

`None` bedeutet in Python: Hier ist kein Wert vorhanden. In diesem Spiel heisst
das: Das Feld ist leer.

### Dictionaries

Eine Pflanze wird als Dictionary gespeichert:

```python
{
    "stage": ",",
    "next_growth": time.time() + random.randint(3, 8)
}
```

Ein Dictionary speichert Werte unter Namen, sogenannten Keys.

- `"stage"` speichert den aktuellen Wachstumszustand.
- `"next_growth"` speichert den Zeitpunkt, zu dem die Pflanze weiter wachsen
  soll.

### Funktionen

Eine Funktion ist ein benannter Code-Block. Sie wird mit `def` erstellt:

```python
def clear_screen():
    print("\033[H\033[J", end="")
```

Funktionen helfen dabei, Code in klare Aufgaben aufzuteilen. Statt alles in
einem grossen Block zu schreiben, bekommt jeder Teil des Spiels eine eigene
Funktion.

## Das Datenmodell des Spiels

Das Spiel speichert seinen Zustand in drei globalen Variablen:

```python
garden = [...]
seeds = 5
gold = 0
```

Global bedeutet: Diese Variablen stehen ausserhalb einer Funktion und koennen
von mehreren Funktionen gelesen werden.

Der Garten selbst enthaelt entweder:

- `None` fuer ein leeres Feld
- ein Pflanzen-Dictionary fuer ein bepflanztes Feld

Eine Pflanze hat aktuell diese Form:

```python
{
    "stage": ",",
    "next_growth": 1234567890.0
}
```

Die Zahl in `"next_growth"` ist ein Zeitstempel. `time.time()` liefert die
aktuelle Zeit als Zahl. Wenn `time.time()` groesser oder gleich
`next_growth` ist, darf die Pflanze wachsen.

## Die Wachstumsstufen

Aktuell gibt es drei Pflanzen-Stufen:

| Stufe | Anzeige | Bedeutung |
| --- | --- | --- |
| Start | `,` | gerade gepflanzt |
| Wachstum | `i` | Pflanze waechst |
| Fertig | `Y` | Pflanze kann geerntet werden |

Leere Felder sind keine Pflanzen und werden als `.` angezeigt.

Wichtig: Jede Pflanze speichert ihren eigenen `next_growth`-Wert. Dadurch
wachsen Pflanzen unabhaengig voneinander.

## Warum die Anzeige jetzt automatisch aktualisiert

Die erste Version hat wahrscheinlich ungefaehr so funktioniert:

```python
command = input("> ")
```

`input()` wartet so lange, bis der Benutzer Enter drueckt. Waehrend dieser Zeit
steht das ganze Programm still. Deshalb konnte das Wachstum zwar theoretisch
nach Zeit berechnet werden, aber praktisch wurde es erst sichtbar, wenn ein
Befehl eingegeben wurde.

Die aktuelle Version verwendet stattdessen:

```python
select.select([sys.stdin], [], [], timeout)
```

Damit fragt das Programm: "Liegt gerade eine Eingabe vor?" Wenn ja, wird sie
gelesen. Wenn nein, geht das Spiel nach kurzer Zeit trotzdem weiter.

So kann der Haupt-Loop immer wieder laufen:

1. Pflanzen wachsen lassen.
2. Bildschirm neu zeichnen.
3. Kurz auf eine Taste warten.
4. Wieder von vorne.

## Funktionen im Detail

### `clear_screen()`

```python
def clear_screen():
    print("\033[H\033[J", end="")
```

Diese Funktion leert den Terminal-Bildschirm.

Der Text `"\033[H\033[J"` ist eine ANSI-Steuersequenz. Sie sagt dem Terminal:

- springe mit dem Cursor nach oben links
- loesche den sichtbaren Bildschirm

`end=""` sorgt dafuer, dass `print()` am Ende keinen extra Zeilenumbruch
ausgibt.

Warum ist diese Funktion nuetzlich?

Das Spiel zeichnet die Anzeige immer wieder neu. Ohne Loeschen wuerde jede neue
Version unter der alten stehen. Mit `clear_screen()` sieht es aus, als wuerde
die Anzeige aktualisiert.

### `draw_garden()`

```python
def draw_garden():
    print("=== IDLE GARDEN ===")
    print(f"Samen: {seeds} | Gold: {gold}")
    print()

    for row in garden:
        for cell in row:
            ...
```

Diese Funktion zeichnet den kompletten Spielzustand ins Terminal.

Sie zeigt zuerst den Titel und die Ressourcen:

```python
print(f"Samen: {seeds} | Gold: {gold}")
```

Das `f` vor dem String macht daraus einen f-String. In einem f-String koennen
Variablen direkt in geschweiften Klammern eingesetzt werden.

Danach laeuft die Funktion durch den Garten:

```python
for row in garden:
    for cell in row:
```

Das sind zwei verschachtelte Schleifen:

- Die aeussere Schleife geht durch jede Zeile.
- Die innere Schleife geht durch jedes Feld in dieser Zeile.

Je nach Inhalt des Feldes wird ein anderes Zeichen ausgegeben:

- `None` wird als `.` gezeichnet.
- Stufe `,` wird als `,` gezeichnet.
- Stufe `i` wird gruen gezeichnet.
- Stufe `Y` wird gelb gezeichnet.

Am Ende zeigt die Funktion die verfuegbaren Tastenbefehle und den Eingabe-Prompt
an.

### `create_plant()`

```python
def create_plant():
    return {
        "stage": ",",
        "next_growth": time.time() + random.randint(3, 8)
    }
```

Diese Funktion erstellt eine neue Pflanze.

Sie gibt ein Dictionary zurueck. Das passiert mit `return`.

Die neue Pflanze startet mit:

- `"stage": ","`
- `"next_growth"` zwischen 3 und 8 Sekunden in der Zukunft

Dieser Teil ist wichtig:

```python
time.time() + random.randint(3, 8)
```

`time.time()` ist die aktuelle Zeit. `random.randint(3, 8)` erzeugt eine
zufaellige ganze Zahl zwischen 3 und 8. Zusammen ergibt das den Zeitpunkt, wann
die Pflanze zum ersten Mal wachsen soll.

### `plant_seed()`

```python
def plant_seed():
    global seeds
```

Diese Funktion pflanzt einen Samen auf ein zufaelliges freies Feld.

`global seeds` sagt Python: Wenn diese Funktion `seeds` veraendert, ist die
globale Variable `seeds` gemeint, nicht eine neue lokale Variable.

Zuerst prueft die Funktion, ob ueberhaupt Samen vorhanden sind:

```python
if seeds <= 0:
    return
```

Wenn keine Samen vorhanden sind, beendet `return` die Funktion sofort.

Danach sammelt die Funktion alle freien Felder:

```python
empty_fields = []

for row_index, row in enumerate(garden):
    for col_index, cell in enumerate(row):
        if cell is None:
            empty_fields.append((row_index, col_index))
```

`enumerate()` ist hier sehr praktisch. Es liefert nicht nur den Wert, sondern
auch den Index.

Beispiel:

- `row_index` ist die Nummer der Zeile.
- `col_index` ist die Nummer der Spalte.
- `cell` ist der Inhalt des Feldes.

Ein freies Feld wird als Tupel gespeichert:

```python
(row_index, col_index)
```

Wenn es kein freies Feld gibt, wird die Funktion beendet:

```python
if not empty_fields:
    return
```

Danach wird ein zufaelliges freies Feld ausgewaehlt:

```python
row, col = random.choice(empty_fields)
```

Dann wird dort eine neue Pflanze erstellt:

```python
garden[row][col] = create_plant()
```

Zum Schluss wird ein Samen abgezogen:

```python
seeds -= 1
```

### `buy_seed()`

```python
def buy_seed():
    global gold, seeds

    if gold < SEED_PRICE:
        return

    gold -= SEED_PRICE
    seeds += 1
```

Diese Funktion kauft einen neuen Samen fuer Gold.

`global gold, seeds` ist noetig, weil beide Werte veraendert werden:

- `gold` wird kleiner.
- `seeds` wird groesser.

Zuerst prueft die Funktion, ob genug Gold vorhanden ist:

```python
if gold < SEED_PRICE:
    return
```

Wenn der Spieler weniger Gold hat als `SEED_PRICE`, passiert nichts. Die
Funktion wird sofort beendet.

Wenn genug Gold vorhanden ist, wird der Preis abgezogen:

```python
gold -= SEED_PRICE
```

Danach bekommt der Spieler einen Samen:

```python
seeds += 1
```

Diese Funktion gibt Gold zum ersten Mal einen direkten Nutzen im Spiel.

### `grow_plants()`

```python
def grow_plants():
    now = time.time()
```

Diese Funktion laesst alle Pflanzen wachsen, deren Zeit gekommen ist.

`now` speichert die aktuelle Zeit. Dadurch muss `time.time()` nicht fuer jede
Pflanze mehrfach aufgerufen werden.

Danach geht die Funktion durch jedes Feld im Garten:

```python
for row in garden:
    for plant in row:
```

Wenn das Feld leer ist, wird es uebersprungen:

```python
if plant is None:
    continue
```

`continue` bedeutet: Beende diesen Schleifendurchlauf und gehe direkt zum
naechsten Feld.

Wenn die aktuelle Zeit groesser oder gleich dem gespeicherten
Wachstumszeitpunkt ist, waechst die Pflanze:

```python
if now >= plant["next_growth"]:
```

Eine neue Pflanze wird von `,` zu `i`:

```python
if plant["stage"] == ",":
    plant["stage"] = "i"
    plant["next_growth"] = now + random.randint(4, 10)
```

Dabei bekommt sie auch einen neuen Wachstumszeitpunkt, diesmal 4 bis 10
Sekunden in der Zukunft.

Eine wachsende Pflanze wird von `i` zu `Y`:

```python
elif plant["stage"] == "i":
    plant["stage"] = "Y"
```

Bei `Y` ist die Pflanze fertig. Sie bekommt keinen neuen `next_growth`-Wert,
weil sie nicht weiter wachsen muss.

### `calculate_harvest_reward()`

```python
def calculate_harvest_reward():
    gold_reward = 1
    seed_reward = 1

    if random.random() < BONUS_HARVEST_CHANCE:
        bonus_type = random.choice(["gold", "seeds"])

        if bonus_type == "gold":
            gold_reward += 1
        else:
            seed_reward += 1

    return gold_reward, seed_reward
```

Diese Funktion berechnet, was eine einzelne geerntete Pflanze bringt.

Normalerweise bringt jede Pflanze:

- 1 Gold
- 1 Samen

Darum starten die beiden Werte so:

```python
gold_reward = 1
seed_reward = 1
```

Danach wird gewuerfelt, ob es einen Bonus gibt:

```python
if random.random() < BONUS_HARVEST_CHANCE:
```

`random.random()` erzeugt eine zufaellige Kommazahl zwischen 0 und 1. Wenn
`BONUS_HARVEST_CHANCE` den Wert `0.1` hat, ist diese Bedingung ungefaehr in 10
Prozent der Faelle wahr.

Wenn ein Bonus passiert, wird der Bonus-Typ zufaellig ausgewaehlt:

```python
bonus_type = random.choice(["gold", "seeds"])
```

Dadurch gibt es entweder:

- einen extra Goldpunkt
- oder einen extra Samen

Die Pflanze kann dadurch 2 Gold oder 2 Samen bringen, aber nicht beides
gleichzeitig.

Am Ende gibt die Funktion beide Werte zurueck:

```python
return gold_reward, seed_reward
```

Das ist ein Rueckgabewert mit zwei Teilen. Beim Aufruf kann man beide direkt in
zwei Variablen speichern.

### `harvest()`

```python
def harvest():
    global gold, seeds
```

Diese Funktion erntet alle fertigen Pflanzen.

`global gold, seeds` ist noetig, weil beide Werte veraendert werden.

Die Funktion geht durch jedes Feld:

```python
for row_index, row in enumerate(garden):
    for col_index, cell in enumerate(row):
```

Dann prueft sie, ob dort eine fertige Pflanze steht:

```python
if cell is not None and cell["stage"] == "Y":
```

Diese Bedingung hat zwei Teile:

- `cell is not None`: Auf dem Feld steht ueberhaupt eine Pflanze.
- `cell["stage"] == "Y"`: Die Pflanze ist erntereif.

Wenn beides stimmt, wird das Feld geleert:

```python
garden[row_index][col_index] = None
```

Dann wird berechnet, was diese Pflanze bringt:

```python
gold_reward, seed_reward = calculate_harvest_reward()
```

Diese Zeile ruft `calculate_harvest_reward()` auf und speichert die beiden
Rueckgabewerte in zwei Variablen.

Danach werden Gold und Samen erhoeht:

```python
gold += gold_reward
seeds += seed_reward
```

Aktuell erntet `harvest()` alle fertigen Pflanzen auf einmal.

### `read_command(timeout=0.25)`

```python
def read_command(timeout=0.25):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
```

Diese Funktion liest eine Taste, blockiert aber nicht dauerhaft.

`timeout=0.25` ist ein Standardwert. Wenn beim Aufruf kein anderer Wert
uebergeben wird, wartet die Funktion hoechstens 0.25 Sekunden.

`select.select(...)` prueft, ob `sys.stdin` bereit ist. In diesem Projekt
bedeutet das: Es wurde eine Taste gedrueckt.

Das Ergebnis wird so gespeichert:

```python
ready, _, _ = select.select(...)
```

`ready` enthaelt die Eingaben, die bereit sind. Die beiden `_` bedeuten: Diese
Rueckgabewerte interessieren uns nicht.

Wenn keine Eingabe bereitliegt, gibt die Funktion `None` zurueck:

```python
if not ready:
    return None
```

Wenn eine Eingabe bereitliegt, wird genau ein Zeichen gelesen:

```python
return sys.stdin.read(1).lower()
```

`.lower()` macht daraus einen Kleinbuchstaben. Dadurch wuerde auch `P` wie `p`
behandelt.

### `handle_command(command)`

```python
def handle_command(command):
    if command == "p":
        plant_seed()
    elif command == "h":
        harvest()
    elif command == "b":
        buy_seed()
    elif command == "q":
        return False

    return True
```

Diese Funktion entscheidet, was bei einer gedrueckten Taste passieren soll.

- Bei `p` wird `plant_seed()` aufgerufen.
- Bei `h` wird `harvest()` aufgerufen.
- Bei `b` wird `buy_seed()` aufgerufen.
- Bei `q` gibt die Funktion `False` zurueck.

Der Rueckgabewert ist wichtig fuer den Haupt-Loop:

- `True` bedeutet: Spiel laeuft weiter.
- `False` bedeutet: Spiel soll beendet werden.

Unbekannte Tasten machen aktuell nichts und das Spiel laeuft weiter.

### `main()`

```python
def main():
    old_terminal_settings = termios.tcgetattr(sys.stdin)
```

`main()` ist die Hauptfunktion des Spiels. Hier wird der Game-Loop gestartet.

Zuerst speichert die Funktion die aktuellen Terminal-Einstellungen:

```python
old_terminal_settings = termios.tcgetattr(sys.stdin)
```

Das ist wichtig, weil das Spiel das Terminal danach veraendert.

Dann startet ein `try`-Block:

```python
try:
    tty.setcbreak(sys.stdin)
    running = True
```

`tty.setcbreak(sys.stdin)` sorgt dafuer, dass Tastendruecke sofort gelesen
werden koennen. Ohne diesen Modus muesste man oft erst Enter druecken.

`running = True` ist die Kontrollvariable fuer den Spiel-Loop.

Der Loop sieht so aus:

```python
while running:
    grow_plants()
    clear_screen()
    draw_garden()

    command = read_command()

    if command is not None:
        running = handle_command(command)
```

Solange `running` wahr ist, passiert immer wieder:

1. Alle Pflanzen werden geprueft und wachsen bei Bedarf.
2. Der Bildschirm wird geloescht.
3. Der Garten wird neu gezeichnet.
4. Das Programm wartet kurz auf eine Taste.
5. Wenn eine Taste gedrueckt wurde, wird der Befehl ausgefuehrt.

Der `finally`-Block laeuft immer, auch wenn etwas schiefgeht:

```python
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)
```

Damit werden die alten Terminal-Einstellungen wiederhergestellt. Das ist sehr
wichtig. Sonst koennte das Terminal nach dem Spiel merkwuerdig reagieren.

### `if __name__ == "__main__":`

```python
if __name__ == "__main__":
    main()
```

Diese Zeilen sorgen dafuer, dass `main()` nur gestartet wird, wenn die Datei
direkt ausgefuehrt wird:

```bash
python3 main.py
```

Wenn die Datei von einer anderen Python-Datei importiert wird, startet das Spiel
nicht automatisch. Das ist nuetzlich fuer Tests oder spaetere Erweiterungen.

## Der komplette Spielablauf

So laeuft das Spiel aktuell:

1. Python laedt die Module.
2. Farben, Garten, Samen und Gold werden vorbereitet.
3. `main()` startet.
4. Das Terminal wird in den direkten Tastaturmodus geschaltet.
5. Der Game-Loop beginnt.
6. `grow_plants()` prueft alle Pflanzen.
7. `clear_screen()` leert die Anzeige.
8. `draw_garden()` zeichnet den aktuellen Zustand.
9. `read_command()` wartet kurz auf eine Taste.
10. `handle_command()` fuehrt bei Bedarf den Befehl aus.
11. Bei `q` endet der Loop.
12. Die alten Terminal-Einstellungen werden wiederhergestellt.

## Warum das ein Idle-Game ist

Ein Idle-Game lebt davon, dass Dinge auch ohne staendige Aktion weiterlaufen.

In diesem Projekt passiert das durch Zeitstempel:

```python
"next_growth": time.time() + random.randint(3, 8)
```

Die Pflanze merkt sich nicht: "Ich muss drei Sekunden lang aktiv wachsen."

Sie merkt sich stattdessen: "Ab diesem Zeitpunkt darf ich in die naechste Stufe
wechseln."

Das ist ein gutes Muster fuer Idle-Games, weil das Spiel nicht jede Sekunde
komplizierte Berechnungen speichern muss. Es muss nur regelmaessig vergleichen:

```python
if now >= plant["next_growth"]:
```

## Moegliche naechste Schritte

Diese Ideen passen gut zum aktuellen Aufbau:

- Verschiedene Pflanzenarten mit unterschiedlichen Wachstumszeiten.
- Unterschiedliche Verkaufspreise pro Pflanze.
- Den Shop um bessere Samen oder Upgrades erweitern.
- Manuelles Auswaehlen eines Feldes statt zufaelliges Pflanzen.
- Speichern und Laden des Spielstands.
- Ein groesserer Garten, der spaeter freigeschaltet wird.
- Automatische Helfer, die nach einer bestimmten Zeit ernten oder pflanzen.

## Mini-Glossar

| Begriff | Bedeutung |
| --- | --- |
| Variable | Name fuer einen gespeicherten Wert |
| Liste | Sammlung von Werten in einer Reihenfolge |
| Dictionary | Sammlung von Werten mit benannten Schluesseln |
| Funktion | Benannter Code-Block fuer eine Aufgabe |
| Konstante | Variable, die waehrend des Programms nicht veraendert werden soll |
| Schleife | Code, der mehrfach ausgefuehrt wird |
| `None` | Kein Wert vorhanden |
| `return` | Funktion beenden und optional einen Wert zurueckgeben |
| `global` | In einer Funktion eine globale Variable veraendern |
| f-String | String, in den Variablen eingesetzt werden koennen |
| Terminal | Textbasierte Eingabe- und Ausgabeumgebung |
| Game-Loop | Schleife, die ein Spiel immer wieder aktualisiert |
| Timeout | Maximale Wartezeit |
| ANSI-Code | Steuerzeichen fuer das Terminal |
| Wahrscheinlichkeit | Chance, dass ein bestimmtes Ereignis passiert |
