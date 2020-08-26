# Ponyspiel

Tool zur Verwaltung von Pferden beim Browsergame noblehorsechampion.

## Funktionen

![main_window](https://beachomize.de/ponyspiel_image/main_with_numbers2.jpg)

### 1 - Login

Eingabe der eigenen Login-Daten, damit das Tool sich im Spiel einloggen kann.

Für Funktion 11 kann außerdem die eigene Telegram ID eingegeben werden. Diese gibt z.B. der Bot _@userinfobot_ aus, der über die Suche in der Telegram-App gefunden werden kann.

### 2 - Datenabruf

Laden der Daten eines Pferdes nach ID. Anschließend können Funktionen 3-6 und 11 auf dieses Pferd angewendet werden.
Die Daten werden im lokalen Cache gespeichert, um den Ladevorgang beim nächsten Mal zu beschleunigen.

### 3 - Als eigenes Pferd registrieren

### 4 - Daten-Export

Daten des Pferdes als HTML-Tabelle in die Windows-Zwischenablage exportieren. Diese kann in einem Tabellenkalkulationsprogramm (z.B. Excel) eingefügt werden.

Es kann ausgewählt werden, welche Kategorien von Werten exportiert werden (**Gesundheit**, **Charakter**, **Exterieur**, **Training**, **Training-Details**, **Fakten**).

Außerdem können optional die Bezeichnungen der Werte als Überschrift mit exportiert werden (**Tabellenüberschriften**),
die Gesamtwerte vom Export ausgeschlossen werden (**Summierte Werte**) und
die Werte aus der Kategorie Gesundheit, die in der aktuellen Version des Spiels immer 100 sind, mit exportiert werden (**Gesundheit komplett**).

### 5 - Kurzbeschreibung

Automatisch eine Kurzbeschreibung generieren und in die Windows-Zwischenablage kopieren. Diese kann auf der Seite des Pferdes im Spiel eingefügt werden.

Wie diese Beschreibung generiert wird, kann mit Hilfe von Dateien im Ordner _descriptions_ definiert werden. Die Beschreibung kann für jede Pferderasse
individuell konfiguriert werden, indem eine txt-Datei im Ordner abgelegt wird, die als Dateinamen den Namen der Pferderasse trägt. Ist eine solche Datei nicht vorhanden,
wird auf die Datei _default.txt_ zurückgegriffen.

Die Datei _Isländer.txt_ könnte z.B. wie folgt aussehen:

```
Exterieur: Haltung, Ausdruck, Kopf, Halsansatz, Rückenlinie, Beinstellung
Gesamtpotenzial
T_Tölt: Tölt, Töltrennen
P_Pass: Rennpass, Passrennen
A_Ausbildung
```

Jede Zeile definiert einen auszugebenden Wert. Die einzelnen Werte werden in der Ausgabe durch einen senkrechten Strich getrennt.

Die Angabe einer einzelnen Kategorie (hier z.B. Ausbildung) sorgt für die Ausgabe des Durchschnittswertes für diese Kategorie.

Ein Doppelpunkt signalisiert, dass der Durchschnittwert der folgenden Einzelwerte berechnet werden soll (hier z.B. Tölt: Tölt, Töltrennen). Das Wort vor dem Doppelpunkt wird verworfen.

Ein Unterstrich signalisiert, dass der Ausdruck vor dem Doppelstrich als Bezeichnung vor dem ausgegebenen Wert stehen soll.

Besondere Schlüsselwörter, bei denen kein Durchschnittswert berechnet wird, sind z.B. Gesamtpotenzial und Fellfarbe.

Die generierte Beschreibung sieht dann so aus:

```
20.0 | 1493 | T 16.0 | P 12.5 | A 12.8
```

### 6 - Ausbildung-Notiz

Automatisch eine Notiz generieren, welche die allgemein für Turniere relevanten Werte aus der Kategorie Ausbildung übersichtlich zusammenfasst:

```
Halle: 8 | Arena: 7 | draußen: 19
Sand: 11 | Gras: 13 | Erde: 9 | Schnee: 19 | Lehm: 13 | Späne: 17
sehr weich: 13 | weich: 5 | mittel: 18 | hart: 9 | sehr hart: 12
```

### 7 - Eigene Pferde ermitteln

Ermittelt automatisch die IDs der eigenen Pferde. Dies ist nützlich, um diese anschließend mit Funtion 8 aufzulisten.

### 8 - Eigene Pferde auflisten

Erzeugt eine Auflistung eigener Pferde. Welche Rassen und welche Werte dabei mit einbezogen werden, kann mithilfe von Dateien im Ordner _listings_ definiert werden.

Anhand welcher dieser Dateien Pferde angezeigt werden, kann im Drop-Down-Menü ausgewählt werden. Die Definition der Dateien folgt einem ähnlichen Schema wie bei Funktion 5.

Die Dateinamen sind dabei beliebig. Eine Datei zur Anzeige von Isländern könnte z.B. wie folgt aussehen:

```
Isländer
Tölt: Tölt, Töltrennen
Pass: Rennpass, Passrennen
Ausbildung
=
Exterieur: Haltung, Ausdruck, Kopf, Halsansatz, Rückenlinie, Beinstellung
Gangarten: Tölt, Rennpass
Rennen: Töltrennen, Passrennen
```

Die erste Zeile definiert die Rassen, die angezeigt werden sollen. Das können auch mehrere sein, durch Kommata getrennt.

Jede folgende Zeile definiert eine Tabellenspalte in der auszugebenden Pferdeliste.

Die Angabe einer einzelnen Kategorie (hier z.B. Ausbildung) sorgt für die Ausgabe des Durchschnittswertes für diese Kategorie.

Ein Doppelpunkt signalisiert, dass der Durchschnittwert der folgenden Einzelwerte berechnet werden soll (hier z.B. Tölt: Tölt, Töltrennen). Das Wort vor dem Doppelpunkt wird als Spaltenüberschrift verwendet.

Die Tabelle enthält immer automatisch eine Spalte für das Alter, eine für Gesamtpotenzial und eine für die Gesamtbewertung. Letztere ist der Durchschnittwert aus den selbst-definierten Spaltenwerten.

Enthält eine Spalte ein Gleichheitszeichen, werden die Einträge nach dem Gleichheitszeichen nicht in die Gesamtbewertung mit einbezogen.

Ein besonderes Schlüsselwort, bei dem kein Durchschnittswert berechnet wird, ist z.B. Fellfarbe. Dies darf nicht vor dem Gleichheitszeichen stehen.

![listing](https://beachomize.de/ponyspiel_image/Auflistung.JPG)

Stuten sind in Rot, Hengste in blauer Schrift dargestellt. Noch nicht ausgewachsene Pferde sind in einer helleren Farbe dargestellt.

Durch Klick auf einen Spaltennamen werden die Pferde absteigend nach dieser Spalte sortiert.

Der Wert über einem Spaltennamen zeigt den Gesamtwert der Kategorie des Pferdes mit dem Höchstwert in dieser Spalte an.

#### Aufruf eines Pferds im Browser

Linksklick auf einen Pferdenamen in der Auflistung öffnet die Pferdeseite im Browser. Möglicherweise muss zuerst der Spiel-Login im Browser erfolgen.

#### Anzeigen von Verwandten

Rechtsklick auf einen Pferdenamen färbt alle Pferde schwarz, die gemeinsame Eltern oder Großeltern mit dem angeklickten Pferd haben - also nicht für die Zucht erlaubt sind.

#### Löschen des Cache

Linksklick auf das Bild des Pferdes in der Auflistung löscht den lokalen Cache des Pferdes. Beim nächsten Aufruf werden die Werte neu aus dem Spiel geladen.

### 9 - Markt-Suche

Durchsuchen von Pferdehandel, Deckstation oder Pferderegister (auswählbar unter **a**). Dies filtert die Pferde aus dem Spiel nach Rasse (auswählbar unter **b**) und sortiert sie nach der unter **c** auswählbaren Methode.

Es wird die unter **e** ausgewählte Anzahl an Seiten ausgewertet. Die Auflistung wird mithilfe der _listing_-Dateien, die auch für Funktion 8 verwendet werden, erstellt (auswählbar unter **d**).

Zusätzlich wird der Preis angezeigt.

### 10 - Cache löschen

Der lokale Cache kann komplett, nur für nicht-eigene Pferde oder für das aktuell geladene Pferd gelöscht werden. Dies ist z.B. sinnvoll, wenn sich Werte durch Training verändert haben.

### 11 - Deckstation-Benachrichtigung

Erhalte eine Benachrichtigung, sobald das Pferd in die Deckstation gestellt wird. Die Benachrichtigung wird
 
1. im Programm selbst angezeigt und

2. per Telegram versendet, falls im Login-Fenster (Funktion 1) eine gültige Telegram-ID eingegeben wurde.

Um eine Telegram-Benachrichtigung zu erhalten, muss der Bot _@PonyspielBot_ auf dem Telefon aktiviert sein.

## Systemvoraussetzungen

#### Nur getestet auf Windows!

### Python 3

mit folgenden Paketen

- tkinter
- requests
- Pillow

### Alternativ

_dist/pony_gui.exe_ sollte ohne Installation von Python auf Windows funktionieren.
