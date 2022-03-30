import requests
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
import pickle
import csv
import shutil
import traceback
from datetime import datetime


from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def add_margin(pil_img, top, right, bottom, left, color):
    width, height = pil_img.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(pil_img.mode, (new_width, new_height), color)
    result.paste(pil_img, (left, top))
    return result


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super(MyHTMLParser, self).__init__()

        # block management
        self.block_types = ['none', 'name', 'facts', 'details', 'training', 'ausbildung', 'gangarten', 'dressur',
                            'springen', 'military', 'western', 'rennen', 'fahren', 'charakter-training', 'pedigree',
                            'alert', 'energy', 'care']
        self.training_block_types = ['training', 'ausbildung', 'gangarten', 'dressur', 'springen', 'military',
                                     'western', 'rennen', 'fahren', 'charakter-training']
        self.block = 'none'
        self.tag_counter = 0

        # variables needed for reading data
        self.next_data_type = ''
        self.span_id = ''
        self.span_value_entered = False

        self.energy_read_now = False
        self.pedigree_id_temp = 0
        self.pedigree_unknown_counter = 0
        self.alert_type = ''

        # Query containers
        # 'Trainingszustand' removed
        self.details_headings = ['Gesundheit', 'Zufriedenheit', 'Robustheit', 'Hufe', 'Zähne', 'Impfungen', 'Wurmkur',
                                 'Charakter', 'Vertrauen', 'Intelligenz', 'Mut', 'Aufmerksamkeit', 'Gehorsam',
                                 'Gelassenheit', 'Nervenstärke', 'Siegeswille', 'Motivation', 'Gutmütigkeit',
                                 'Genauigkeit', 'Auffassungsvermögen',
                                 'Exterieur', 'Bemuskelung', 'Bewegungen', 'Haltung', 'Ausdruck', 'Kopf', 'Halsansatz',
                                 'Rückenlinie', 'Beinstellung']
        self.gesundheit_headings = self.details_headings[
                                   self.details_headings.index('Gesundheit'):self.details_headings.index('Charakter')]
        self.charakter_headings = self.details_headings[
                                  self.details_headings.index('Charakter'):self.details_headings.index('Exterieur')]
        self.exterieur_headings = self.details_headings[self.details_headings.index('Exterieur'):]
        self.training_headings = ['Gesamtpotenzial', 'Ausbildung', 'Gangarten', 'Dressur', 'Springen', 'Military',
                                  'Western', 'Rennen', 'Fahren', 'Charakter-Training']
        self.facts_headings = ['Rufname', 'Besitzer', 'Züchter', 'Rasse', 'Alter', 'Geburtstag', 'Stockmaß',
                               'Erwartetes Stockmaß', 'Fellfarbe']
        # additionaly, there are 'Geschlecht' and 'Fohlen' which are extracted differently (handle_starttag), also 'deckstation' and 'verkauf' for price
        self.fohlenerziehung_headings = ['Kopf streicheln', 'Körper berühren', 'Hufe anfassen', 'Halfter tragen',
                                         'Führen', 'Putzen', 'Hufe geben']
        self.fohlenerziehung_codes = [3001 + i for i in range(7)]
        self.ausbildung_headings = ['Ausbildung',
                                    'Stärke', 'Trittsicherheit', 'Ausdauer', 'Geschwindigkeit', 'Beschleunigung',
                                    'Wendigkeit', 'Sprungkraft', 'taktrein', 'Geschicklichkeit',
                                    'Sand', 'Gras', 'Erde', 'Schnee', 'Lehm', 'Späne',
                                    'Halle', 'Arena', 'draußen', 'sehr weich', 'weich', 'mittel', 'hart', 'sehr hart']
        self.ausbildung_codes = [101 + i for i in range(9)] + [130 + i for i in range(6)] + [150 + i for i in
                                                                                             range(3)] + [170 + i for i
                                                                                                          in range(5)]
        self.gangarten_headings = ['Gangarten', 'Schritt', 'Trab', 'leichter Galopp', 'Galopp', 'Rückwärts richten',
                                   'Slow Gait',
                                   'Tölt', 'Paso', 'Rack', 'Walk', 'Marcha Batida', 'Jog', 'Indian Shuffle', 'Foxtrott',
                                   'Marcha Picada', 'Rennpass', 'Single Foot', 'Saddle Gait',
                                   'Trailwalk', 'Slow Canter', 'Lope', 'Running Walk', 'Flatfoot Walk', 'Sobreandando',
                                   'Paso Llano', 'Termino', 'Classic Fino', 'Paso Corto', 'Paso Largo', 'Trocha',
                                   'Trote Y Galope']
        self.gangarten_codes = [200 + i for i in range(31)]

        # Verstärkt & Versammelt
        self.dressur_headings = ['Dressur', 'starker Schritt', 'starker Trab', 'starker Galopp', 'versammelter Schritt',
                                 'versammelter Trab', 'versammelter Galopp',
                                 # Attribute
                                 'Losgelassenheit', 'Anlehnung', 'Schwung', 'Durchlässigkeit', 'Geraderichtung',
                                 'Geschmeidigkeit', 'Serienwechsel', 'Übergänge', 'Balance', 'Elastizität', 'Raumgriff',
                                 'Bergauftendenz',
                                 # Grundlagen
                                 'Halten', 'Arbeitstrab', 'Galoppwechsel', 'Außengalopp', 'Hinterhandwendung',
                                 'Kurzkehrtwendung', 'Vorhandwendung', 'Passage', 'Piaffe', 'Pirouette', 'Schultervor',
                                 'Renvers', 'Traversale', 'Schaukel',
                                 'Traversalverschiebungen', 'Kehrtwendevorhand', 'Kehrtwendehinterhand',
                                 'halbe Pirouette', 'Schulterherein', 'Galoppsprünge verlängern', 'Tritte verlängern',
                                 # Hohe Schule
                                 'Spanischer Tritt', 'Ballotade', 'Courbette', 'Croupade', 'Kapriole', 'Levade',
                                 'Pesade', 'Mezair', 'Terre à Terre', 'Spanischer Trab', 'Sarabande', 'Piaffepirouette',
                                 'Passagetravers']
        # [375 + i for i in range(7)] + [383 + i for i in range(4)] sind der Block 'Attribute' da 382 fehlt
        self.dressur_codes = [300 + i for i in range(6)] \
                             + [375 + i for i in range(12)] \
                             + [307, 306] + [310 + i for i in range(19)] \
                             + [350 + i for i in range(13)]

        self.springen_headings = ['Springen', 'Steilsprung', 'Wassergraben', '2er Kombination', '3er Kombination',
                                  'Mauer', 'Eisenbahnschranken', 'Gatter', 'Rick', 'Kreuz', 'Planke', 'Palisade',
                                  'Oxer', 'Triplebarre', 'Überbautes Wasser', 'Buschoxer', 'Birkenoxer', 'Doppelrick',
                                  'Pulvermanns Grab', 'Irische Wälle', 'Holsteiner Wegesprünge', 'Wall']
        self.springen_codes = [400 + i for i in range(11)] + [440 + i for i in range(6)] + [470 + i for i in range(4)]

        self.military_headings = ['Military', 'Bank', 'Hecke', 'Coffin', 'Eulenloch', 'Normandiebank',
                                  'Schmales Hindernis', 'Sunkenroad',
                                  'Hogback', 'Wasser', 'Arrow Head', 'Graben', 'Steinwand', 'Bürste', 'Ecke',
                                  'Trakehnergraben',
                                  'Wassereinsprung', 'Wasseraussprung', 'Rolltop', 'Tisch', 'Strohsprung', 'Bullfinish',
                                  'Doppelfass']
        self.military_codes = [500 + i for i in range(22)]

        # Reining
        self.western_headings = ['Western', 'Sliding Stop', 'Spin', 'Roll Back', 'Back Up', 'Rundown', 'Circles',
                                 'Turn', 'Figure Eight', 'Railwork',
                                 # Cutting
                                 'Cow Sense', 'Cow Focus', 'Cow Seperation', 'Dry Work', 'Fence Work', 'Roping',
                                 # Trail
                                 'Brücke', 'Gate', 'L-Hindernis', 'U-Hindernis', 'Rückwärts durch das Hindernis',
                                 'Sidepass', 'Tempowechsel', 'Halt', 'Pole Bending', 'Barrel Race',
                                 'Lopes', 'Flying Lead Changes', 'Rein Back', 'Sideways', 'Schlangenlinie',
                                 'Rods Alley']  # deprecated
        self.western_codes = [600, 601, 607, 602, 614, 613, 612, 619, 615] \
                             + [620 + i for i in range(5)] + [609] \
                             + [626, 625, 627, 628, 630, 616] + [603 + i for i in range(4)] + [608, 610, 611, 617, 618,
                                                                                               629]

        # Rennart
        self.rennen_headings = ['Rennen', 'Sulky', 'Distanzrennen', 'Flachrennen', 'Trabrennen',
                                # Attribute
                                'Start', 'Fliegender Start', 'Autostart', 'Bänderstart', 'Startbox',
                                # Attribute
                                'Hindernisrennen', 'Linkskurve', 'Rechtskurve', 'kurze Distanz', 'mittlere Distanz',
                                'lange Distanz', 'Endspurt', 'Sprint']  # deprecated

        self.rennen_codes = [701, 703, 705, 706] + [751 + i for i in range(5)] + [700, 702, 704, 756, 757, 758, 750, 759]

        # Dressur
        self.fahren_headings = ['Fahren', 'Zügel in einer Hand', 'Schritt am langen Zügel', 'Volte', 'Links lenken',
                                'Rechts lenken', 'S-Kurve', 'Schleife', 'Trab am langen Zügel', 'Still stehen',
                                'Pull Back',
                                # Marathon
                                'Zick Zack Kegel', 'Kegel im Kreis', 'Kegel S-Kurve', 'Kegel in einer Schleife',
                                'U-Kurve', 'L-Biegung', 'Kegel auf einer Schlangenlinie',
                                # Geschicklichkeit
                                'Holzhindernis', 'Trail Brücke', 'Strohballen', 'Wasserhindernis', 'Trail Sektion',
                                'Tonnen', 'Flaggen', 'Huegel', 'Baumstamm', 'Bäume', 'Schlangenlinien Volte',
                                # Anspannungen
                                'Einspänner', 'Zweispänner', 'Tandem', 'Dreispänner', 'Random', 'Einhorn',
                                'Verkehrtes Einhorn',
                                'Quadriga', 'Vierspänner', 'Fünfspänner', 'Sechsspänner', 'Wildgang']  # deprecated
        self.fahren_codes = [801] + [805 + i for i in range(9)] \
                            + [804] + [814 + i for i in range(6)] \
                            + [802, 803] + [820 + i for i in range(9)] \
                            + [850 + i for i in range(12)]

        self.charakter_training_headings = ['Bodenarbeit', 'Spaziergang', 'Longenarbeit', 'Freiheitsdressur',
                                            'Desensibilisierung', 'Zirzensik', 'Dualaktivierung', 'Gymnastikreihe',
                                            'Freispringen', 'Liberty', 'Working Equitation', 'Handarbeit']
        self.charakter_training_codes = [2001 + i for i in range(12)]

        self.care_ids = ['brushpg', 'waterpg', 'langhaarpg', 'foodpg', 'hufpg', 'liebepg', 'ausmistenpg']
        self.care_query_params = {'brushpg': 'brush', 'waterpg': 'water', 'langhaarpg': 'haar', 'foodpg': 'food',
                                  'hufpg': 'hufe', 'liebepg': 'liebe', 'ausmistenpg': 'boxclean'}
        self.care_query_pages = {'brushpg': 'brush', 'waterpg': 'water', 'langhaarpg': 'hair', 'foodpg': 'food',
                                 'hufpg': 'hufe', 'liebepg': 'streicheln', 'ausmistenpg': 'ausmisten'}

        # result containers
        self.name = ''
        self.energy = -1
        self.facts_values = dict()
        self.details_values = dict()
        self.gesundheit_values, self.charakter_values, self.exterieur_values = dict(), dict(), dict()
        self.training_values = dict()
        self.ausbildung_values, self.gangarten_values, self.dressur_values, self.springen_values = dict(), dict(), dict(), dict()
        self.military_values, self.western_values, self.rennen_values, self.fahren_values = dict(), dict(), dict(), dict()
        self.charakter_training_values, self.fohlenerziehung_values = dict(), dict()
        self.training_max = dict()
        self.ausbildung_max, self.gangarten_max, self.dressur_max, self.springen_max = dict(), dict(), dict(), dict()
        self.military_max, self.western_max, self.rennen_max, self.fahren_max = dict(), dict(), dict(), dict()
        self.charakter_training_max, self.fohlenerziehung_max = dict(), dict()
        self.care_values = dict()
        self.image_urls = []
        self.ancestors = []
        self.has_box = True

    def is_in_block(self):
        return self.block != 'none'

    def exit_block(self):
        self.block = 'none'
        self.next_data_type = ''
        self.span_id = ''
        self.span_value_entered = False

    def enter_block(self, block_type):
        if block_type in self.block_types:
            self.block = block_type
            self.tag_counter = 1
        else:
            print("Exception: Invalid block type")
            raise Exception()

    def handle_starttag(self, tag, attrs):
        # ============================= Statements for entering blocks ==========================================================
        if not self.is_in_block() and tag == 'button' and len(attrs) > 0:
            if attrs[0] == ('class', 'tooltipover'):
                data_content = (None, None)
                for tup in attrs:
                    if tup[0] == 'data-content':
                        data_content = tup
                        break
                if data_content[0] is not None:
                    if 'trächtig' in data_content[1]:
                        date = data_content[1][data_content[1].index('(') + 1:data_content[1].index(')')]
                        self.facts_values['Fohlen'] = date
                    elif data_content[1].strip() == 'Stute':
                        self.facts_values['Geschlecht'] = 'Stute'
                    elif data_content[1].strip() == 'Hengst':
                        self.facts_values['Geschlecht'] = 'Hengst'

        if not self.is_in_block() and tag == 'div' and len(attrs) > 0:
            if len(self.name) == 0 and attrs[0] == ('class', 'main'):
                # Start des Seiteninhalts. Das nächste Stück Text (h2-Überschrift) beinhaltet den Namen des Pferdes
                self.enter_block('name')

            if not self.is_in_block() and len(self.name) > 0 and tag == 'div' and len(attrs) > 0:
                if self.energy == -1 and attrs[0] == ('class', 'col-lg-4'):
                    # Erste Progress-Bar im Seiteninhalt. Danach folgt die Energie-Angabe
                    self.enter_block('energy')

            if ('role', 'alert') in attrs:
                # grey alert area above name. Includes market price etc.
                self.enter_block('alert')
                self.alert_type = ''

            elif attrs[0] == ('id', 'facts'):
                self.enter_block('facts')

            elif attrs[0] == ('id', 'health'):
                self.enter_block('details')

            elif attrs[0] == ('id', 'care'):
                self.enter_block('care')

            elif attrs[0] == ('id', 'traintab'):
                self.enter_block('training')

            elif attrs[0] == ('id', 'traintabausbildung'):
                self.enter_block('ausbildung')

            elif attrs[0] == ('id', 'traintabgangarten'):
                self.enter_block('gangarten')

            elif attrs[0] == ('id', 'traintabdressur'):
                self.enter_block('dressur')

            elif attrs[0] == ('id', 'traintabspringen'):
                self.enter_block('springen')

            elif attrs[0] == ('id', 'traintabmilitary'):
                self.enter_block('military')

            elif attrs[0] == ('id', 'traintabwestern'):
                self.enter_block('western')

            elif attrs[0] == ('id', 'traintabrennen'):
                self.enter_block('rennen')

            elif attrs[0] == ('id', 'traintabfahren'):
                self.enter_block('fahren')

            elif attrs[0] == ('id', 'traintabcharakter'):
                self.enter_block('charakter-training')

            elif attrs[0] == ('id', 'pedigree'):
                self.enter_block('pedigree')

        # ============================ Incrementing tag counter ================================================================
        elif self.is_in_block():
            if tag == 'div':
                self.tag_counter += 1

            # ============================ Block specifics - only executed if in block =============================================
            if self.block == 'energy':
                if tag == 'span' and len(attrs) > 0:
                    if attrs[0] == ('id', 'apvalue'):
                        self.energy_read_now = True

            if self.block in self.training_block_types:
                if tag == 'span':
                    if len(attrs) > 0:
                        self.span_id = attrs[0][1]
                    else:
                        self.span_id = 'some'

            if self.block == 'facts':
                # Sammeln der Bild-URLs
                if tag == 'img':
                    for tup in attrs:
                        if tup[0] == 'src' or tup[0] == 'data-src':
                            self.image_urls.append(tup[1])
                            break

            if self.block == 'pedigree':
                # Durch 'Sammeln der Eltern und Großeltern' gespeicherte id eintragen (nur bei Ponies mit Bild)
                if tag == 'img' and self.pedigree_id_temp != 0:
                    self.ancestors.append(self.pedigree_id_temp)
                    self.pedigree_id_temp = 0
                # Sammeln der Eltern und Großeltern
                elif tag == 'a':
                    for tup in attrs:
                        if tup[0] == 'href':
                            val = tup[1]
                            search_string = 'horse.php?id='
                            if search_string in val:
                                # Nach einem Pony-Link folgen eventuell "unbekannt"-Einträge
                                # Wenn der Vater ein Systempferd ist, sind es 14 Stück, ansonsten 12 oder weniger
                                # In ersterem Fall wird der Vater wiederholt, damit an Index 0 und 3 die Eltern stehen
                                if self.pedigree_unknown_counter == 14:
                                    self.ancestors.append(self.ancestors[-1])
                                    self.ancestors.append(self.ancestors[-1])
                                self.pedigree_unknown_counter = 0
                                index = val.index(search_string) + len(search_string)
                                id_string = ''
                                while index < len(val) and val[index].isnumeric():
                                    id_string += val[index]
                                    index += 1
                                id = int(id_string)
                                if not id in self.ancestors:
                                    self.pedigree_id_temp = id
                else:
                    self.pedigree_id_temp = 0

            if self.block == 'care':
                if tag == 'div' and len(attrs) > 0:
                    if attrs[0][0] == 'id' and attrs[0][1] in self.care_ids:
                        sty = [[]]
                        for a in attrs:
                            if a[0] == 'style':
                                sty = a[1].split(':')
                                break
                        progress_value = 100
                        if 'width' in sty[0]:
                            num = sty[1].split('%')[0].strip()
                            try:
                                progress_value = float(num)
                            except:
                                pass
                        self.care_values[attrs[0][1]] = progress_value

    def handle_endtag(self, tag):
        # =========================== Decrementing tag counter and exiting block ================================================
        if self.is_in_block():
            if tag == 'div':
                self.tag_counter -= 1
                if self.tag_counter <= 0:
                    self.exit_block()

            # =========================== Handling span tags for reading training values ============================================
            if self.block in self.training_block_types:
                if tag == 'span':
                    self.span_id = ''
                if self.span_value_entered and tag == 'div':
                    self.span_value_entered = False
                    self.next_data_type = ''

    def handle_data(self, data):
        content = data.strip()

        if self.block == 'name':
            if len(content) > 0:
                self.name = content
                self.tag_counter = 0  # leave block at next div close

        if self.block == 'energy' and self.energy_read_now:
            if len(content) > 0 and content.isnumeric():
                self.energy = int(content)
                self.energy_read_now = False
                self.tag_counter = 0  # leave block at next div close

        if self.block == 'alert':
            def get_val():
                s = ''
                first_num = False
                for c in content:
                    if c.isnumeric():
                        first_num = True
                        s += c
                    elif first_num:
                        break
                return s

            cont_low = content.lower()
            if 'deckstation' in cont_low and 'club' not in cont_low:
                self.alert_type = 'deckstation'
            elif 'verkauf' in cont_low and 'club' not in cont_low:
                self.alert_type = 'verkauf'
            elif 'eigene box' in cont_low:
                self.has_box = False
            elif self.alert_type == 'deckstation':
                self.facts_values['deckstation'] = int(get_val())
                self.alert_type = ''
            elif self.alert_type == 'verkauf':
                self.facts_values['verkauf'] = int(get_val())
                self.alert_type = ''

        if self.block == 'facts':
            # if len(self.next_data_type) == 0 and content in self.facts_headings:
            if content in self.facts_headings:
                self.next_data_type = content
                self.facts_values[self.next_data_type] = ''
            elif len(self.next_data_type) > 0 and len(content) > 0:
                if not content.lower() == 'kurzbeschreibung':
                    self.facts_values[self.next_data_type] = content
                self.next_data_type = ''

        if self.block == 'details':
            # if len(self.next_data_type) == 0 and content in self.details_headings:
            if content in self.details_headings:
                self.next_data_type = content
            elif len(self.next_data_type) > 0 and len(content) > 0:
                self.details_values[self.next_data_type] = int(content)
                self.next_data_type = ''

        if self.block in self.training_block_types:
            list_index = self.training_block_types.index(self.block)
            block_headings = \
            [self.training_headings, self.fohlenerziehung_headings + self.ausbildung_headings, self.gangarten_headings,
             self.dressur_headings, self.springen_headings,
             self.military_headings, self.western_headings, self.rennen_headings, self.fahren_headings,
             self.charakter_training_headings][list_index]
            block_values = [self.training_values, self.ausbildung_values, self.gangarten_values, self.dressur_values,
                            self.springen_values,
                            self.military_values, self.western_values, self.rennen_values, self.fahren_values,
                            self.charakter_training_values][list_index]
            block_max = \
            [self.training_max, self.ausbildung_max, self.gangarten_max, self.dressur_max, self.springen_max,
             self.military_max, self.western_max, self.rennen_max, self.fahren_max, self.charakter_training_max][
                list_index]
            # if len(self.next_data_type) == 0 and content in block_headings:
            if content in block_headings:
                self.next_data_type = content
            elif len(self.next_data_type) > 0 and len(content) > 0:
                if list_index == 1 and self.next_data_type in self.fohlenerziehung_headings:
                    block_values = self.fohlenerziehung_values
                    block_max = self.fohlenerziehung_max
                # We need to read either one value
                # or multiple, if the first of them occured within a span tag
                # It's multiple (two) values if there is one trained value and one max value
                if len(self.span_id) == 0 and not self.span_value_entered:
                    # We are not within a span tag, and we have not been previously
                    # Only one value has to be read
                    block_values[self.next_data_type] = int(content)
                    block_max[self.next_data_type] = int(content)
                    self.next_data_type = ''
                else:
                    # We are either within a span tag, or we have previously been
                    if len(self.span_id) > 0:
                        # we are in a span -> We can just add the value to the list
                        if self.span_value_entered:
                            # second span
                            block_max[self.next_data_type] = int(content)
                        else:
                            # first span
                            block_values[self.next_data_type] = int(content)
                            self.span_value_entered = True
                    elif len(content) > 1 and '/' in content:
                        # We are not in a span -> normally there is just a dash, which we don't want to store
                        # but sometimes they failed to put the second value in a span and it just follows the dash -> then we need to extract it
                        cont = ''.join(c for c in content if c.isdigit())
                        if len(cont) > 0:
                            block_max[self.next_data_type] = int(cont)

        if self.block == 'pedigree':
            if content.lower() == 'unbekannt':
                self.pedigree_unknown_counter += 1


class BeautyParser(HTMLParser):
    def __init__(self):
        super(BeautyParser, self).__init__()
        self.block_types = ['main']
        self.competition_values = ['0a', '0b', '0c', '0d', '0e', '1a', '1b', '1c', '1d', '1e', '2a', '2b', '2c', '2d',
                                   '2e',
                                   '3a', '3b', '3c', '3d', '3e', '4a', '4b', '4c', '4d', '4e', '5a', '5b', '5c', '5d',
                                   '5e']
        self.competition_found = False
        self.value = None

        self.h2 = 0  # 0: First heading not yet found, 1: Now in first heading, 2: First heading was already processed
        self.continue_parsing = True

        self.block = 'none'
        self.tag_counter = 0

    def is_in_block(self):
        return self.block != 'none'

    def exit_block(self):
        self.block = 'none'

    def enter_block(self, block_type):
        if block_type in self.block_types:
            self.block = block_type
            self.tag_counter = 1
        else:
            print("Exception: Invalid block type")
            raise Exception()

    def handle_starttag(self, tag, attrs):
        if not self.is_in_block() and tag == 'div' and ('class', 'main') in attrs:
            self.enter_block('main')

        elif self.is_in_block():
            if tag == 'div':
                self.tag_counter += 1

        if self.continue_parsing and self.block == 'main':
            if tag == 'h2' and self.h2 == 0:
                self.h2 = 1
            if tag == 'input' and not self.competition_found:
                for tup in attrs:
                    if tup[0] == 'value' and tup[1] in self.competition_values:
                        self.value = tup[1]
                    elif tup[0] == 'disabled':
                        self.value = None
                        break
                if self.value is not None:
                    self.competition_found = True

    def handle_endtag(self, tag):
        # =========================== Decrementing tag counter and exiting block ================================================
        if self.is_in_block():
            if tag == 'div':
                self.tag_counter -= 1
                if self.tag_counter <= 0:
                    self.exit_block()

    def handle_data(self, data):
        if self.continue_parsing and self.block == 'main' and self.h2 == 1:
            self.h2 = 2
            if 'Schönheitswettbewerb' not in data:
                # stop parsing if the first heading is not Schönheitswettbewerb heading
                self.continue_parsing = False


class FakeParser(MyHTMLParser):
    def __init__(self, image_urls, pony_dict):
        super(FakeParser, self).__init__()
        for head in self.facts_headings:
            self.facts_values[head] = 0
        for head in self.details_headings:
            self.details_values[head] = 0
        for head in self.gesundheit_headings:
            self.gesundheit_values[head] = 0
        for head in self.charakter_headings:
            self.charakter_values[head] = 0
        for head in self.exterieur_headings:
            self.exterieur_values[head] = 0
        for head in self.training_headings:
            self.training_max[head] = 0
            self.training_values[head] = 0
        for head in self.ausbildung_headings:
            self.ausbildung_max[head] = 0
            self.ausbildung_values[head] = 0
        for head in self.gangarten_headings:
            self.gangarten_max[head] = 0
            self.gesundheit_values[head] = 0
        for head in self.dressur_headings:
            self.dressur_max[head] = 0
            self.dressur_values[head] = 0
        for head in self.springen_headings:
            self.springen_max[head] = 0
            self.springen_values[head] = 0
        for head in self.military_headings:
            self.military_max[head] = 0
            self.military_values[head] = 0
        for head in self.western_headings:
            self.western_max[head] = 0
            self.western_values[head] = 0
        for head in self.rennen_headings:
            self.rennen_max[head] = 0
            self.rennen_values[head] = 0
        for head in self.fahren_headings:
            self.fahren_max[head] = 0
            self.fahren_values[head] = 0

        self.image_urls = image_urls
        if len(pony_dict) > 0:
            self.name = pony_dict['Name']
            self.facts_values['Geschlecht'] = pony_dict['Geschlecht']
            self.facts_values['Rasse'] = pony_dict['Rasse']
            self.facts_values['Alter'] = pony_dict['Alter']
            self.facts_values['Fellfarbe'] = pony_dict['Fellfarbe']
            self.details_values['Gesundheit'] = pony_dict['Gesundheit']
            self.gesundheit_values['Gesundheit'] = pony_dict['Gesundheit']
            self.details_values['Charakter'] = pony_dict['Charakter']
            self.charakter_values['Charakter'] = pony_dict['Charakter']
            self.details_values['Exterieur'] = pony_dict['Exterieur']
            self.exterieur_values['Exterieur'] = pony_dict['Exterieur']
            self.training_max['Ausbildung'] = pony_dict['Ausbildung']
            self.training_max['Gesamtpotenzial'] = pony_dict['Gesamtpotenzial']
            self.ausbildung_max['Ausbildung'] = pony_dict['Ausbildung']
            self.training_max['Gangarten'] = pony_dict['Gangarten']
            self.gangarten_max['Gangarten'] = pony_dict['Gangarten']
            self.training_max['Dressur'] = pony_dict['Dressur']
            self.dressur_max['Dressur'] = pony_dict['Dressur']
            self.training_max['Springen'] = pony_dict['Springen']
            self.springen_max['Springen'] = pony_dict['Springen']
            self.training_max['Military'] = pony_dict['Military']
            self.military_max['Military'] = pony_dict['Military']
            self.training_max['Western'] = pony_dict['Western']
            self.western_max['Western'] = pony_dict['Western']
            self.training_max['Rennen'] = pony_dict['Rennen']
            self.rennen_max['Rennen'] = pony_dict['Rennen']
            self.training_max['Fahren'] = pony_dict['Fahren']
            self.fahren_max['Fahren'] = pony_dict['Fahren']
            if 'Preis' in pony_dict.keys():
                self.facts_values['verkauf'] = pony_dict['Preis']
                self.facts_values['deckstation'] = pony_dict['Preis']


class ListParser(HTMLParser):
    def __init__(self):
        super(ListParser, self).__init__()
        self.in_main = False
        self.main_tag_counter = 0
        self.images_done = False

        self.in_a = False

        self.in_price = False

        self.in_values = False
        self.values_tag_counter = 0
        self.values_column_counter = 0

        self.block_types = ['row']

        self.block = 'none'
        self.tag_counter = 0

        self.ponies = [dict()]
        self.images = [[]]

    def is_in_block(self):
        return self.block != 'none'

    def exit_block(self):
        self.block = 'none'

    def enter_block(self, block_type):
        if block_type in self.block_types:
            self.block = block_type
            self.tag_counter = 1
        else:
            print("Exception: Invalid block type")
            raise Exception()

    def handle_starttag(self, tag, attrs):
        if not self.in_main and tag == 'div' and ('class', 'main') in attrs:
            self.in_main = True
            self.main_tag_counter = 1
        elif self.in_main and tag == 'div':
            self.main_tag_counter += 1

        if self.in_main and not self.is_in_block() and tag == 'div' and ('class', 'row') in attrs:
            self.enter_block('row')
            self.images_done = False
            self.values_column_counter = 0
            if len(self.ponies[-1]) > 0:
                self.ponies.append(dict())
            if len(self.images[-1]) > 0:
                self.images.append([])
        elif self.is_in_block():
            if tag == 'div':
                self.tag_counter += 1

        if self.block == 'row':
            if tag == 'a':
                self.in_a = True
            elif self.in_a and tag == 'img':
                for tup in attrs:
                    if tup[0] == 'src' or tup[0] == 'data-src':
                        self.images[-1].append(tup[1])
                        break
            elif self.images_done:
                if not self.in_values and tag == 'div':
                    self.in_values = True
                    self.values_tag_counter = 1
                    self.values_column_counter += 1
                elif self.in_values and tag == 'div':
                    self.values_tag_counter += 1
                    if ('class', 'row') in attrs and 'Preis' not in self.ponies[-1].keys():
                        self.in_price = True
                elif self.in_values and tag == 'button' and not ('class', 'tooltipover') in attrs and 'Preis' not in \
                        self.ponies[-1].keys():
                    self.in_price = True
                elif self.in_values and tag == 'i' and 'Geschlecht' not in self.ponies[-1].keys():
                    for tup in attrs:
                        if tup[0] == 'title':
                            self.ponies[-1]['Geschlecht'] = tup[1]
                            break

    def handle_endtag(self, tag):
        # =========================== Decrementing tag counter and exiting block ================================================
        if self.is_in_block():
            if tag == 'div':
                self.tag_counter -= 1
                if self.tag_counter <= 0:
                    self.exit_block()
        if self.in_main:
            if tag == 'div':
                self.main_tag_counter -= 1
                if self.main_tag_counter <= 0:
                    self.in_main = False
        if self.in_a and tag == 'a':
            self.in_a = False
            self.images_done = True
        if self.in_values and tag == 'div':
            self.values_tag_counter -= 1
            if self.values_tag_counter <= 0:
                self.in_values = False

    def handle_data(self, data):
        if self.in_values:
            keys = self.ponies[-1].keys()
            strp = data.strip()
            if len(strp) > 0:
                # second column
                if self.values_column_counter == 1:
                    if self.in_price:
                        self.ponies[-1]['Preis'] = strp
                        self.in_price = False
                    else:
                        if 'Name' not in keys:
                            self.ponies[-1]['Name'] = strp
                        elif 'Rasse' not in keys:
                            self.ponies[-1]['Rasse'] = strp
                        elif 'Alter' not in keys:
                            if len(strp) > 0:
                                if 'Gesundheit' in strp:  # Ponies that are below 6 month show up in allhorses, but have no age
                                    self.ponies[-1]['Alter'] = '1 Monat'
                                    if 'Gesundheit' not in keys:
                                        splt = strp.split()
                                        if 'Gesundheit' in splt[0]:
                                            self.ponies[-1]['Gesundheit'] = int(splt[1])
                                else:
                                    self.ponies[-1]['Alter'] = strp
                        elif 'Gesundheit' not in keys:
                            splt = strp.split()
                            if 'Gesundheit' in splt[0]:
                                self.ponies[-1]['Gesundheit'] = int(splt[1])
                        elif 'Charakter' not in keys:
                            splt = strp.split()
                            if 'Charakter' in splt[0]:
                                self.ponies[-1]['Charakter'] = int(splt[1])
                        elif 'Exterieur' not in keys:
                            splt = strp.split()
                            if 'Exterieur' in splt[0]:
                                self.ponies[-1]['Exterieur'] = int(splt[1])
                        elif 'Fellfarbe' not in keys:
                            self.ponies[-1]['Fellfarbe'] = strp
                elif self.values_column_counter == 2:
                    # third column
                    if 'Gesamtpotenzial' not in keys:
                        splt = strp.split()
                        if 'Gesamtpotenzial' in splt[0]:
                            self.ponies[-1]['Gesamtpotenzial'] = int(splt[1])
                    elif 'Ausbildung' not in keys:
                        splt = strp.split()
                        if 'Ausbildung' in splt[0]:
                            self.ponies[-1]['Ausbildung'] = int(splt[1])
                    elif 'Gangarten' not in keys:
                        splt = strp.split()
                        if 'Gangarten' in splt[0]:
                            self.ponies[-1]['Gangarten'] = int(splt[1])
                    elif 'Dressur' not in keys:
                        splt = strp.split()
                        if 'Dressur' in splt[0]:
                            self.ponies[-1]['Dressur'] = int(splt[1])
                    elif 'Springen' not in keys:
                        splt = strp.split()
                        if 'Springen' in splt[0]:
                            self.ponies[-1]['Springen'] = int(splt[1])
                    elif 'Military' not in keys:
                        splt = strp.split()
                        if 'Military' in splt[0]:
                            self.ponies[-1]['Military'] = int(splt[1])
                    elif 'Western' not in keys:
                        splt = strp.split()
                        if 'Western' in splt[0]:
                            self.ponies[-1]['Western'] = int(splt[1])
                    elif 'Rennen' not in keys:
                        splt = strp.split()
                        if 'Rennen' in splt[0]:
                            self.ponies[-1]['Rennen'] = int(splt[1])
                    elif 'Fahren' not in keys:
                        splt = strp.split()
                        if 'Fahren' in splt[0]:
                            self.ponies[-1]['Fahren'] = int(splt[1])


class DeckstationLoginParser(HTMLParser):
    def __init__(self):
        super(DeckstationLoginParser, self).__init__()

    def handle_starttag(self, tag, attrs):
        if not self.in_main and tag == 'div':
            if ('class', 'main') in attrs:
                self.in_main = True
        elif self.in_main:
            if tag == 'h2' and self.h2 is None:
                self.in_h2 = True
            elif tag == 'input' and ('name', 'studfee') in attrs:
                for (t, v) in attrs:
                    if t == 'value':
                        self.current_fee = v
            elif tag == 'textarea':
                if ('name', 'newshort') in attrs:
                    self.lasttag = 'newshort'
                if ('name', 'newnotes') in attrs:
                    self.lasttag = 'newnotes'

    def handle_endtag(self, tag):
        if self.in_main:
            if tag == 'textarea' and self.lasttag is not None:
                self.lasttag = None
            elif tag == 'h2':
                self.in_h2 = False

    def handle_data(self, data):
        if self.in_h2:
            self.page_title = data
        if self.lasttag == 'newshort':
            self.short_description = str(data)
        elif self.lasttag == 'newnotes':
            self.notes = str(data)

    def reset(self):
        super(DeckstationLoginParser, self).reset()
        self.in_main = False
        self.in_h2 = False
        self.page_title = ''
        self.current_fee = ''
        self.textarea_type = None
        self.short_description = ''
        self.notes = ''
        self.h2 = None


class PonyExtractor:
    GRUNDAUSBILDUNG = 0
    DRESSUR = 1
    SPRINGEN = 2
    MILITARY = 3
    WESTERN = 4
    RENNEN = 5
    FAHREN = 6
    CHARAKTER = 7
    KOMPLETT = 8
    TRAINING_CONSTANT_DICT = {'Dressur': DRESSUR,
                              'Springen': SPRINGEN,
                              'Military': MILITARY,
                              'Western': WESTERN,
                              'Rennen': RENNEN,
                              'Fahren': FAHREN,
                              # 'Charakter': CHARAKTER
                              }

    def __init__(self):
        self.parser = MyHTMLParser()
        self.beauty_parser = BeautyParser()
        self.deckstation_login_parser = DeckstationLoginParser()
        self.driver = None
        self.pony_image = None
        self.data = ''
        self.session = None
        self.post_login_url = 'https://noblehorsechampion.com/index.php'
        self.request_url_base = 'https://noblehorsechampion.com/inside/horse.php?id={}'
        self.organize_url_base = 'https://noblehorsechampion.com/inside/organizehorses.php?id={}'
        self.base_url = 'https://noblehorsechampion.com/inside/'
        self.train_post_url = 'https://noblehorsechampion.com/inside/inc/horses/training/training.php'
        self.deckstation_login_url = 'https://noblehorsechampion.com/inside/loginstud.php?id={}'
        self.deckstation_club_url = 'https://noblehorsechampion.com/inside/loginclubstud.php?id={}'
        self.beauty_url = 'https://noblehorsechampion.com/inside/loginbeauty.php'
        self.payload = {'email': '', 'password': '', 'login': ''}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'}
        self.telegram_id = ''
        self.bot_token = '1331285354:AAEbZPUpJ7X1xaR3YSujlSLNr4j1q_ORWHc'
        self.race_dict = {'Alle': 0,
                          'Trakehner': 1,
                          'Pura Raza Española': 2,
                          'Andalusier': 2,
                          'Holsteiner': 3,
                          'Englisches Vollblut': 4,
                          'Tinker': 5,
                          'American Paint Horse': 6,
                          'Araber': 7,
                          'Welsh Mountain Pony': 8,
                          'Isländer': 9,
                          'Friese': 10,
                          'Haflinger': 11,
                          'Appaloosa': 12,
                          'Marwari':13,
                          'Shire Horse':14}
        self.sort_by_dict = {'Neueste zuerst': 'firstnew',
                             'Jüngste zuerst': 'firstyoung',
                             'Älteste zuerst': 'firstold',
                             'Namen A-Z': 'firsta',
                             'Namen Z-A': 'firstz',
                             'Preis aufsteigend': 'firstminprize',
                             'Preis absteigend': 'firstmaxprize',
                             'Gesamtpotenzial': 'gp',
                             'Ausbildung': 'summaxausbildung',
                             'Gangarten': 'summaxgangarten',
                             'Dressur': 'summaxdressur',
                             'Springen': 'summaxspringen',
                             'Military': 'summaxmilitary',
                             'Western': 'summaxwestern',
                             'Rennen': 'summaxrennen',
                             'Fahren': 'summaxfahren',
                             'Gesundheit': 'sumhealth',
                             'Charakter': 'sumchar',
                             'Exterieur': 'sumext'}
        self.pony_id = 0
        self.cache_exists = False
        self.log = []
        self.last_login_time = None
        self.insidepage_length_threshold = 30000
        self.loginpage_length_threshold = 10000

        self.images = []
        self.ponies = []
        self.empty_img = Image.new('RGBA', (428, 251), (0, 0, 0, 0))

        self.has_box = None
        self.energy = None
        self.train_state = None

    def __del__(self):
        if self.session is not None:
            self.session.close()
        if self.driver is not None:
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            self.session.close()
        if self.driver is not None:
            self.driver.quit()

    def _login_if_required(self):
        # check whether cookie has expired
        if self.session is not None:
            cookie_age = datetime.now() - self.last_login_time
            if cookie_age.seconds // 60 >= 30:  # if minutes > 30 we get a new cookie. I could not find a way to get the actual expiration time, so I assume it is at least 30 minutes
                self.session.close()
                self.session = None
        if self.session is None:
            if len(self.payload['email']) == 0:
                try:
                    with open('login', 'r') as f:
                        self.payload['email'] = f.readline().strip()
                        self.payload['password'] = f.readline().strip()
                        tel_id = f.readline().strip()
                        self.telegram_id = tel_id
                except IOError:
                    self.log.append('Login at {} failed. Email/Password combination wrong?'.format(self.post_login_url))
                    return False
            self.session = requests.Session()
            self.session.max_redirects = 3
            # login
            try:
                r1 = self.session.get(self.post_login_url, headers=self.headers)
            except Exception:
                traceback.print_exc()
                self.log.append(
                    'Login at {} failed. Unexpected error. Exception was printed.'.format(self.post_login_url))
                return False
            if len(r1.text) < self.loginpage_length_threshold:
                self.log.append('Contacting login page at {} failed'.format(self.post_login_url))
                self.session.close()
                self.session = None
                return False
            post = self.session.post(self.post_login_url, data=self.payload, headers=self.headers)
            if len(post.text) < self.insidepage_length_threshold:
                self.log.append('Login at {} failed. Email/Password combination wrong?'.format(self.post_login_url))
                self.session.close()
                self.session = None
                return False

            self.last_login_time = datetime.now()
        return True

    def get_page_content(self, url):
        if not self._login_if_required():
            return False
        r1 = self.session.get(url, headers=self.headers)
        return r1.text

    def _login_in_browser(self):
        if self.driver is not None:
            return True
        if len(self.payload['email']) == 0:
            try:
                with open('login', 'r') as f:
                    self.payload['email'] = f.readline().strip()
                    self.payload['password'] = f.readline().strip()
                    tel_id = f.readline().strip()
                    self.telegram_id = tel_id
            except IOError:
                self.log.append('Login at {} failed. Email/Password combination wrong?'.format(self.post_login_url))
                return False
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        driver_path = Path('./chromedriver.exe').absolute()
        options = Options()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.driver = webdriver.Chrome(str(driver_path), chrome_options=chrome_options, options=options)
        # self.driver = webdriver.Chrome()
        self.driver.get(self.post_login_url)
        # assert "noblehorsechampion" in driver.title

        username = self.driver.find_element_by_name("email")
        username.clear()
        username.send_keys(self.payload['email'])

        password = self.driver.find_element_by_name("password")
        password.clear()
        password.send_keys(self.payload['password'])
        self.driver.find_element_by_name("login").click()

    def open_page_in_browser(self, url):
        if self._login_in_browser():
            self.driver.get(url)
        return self.driver.page_source

    def get_own_ponies(self, progress_window=None):
        def get_own_ponies_from_stables(html_text, prog_win=None):
            urls = []
            if not 'nostable.php?id=' in html_text:
                self.log.append(f'Could not find nostable link in landing page')
                return False, False
            url_begin = html_text.index('nostable.php?id=')
            url_text = html_text[url_begin: url_begin + 30]
            url_end = url_text.index('"')
            nostable_url = url_text[:url_end]
            urls.append(nostable_url)

            while 'stable.php?id=' in html_text:
                url_begin = html_text.index('stable.php?id=')
                url_text = html_text[url_begin: url_begin+30]
                url_end = url_text.index('"')
                stable_url = url_text[:url_end]
                if stable_url not in urls:
                    urls.append(stable_url)
                html_text = html_text[url_begin+url_end:]

            if prog_win is not None:
                prog_win.set_steps(len(urls)+1)

            horse_ids = []
            stable_names = []
            for stable_url in urls:
                if prog_win is not None:
                    prog_win.step(stable_url)
                r2 = self.session.get(self.base_url + stable_url)
                stable_text = r2.text
                if 'class="main"' in stable_text:
                    main_begin = stable_text.index('class="main"')
                else:
                    self.log.append(f'Could not find main div in stable {self.base_url + stable_url}')
                    return False, False
                if '<footer' in stable_text:
                    main_end = stable_text.index('<footer')
                else:
                    self.log.append(f'Could not find footer in stable {self.base_url + stable_url}')
                    return False, False
                stable_text = stable_text[main_begin : main_end]
                if '<h2 class="center_items">' in stable_text and '</h2>' in stable_text:
                    caption_start = stable_text.index('<h2 class="center_items">')
                    caption_end = stable_text.index('</h2>')
                    stable_name = stable_text[caption_start + 28: caption_end].strip()
                else:
                    stable_name = ''
                search_string = '"horse.php?id='
                while search_string in stable_text:
                    index = stable_text.index(search_string) + len(search_string)
                    id_string = ''
                    while stable_text[index].isnumeric():
                        id_string += stable_text[index]
                        index += 1
                    id = int(id_string)
                    if not id in horse_ids:
                        horse_ids.append(id)
                        stable_names.append(stable_name)
                    stable_text = stable_text[index:]

            if prog_win is not None:
                prog_win.step('Finished')
            return horse_ids, stable_names

        if not self._login_if_required():
            return False
        r1 = self.session.get(self.base_url, headers=self.headers)
        text = r1.text
        if len(text) < self.loginpage_length_threshold:
            self.log.append('Contacting start page at {} failed'.format(self.base_url))
            return False

        # Temporarily (or maybe permanently) switched to horse detection from stable page
        return get_own_ponies_from_stables(text, progress_window)

        search_string = 'organizehorses.php?id='
        if not search_string in text:
            self.log.append('Could not find organizehorses link in start page')
            return False
        index = text.index(search_string) + len(search_string)
        id_string = ''
        while text[index].isnumeric():
            id_string += text[index]
            index += 1
        organize_id = int(id_string)

        r2 = self.session.get(self.organize_url_base.format(organize_id), headers=self.headers)
        text = r2.text
        if len(text) < self.loginpage_length_threshold:
            self.log.append('Contacting organize page at {} failed'.format(self.organize_url_base.format(organize_id)))
            return False

        search_string = 'class="main"'
        if not search_string in text:
            self.log.append('Could not find main class in start page')
            return False
        text = text[text.index(search_string):]

        horse_ids = []
        search_string = '"horse.php?id='
        while search_string in text:
            index = text.index(search_string) + len(search_string)
            id_string = ''
            while text[index].isnumeric():
                id_string += text[index]
                index += 1
            id = int(id_string)
            if not id in horse_ids:
                horse_ids.append(id)
            text = text[index:]
        return horse_ids

    def browse_horses(self, type=0, race='Alle', sort_by='gp', pages=3, quick=False):
        if quick:
            self.images = []
            self.ponies = []
        if type == 1:
            url = self.base_url + 'stud.php'
        elif type == 0:
            url = self.base_url + 'horsetrade.php'
        elif type == 2:
            url = self.base_url + 'allhorses.php'
        else:
            self.log.append('Invalid type-argument for browse_horses() function')
            return False
        race_num = self.race_dict[race] if race in self.race_dict.keys() else 0
        if not self._login_if_required():
            return False
        form_data = {'rasse': race_num, 'filter': sort_by, 'submit': ''}
        if type != 1:
            form_data['geschlecht'] = 'gall'
        post = self.session.post(url, data=form_data, headers=self.headers)
        text = post.text
        if len(text) < self.insidepage_length_threshold:
            self.log.append('Posting to {} failed.'.format(url))
            return False

        page = 1
        horse_ids = []
        while page <= pages:
            if page > 1:
                r = self.session.get(url + '?page={}'.format(page), headers=self.headers)
                text = r.text
                if len(text) < self.insidepage_length_threshold:
                    self.log.append('Retrieving {} failed.'.format(url))
                    return False

            if quick:
                list_parser = ListParser()
                list_parser.feed(text)
                self.images.extend(list_parser.images)
                self.ponies.extend(list_parser.ponies)

            search_string = 'class="main"'
            if not search_string in text:
                self.log.append('Could not find main class in start page')
                return False
            text = text[text.index(search_string):]

            search_string = '"horse.php?id='
            while search_string in text:
                index = text.index(search_string) + len(search_string)
                id_string = ''
                while text[index].isnumeric():
                    id_string += text[index]
                    index += 1
                id = int(id_string)
                if not id in horse_ids:
                    horse_ids.append(id)
                text = text[index:]

            page += 1

        if quick:
            if len(self.ponies) > len(horse_ids):
                self.ponies = self.ponies[:len(horse_ids)]
                self.images = self.images[:len(horse_ids)]

        return horse_ids

    def _request_pony_file(self, pony_id, cached=True):
        # cache_path = Path('.cache/{}/'.format(pony_id))
        # cache_path.mkdir(parents=True, exist_ok=True)
        # write_file = Path('.cache/{}/ponyfile.html'.format(pony_id))
        # if cached:
        #     if len(self.data) > 0 and self.pony_id == pony_id:
        #         we still have the data stored
        # return True
        self.pony_id = pony_id
        # if write_file.exists():
        # we can load the file from disk
        # with open(write_file, 'r') as f:
        #     self.data = f.read()
        # return True
        if not self._login_if_required():
            return False
        request_url = self.request_url_base.format(pony_id)
        try:
            r = self.session.get(request_url, headers=self.headers)
        except requests.exceptions.TooManyRedirects:
            self.log.append('Retrieving pony page at {} failed. Too many redirects.'.format(request_url))
            # self.del_pony_cache(pony_id)
            return False
        except Exception:
            traceback.print_exc()
            self.log.append(
                'Retrieving pony page at {} failed. Unexpected error. Exception was printed.'.format(request_url))
            # self.del_pony_cache(pony_id)
            return False
        if len(r.text) < self.insidepage_length_threshold:
            self.log.append('Retrieving pony page at {} failed. Server reply too short.'.format(request_url))
            # self.del_pony_cache(pony_id)
            return False
        self.data = str(r.text)
        # get id of pony that was actually returned. If requested pony is foal that is still wih mother, a redirect would have happened to mother page.
        # then cache must not be stored. Otherwise cached values of pony will be wrong once it has its own box.
        search_string = 'horse.php?id='
        id_ind = r.url.index(search_string) + len(search_string)
        urllen = len(r.url)
        new_id = ''
        while id_ind < urllen and r.url[id_ind].isnumeric():
            new_id += r.url[id_ind]
            id_ind += 1
        # store to disk
        # with open(write_file, 'w', encoding='utf-8') as f:
        #     f.write(self.data)
        return int(new_id)

    def del_pony_cache(self, pony_id):
        cache_path = Path('.cache/{}/'.format(pony_id))
        shutil.rmtree(cache_path, ignore_errors=True)

    def del_pony_cache_all(self, exclude=None):
        cache_all_path = Path('.cache/')
        if exclude is None:
            shutil.rmtree(cache_all_path, ignore_errors=True)
        else:
            p = cache_all_path.glob('**/*')
            for pa in p:
                if pa.name not in exclude:
                    shutil.rmtree(pa, ignore_errors=True)

    def get_pony_info(self, pony_id, cached=True):
        if self.pony_id == 0:
            self.pony_id = pony_id
        Path('.cache/{}/'.format(pony_id)).mkdir(parents=True, exist_ok=True)
        write_file = Path('.cache/{}/ponydata.p'.format(pony_id))
        if cached:
            if write_file.exists():
                self.pony_id = pony_id
                # we can load the file from disk
                with open(write_file, 'rb') as f:
                    self.parser = pickle.load(f)
                    # When loading parser from disk, we need to null data, because we are not overwriting it
                    # Otherwise, wrong old data will be in data.
                    self.data = ''
                self.cache_exists = True
                return True
        new_id = self._request_pony_file(pony_id, cached=cached)
        if not new_id:
            self.cache_exists = False
            return False
        self.pony_id = pony_id
        self.parser = MyHTMLParser()
        self.parser.feed(self.data)
        self.parser.gesundheit_values = {k: self.parser.details_values[k] for k in self.parser.gesundheit_headings}
        self.parser.charakter_values = {k: self.parser.details_values[k] for k in self.parser.charakter_headings}
        self.parser.exterieur_values = {k: self.parser.details_values[k] for k in self.parser.exterieur_headings}
        if new_id == int(pony_id):
            # if the parser was not redirected to a different page. If it was, the info usually belongs to the
            # mother of the requested pony. We do not want to store that
            with open(write_file, 'wb') as f:
                pickle.dump(self.parser, f)
            self.cache_exists = True
        else:
            self.cache_exists = False
        return True

    def _write_cache(self, pony_id):
        write_file = Path('.cache/{}/ponydata.p'.format(pony_id))
        with open(write_file, 'wb') as f:
            pickle.dump(self.parser, f)
        self.cache_exists = True

    def request_pony_images(self, cached=True, urls=None, pony_id=None):
        if urls is not None:
            if pony_id is None:
                self.log.append('Image URLS were given but no corresponding pony id when calling request_pony_images')
                return False
            image_urls = urls
            pid = pony_id
        else:
            image_urls = self.parser.image_urls
            pid = self.pony_id
        Path('.cache/{}/'.format(pid)).mkdir(parents=True, exist_ok=True)
        write_file = Path('.cache/{}/{}_image.png'.format(pid, pid))
        if not (write_file.exists() and cached):
            if not self._login_if_required():
                return False
            for ind, url in enumerate(image_urls):
                full_url = self.base_url + url
                try:
                    ri = self.session.get(full_url, headers=self.headers)
                except requests.exceptions.TooManyRedirects:
                    self.log.append('Retrieving image at {} failed. Too many redirects.'.format(full_url))
                    continue
                except Exception:
                    traceback.print_exc()
                    self.log.append(
                        'Retrieving pony page at {} failed. Unexpected error. Exception was printed.'.format(full_url))
                    continue
                if 'DOCTYPE html' in ri.text or len(ri.text) < 100:
                    self.log.append(
                        'Retrieving image at {} failed. Image file too short or not an image.'.format(full_url))
                    # return False
                else:
                    with open('.cache/{}/img{:02d}.png'.format(pid, ind), 'wb') as out_file:
                        out_file.write(ri.content)
                del ri

        if write_file.exists():
            write_file.unlink()  # delete file so it is not in the mixture. In the end it is overwritten anyway
        imlist = sorted(Path('.cache/{}/'.format(pid)).glob('*.png'))
        if len(imlist) == 0:
            self.pony_image = self.empty_img
            return True
        last_im = None
        for im in imlist:
            try:
                this_im = Image.open(im).convert('RGBA')
            except:
                self.log.append('Loading image {} failed. Skipping.'.format(im))
                break
            if last_im is not None:
                x_dif = last_im.size[0] - this_im.size[0]
                y_dif = last_im.size[1] - this_im.size[1]
                if y_dif > 0:
                    this_im = add_margin(this_im, y_dif, 0, 0, 0, (0, 0, 0, 0))
                elif y_dif < 0:
                    last_im = add_margin(last_im, -y_dif, 0, 0, 0, (0, 0, 0, 0))
                if x_dif > 0:
                    this_im = add_margin(this_im, 0, x_dif, 0, 0, (0, 0, 0, 0))
                elif x_dif < 0:
                    last_im = add_margin(last_im, 0, -x_dif, 0, 0, (0, 0, 0, 0))
                last_im = Image.alpha_composite(last_im, this_im)
            else:
                last_im = this_im
        last_im = last_im.crop(last_im.getbbox())
        last_im.save(write_file)
        self.pony_image = last_im
        return True

    def export_data(self, file_path):
        all_dict = {**self.parser.facts_values, **self.parser.details_values, **self.parser.training_max,
                    **self.parser.ausbildung_max, **self.parser.gangarten_max, **self.parser.dressur_max,
                    **self.parser.springen_max,
                    **self.parser.military_max, **self.parser.western_max, **self.parser.rennen_max,
                    **self.parser.fahren_max}
        csv_columns = all_dict.keys()
        dict_data = [all_dict]
        try:
            with open(file_path, 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                for data in dict_data:
                    writer.writerow(data)
        except IOError:
            print("I/O error")

    def get_pony_quality(self):
        if self.parser is not None:
            try:
                gesundheit = (self.parser.details_values['Gesundheit'] - 400) / 200
                charakter = self.parser.details_values['Charakter'] / 1200
                exterieur = self.parser.details_values['Exterieur'] / 800
                ausbildung = self.parser.training_max['Ausbildung'] / 2200
                gangarten = self.parser.training_max['Gangarten'] / 3100
                dressur = self.parser.training_max['Dressur'] / 3300
                springen = self.parser.training_max['Springen'] / 2100
                military = self.parser.training_max['Military'] / 2200
                western = self.parser.training_max['Western'] / 1800
                rennen = self.parser.training_max['Rennen'] / 1300
                fahren = self.parser.training_max['Fahren'] / 1600
            except:
                return 0

            gesundheit_weight = 0.5
            training = (ausbildung + gangarten + dressur + springen + military + western + rennen + fahren) / 8
            quality = (training + charakter + exterieur + gesundheit_weight * gesundheit) / (3 + gesundheit_weight)

            return quality

    def print_pony_info(self):
        if self.parser is not None:
            print(self.parser.name)
            print(self.parser.image_urls)
            print(self.parser.facts_values)
            print(self.parser.details_values)
            print(self.parser.training_values)
            print(self.parser.training_max)
            print(self.parser.ausbildung_values)
            print(self.parser.ausbildung_max)
            print(self.parser.gangarten_values)
            print(self.parser.gangarten_max)
            print(self.parser.dressur_values)
            print(self.parser.dressur_max)
            print(self.parser.springen_values)
            print(self.parser.springen_max)
            print(self.parser.military_values)
            print(self.parser.military_max)
            print(self.parser.western_values)
            print(self.parser.western_max)
            print(self.parser.rennen_values)
            print(self.parser.rennen_max)
            print(self.parser.fahren_values)
            print(self.parser.fahren_max)

    def telegram_bot_sendtext(self, bot_message):
        if len(self.telegram_id) > 0:
            send_text = 'https://api.telegram.org/bot' + self.bot_token + '/sendMessage?chat_id=' + self.telegram_id + '&parse_mode=Markdown&text=' + bot_message

            response = requests.get(send_text)
            resp = response.json()
            self.log.append(resp)
            return resp
        else:
            resp = 'No telegram id found. Message was not sent'
            self.log.append(resp)
            return 'No telegram id found. Message was not sent'

    def train_pony(self, pony_id, disciplines=None, refresh_state_only=False):
        if disciplines is None:
            disciplines = [PonyExtractor.GRUNDAUSBILDUNG]  # default argument
        if not refresh_state_only:
            if not self.get_pony_info(pony_id, cached=False):
                return False
        years = int(self.parser.facts_values['Alter'].split('Jahre')[0].strip()) if 'Jahre' in self.parser.facts_values[
            'Alter'] else 0
        # Check whether charakter training is in progress
        charakter_training_in_progress = any(x > 0 for x in self.parser.charakter_training_values.values())
        if years >= 3:
            if PonyExtractor.KOMPLETT in disciplines:
                all_dict_max = {**self.parser.ausbildung_max, **self.parser.gangarten_max, **self.parser.dressur_max,
                                **self.parser.springen_max,
                                **self.parser.military_max, **self.parser.western_max, **self.parser.rennen_max,
                                **self.parser.fahren_max, **self.parser.charakter_training_max}
                all_dict_values = {**self.parser.ausbildung_values, **self.parser.gangarten_values,
                                   **self.parser.dressur_values, **self.parser.springen_values,
                                   **self.parser.military_values, **self.parser.western_values,
                                   **self.parser.rennen_values, **self.parser.fahren_values,
                                   **self.parser.charakter_training_values}
                all_headings = self.parser.ausbildung_headings[1:] + self.parser.gangarten_headings[
                                                                     1:] + self.parser.dressur_headings[
                                                                           1:] + self.parser.springen_headings[1:] + \
                               self.parser.military_headings[1:] + self.parser.western_headings[
                                                                   1:] + self.parser.rennen_headings[
                                                                         1:] + self.parser.fahren_headings[
                                                                               1:] + self.parser.charakter_training_headings
                all_codes = self.parser.ausbildung_codes + self.parser.gangarten_codes + self.parser.dressur_codes + self.parser.springen_codes + \
                            self.parser.military_codes + self.parser.western_codes + self.parser.rennen_codes + self.parser.fahren_codes + self.parser.charakter_training_codes
            else:
                all_dict_max = {}
                all_dict_values = {}
                all_headings = []
                all_codes = []

                if PonyExtractor.GRUNDAUSBILDUNG in disciplines:
                    all_dict_max = {**self.parser.ausbildung_max, **self.parser.gangarten_max}
                    all_dict_values = {**self.parser.ausbildung_values, **self.parser.gangarten_values}
                    all_headings = self.parser.ausbildung_headings[1:] + self.parser.gangarten_headings[1:]
                    all_codes = self.parser.ausbildung_codes + self.parser.gangarten_codes

                if PonyExtractor.DRESSUR in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.dressur_max}
                    all_dict_values = {**all_dict_values, **self.parser.dressur_values}
                    all_headings = all_headings + self.parser.dressur_headings[1:]
                    all_codes = all_codes + self.parser.dressur_codes

                if PonyExtractor.SPRINGEN in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.springen_max}
                    all_dict_values = {**all_dict_values, **self.parser.springen_values}
                    all_headings = all_headings + self.parser.springen_headings[1:]
                    all_codes = all_codes + self.parser.springen_codes

                if PonyExtractor.MILITARY in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.military_max}
                    all_dict_values = {**all_dict_values, **self.parser.military_values}
                    all_headings = all_headings + self.parser.military_headings[1:]
                    all_codes = all_codes + self.parser.military_codes

                if PonyExtractor.WESTERN in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.western_max}
                    all_dict_values = {**all_dict_values, **self.parser.western_values}
                    all_headings = all_headings + self.parser.western_headings[1:]
                    all_codes = all_codes + self.parser.western_codes

                if PonyExtractor.RENNEN in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.rennen_max}
                    all_dict_values = {**all_dict_values, **self.parser.rennen_values}
                    all_headings = all_headings + self.parser.rennen_headings[1:]
                    all_codes = all_codes + self.parser.rennen_codes

                if PonyExtractor.FAHREN in disciplines:
                    all_dict_max = {**all_dict_max, **self.parser.fahren_max}
                    all_dict_values = {**all_dict_values, **self.parser.fahren_values}
                    all_headings = all_headings + self.parser.fahren_headings[1:]
                    all_codes = all_codes + self.parser.fahren_codes

                if charakter_training_in_progress:
                    all_dict_max = {**all_dict_max, **self.parser.charakter_training_max}
                    all_dict_values = {**all_dict_values, **self.parser.charakter_training_values}
                    all_headings = all_headings + self.parser.charakter_training_headings
                    all_codes = all_codes + self.parser.charakter_training_codes

        else:
            all_dict_max = self.parser.fohlenerziehung_max
            all_dict_values = self.parser.fohlenerziehung_values
            all_headings = self.parser.fohlenerziehung_headings
            all_codes = self.parser.fohlenerziehung_codes

            if PonyExtractor.GRUNDAUSBILDUNG in disciplines or PonyExtractor.KOMPLETT in disciplines:
                all_dict_max = {**self.parser.fohlenerziehung_max, **self.parser.ausbildung_max,
                                **self.parser.gangarten_max}
                all_dict_values = {**self.parser.fohlenerziehung_values, **self.parser.ausbildung_values,
                                   **self.parser.gangarten_values}
                all_headings = self.parser.fohlenerziehung_headings + self.parser.ausbildung_headings[
                                                                      1:] + self.parser.gangarten_headings[1:]
                all_codes = self.parser.fohlenerziehung_codes + self.parser.ausbildung_codes + self.parser.gangarten_codes
        energy = self.parser.energy if not refresh_state_only else 0
        max_sum = sum(all_dict_max.values()) if not charakter_training_in_progress else 120
        val_sum = min(max_sum, sum(all_dict_values.values()) + energy) if not charakter_training_in_progress else min(max_sum, sum(self.parser.charakter_training_values.values()) + energy)
        if max_sum == 0:
            self.parser.train_state = -1
        else:
            self.parser.train_state = val_sum/max_sum if not charakter_training_in_progress else val_sum/max_sum + 1
        ind = 0
        train_payload = {'id': pony_id, 'trainwert': 0}
        if not self.parser.has_box:
            self.log.append('Pony {} cannot be trained because it does not have a box'.format(pony_id))
            energy = 0
        while energy > 0:
            if ind < len(all_headings):
                heading = all_headings[ind]
                if heading in all_dict_max.keys():
                    max = all_dict_max[heading]
                    val = all_dict_values[heading]
                    if max > val:
                        code = all_codes[ind]
                        train_payload = {'id': pony_id, 'trainwert': code}
                        try:
                            post = self.session.post(self.train_post_url, data=train_payload, headers=self.headers)
                        except:
                            traceback.print_exc()
                            self.log.append('Training failed. Unexpected error. Exception was printed.')
                            return False
                        all_dict_values[heading] += 1
                        energy -= 1
                    else:
                        ind += 1  # max = val -> next attribute
                else:
                    ind += 1  # heading not in dict (hopefully this is because heading is part of Fohlenerziehung or Charakter-Training)
            else:
                self.log.append('Pony {} is fully trained'.format(pony_id))
                energy = 0
        if train_payload['trainwert'] in self.parser.charakter_training_codes:
            self.log.append('Pony {} is doing charakter training'.format(pony_id))
        # write cache to store updated train state
        self._write_cache(pony_id)
        return True

    def care_pony(self, pony_id):
        if not self.get_pony_info(pony_id, cached=False):
            return False
        for (k, v) in self.parser.care_values.items():
            if v < 99:
                query_param = self.parser.care_query_params[k]
                query_page = self.parser.care_query_pages[k]
                if query_param == 'food':
                    query_numbers = [50, 30, 20]
                else:
                    query_numbers = [100]
                for qnum in query_numbers:
                    query_dict = {'id': pony_id, query_param: qnum}
                    resp = self.session.get(self.base_url + 'inc/horses/care_php/{}.php'.format(query_page),
                                            params=query_dict, headers=self.headers)
        return True

    def login_deckstation(self, pony_id, fee):
        if not self._login_if_required():
            return False
        if not self.get_pony_info(pony_id):
            return False
        years = int(self.parser.facts_values['Alter'].split('Jahre')[0].strip()) if 'Jahre' in self.parser.facts_values[
            'Alter'] else 0
        if years > 25:
            self.log.append('Pony {} is older than 25 years. Deckstation login no allowed.'.format(pony_id))
            return True
        deckstation_login_payload = {'studfee': fee, 'newshort': '', 'newnotes': ''}
        url = self.deckstation_login_url.format(pony_id)
        try:
            r = self.session.get(url, headers=self.headers)
        except requests.exceptions.TooManyRedirects:
            self.log.append('Retrieving deckstation login page at {} failed. Too many redirects.'.format(url))
            return False
        except Exception:
            traceback.print_exc()
            self.log.append(
                'Retrieving deckstation login page at {} failed. Unexpected error. Exception was printed.'.format(url))
            return False
        self.deckstation_login_parser.reset()
        self.deckstation_login_parser.feed(r.text)
        lowertitle = self.deckstation_login_parser.page_title.lower()
        if 'deckstation' in lowertitle:  # If deckstation login is not possible, get redirects to pony page. So we check whether Deckstation is in Page title
            # if int(pony_id) == 161516:
            #     print('{}: current fee {}, new fee {}, lowertitle {}, short_description {}, notes {}'.format(pony_id,
            #                                                               self.deckstation_login_parser.current_fee,
            #                                                               fee, lowertitle, self.deckstation_login_parser.short_description,
            #                                                                                                   self.deckstation_login_parser.notes))
            if len(self.deckstation_login_parser.current_fee) > 0 and int(
                    self.deckstation_login_parser.current_fee) == int(fee):
                return True
            deckstation_login_payload['newshort'] = self.deckstation_login_parser.short_description
            deckstation_login_payload['newnotes'] = self.deckstation_login_parser.notes
            if 'verwalten' in lowertitle:
                deckstation_login_payload['changestudfee'] = ''  # Stud fee change
            else:
                # check if pony is already in club deckstation, abort if true
                club_url = self.deckstation_club_url.format(pony_id)
                try:
                    r_club = self.session.get(club_url, headers=self.headers)
                except requests.exceptions.TooManyRedirects:
                    self.log.append(
                        'Retrieving club deckstation login page at {} failed. Too many redirects.'.format(club_url))
                    return False
                except Exception:
                    traceback.print_exc()
                    self.log.append(
                        'Retrieving club deckstation login page at {} failed. Unexpected error. Exception was printed.'.format(
                            club_url))
                    return False
                self.deckstation_login_parser.reset()
                self.deckstation_login_parser.feed(r_club.text)
                lowertitle = self.deckstation_login_parser.page_title.lower()
                if 'verwalten' in lowertitle:
                    # Pony is already registered in club deckstation
                    return True
                deckstation_login_payload['checkin'] = ''  # Stud fee new
            try:
                pos = self.session.post(url, data=deckstation_login_payload, headers=self.headers)
            except requests.exceptions.TooManyRedirects:
                self.log.append('Deckstation login failed for {}. Too many redirects.'.format(url))
                return False
            except:
                traceback.print_exc()
                self.log.append('Deckstation login failed. Unexpected error. Exception was printed.')
                return False
            # if int(pony_id) == 161516:
        #         print('Just posted to {} with payload {}'.format(url, deckstation_login_payload))
        # print('Trying to load Deckstation login at {}, got redirected to a page with title {}.'.format(url, lowertitle))
        return True

    def login_beauty(self, pony_id):
        if not self._login_if_required():
            return False
        if not self.get_pony_info(pony_id):
            return False
        years = int(self.parser.facts_values['Alter'].split('Jahre')[0].strip()) if 'Jahre' in self.parser.facts_values[
            'Alter'] else 0
        if years > 25:
            self.log.append('Pony {} is older than 25 years. Beauty registration no allowed.'.format(pony_id))
            print('Pony {} is older than 25 years. Beauty registration no allowed.'.format(pony_id))
            return True
        query_dict = {'id': pony_id}
        try:
            r = self.session.get(self.beauty_url, params=query_dict, headers=self.headers)
        except requests.exceptions.TooManyRedirects:
            self.log.append('Retrieving beauty page at {} failed. Too many redirects.'.format(self.beauty_url))
            self.del_pony_cache(pony_id)
            return False
        except Exception:
            traceback.print_exc()
            self.log.append(
                'Retrieving beauty page at {} failed. Unexpected error. Exception was printed.'.format(self.beauty_url))
            self.del_pony_cache(pony_id)
            return False
        self.beauty_parser = BeautyParser()
        self.beauty_parser.feed(r.text)
        # print('competition found', self.beauty_parser.competition_found)
        # print('value', self.beauty_parser.value)
        if self.beauty_parser.competition_found:
            formdata = {'participate[{}]'.format(self.beauty_parser.value): ''}
            try:
                pos = self.session.post(self.beauty_url, params=query_dict, data=formdata, headers=self.headers)
            except requests.exceptions.TooManyRedirects:
                self.log.append(
                    'Registering for beauty contest failed for {}. Too many redirects.'.format(self.beauty_url))
                self.del_pony_cache(pony_id)
                return False
            except:
                traceback.print_exc()
                self.log.append('Beauty registration failed. Unexpected error. Exception was printed.')
                return False
        else:
            self.log.append('No available competition found for pony {}'.format(pony_id))
        return True


if __name__ == '__main__':
    PONY_ID = 106161
    PONY_ID = 0

    pony_extractor = PonyExtractor()

    if pony_extractor.get_pony_info(PONY_ID):
        pony_extractor.print_pony_info()
        if pony_extractor.request_pony_images():
            # pony_extractor.export_data('test.csv')
            pass
        else:
            print(pony_extractor.log[-1])
    else:
        print(pony_extractor.log[-1])
