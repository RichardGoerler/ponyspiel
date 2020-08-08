import requests
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
import pickle
import csv
import shutil
import traceback

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
        self.block_types = ['none', 'name', 'facts', 'details', 'training', 'ausbildung', 'gangarten', 'dressur', 'springen', 'military', 'western', 'rennen', 'fahren', 'pedigree', 'alert']
        self.training_block_types = ['training', 'ausbildung', 'gangarten', 'dressur', 'springen', 'military', 'western', 'rennen', 'fahren']
        self.block = 'none'
        self.tag_counter = 0

        # variables needed for reading data
        self.next_data_type = ''
        self.span_id = ''
        self.span_value_entered = False

        # Query containers
        self.details_headings = ['Gesundheit', 'Zufriedenheit', 'Robustheit', 'Hufe', 'Zähne', 'Impfungen', 'Wurmkur',
                                 'Charakter', 'Vertrauen', 'Intelligenz', 'Mut', 'Aufmerksamkeit', 'Gehorsam', 'Gelassenheit', 'Nervenstärke', 'Siegeswille', 'Motivation', 'Gutmütigkeit', 'Genauigkeit', 'Auffassungsvermögen',
                                 'Exterieur', 'Trainingszustand', 'Bemuskelung', 'Bewegungen', 'Haltung', 'Ausdruck', 'Kopf', 'Halsansatz', 'Rückenlinie', 'Beinstellung']
        self.gesundheit_headings = self.details_headings[self.details_headings.index('Gesundheit'):self.details_headings.index('Charakter')]
        self.charakter_headings = self.details_headings[self.details_headings.index('Charakter'):self.details_headings.index('Exterieur')]
        self.exterieur_headings = self.details_headings[self.details_headings.index('Exterieur'):]
        self.training_headings = ['Gesamtpotenzial', 'Ausbildung', 'Gangarten', 'Dressur', 'Springen', 'Military', 'Western', 'Rennen', 'Fahren']
        self.facts_headings = ['Rufname', 'Besitzer', 'Züchter', 'Rasse', 'Alter', 'Geburtstag', 'Stockmaß', 'Erwartetes Stockmaß', 'Fellfarbe']
                                        # additionaly, there are 'Geschlecht' and 'Fohlen' which are extracted differently (handle_starttag)
        self.ausbildung_headings = ['Ausbildung', 'Stärke', 'Trittsicherheit', 'Ausdauer', 'Geschwindigkeit', 'Beschleunigung', 'Wendigkeit', 'Sprungkraft', 'taktrein', 'Geschicklichkeit',
                                    'Sand', 'Gras', 'Erde', 'Schnee', 'Lehm', 'Späne',
                                    'Halle', 'Arena', 'draußen', 'sehr weich', 'weich', 'mittel', 'hart', 'sehr hart']
        self.gangarten_headings = ['Gangarten', 'Schritt', 'Trab', 'leichter Galopp', 'Galopp', 'Rückwärts richten', 'Slow Gait',
                                   'Tölt', 'Paso', 'Rack', 'Walk', 'Marcha Batida', 'Jog', 'Pass', 'Foxtrott', 'Marcha Picada', 'Rennpass', 'Single Foot', 'Saddle Gait',
                                   'Trailwalk', 'Slow Canter', 'Lope', 'Running Walk', 'Flatfoot Walk', 'Sobreandando', 'Paso Llano', 'Termino', 'Classic Fino', 'Paso Corto', 'Paso Largo', 'Trocha', 'Trote Y Galope']
        self.dressur_headings = ['Dressur', 'starker Schritt', 'starker Trab', 'starker Galopp', 'versammelter Schritt', 'versammelter Trab', 'versammelter Galopp',
                                'Galoppwechsel', 'Außengalopp', 'Hinterhandwendung', 'Kurzkehrtwendung', 'Vorhandwendung', 'Passage', 'Piaffe', 'Pirouette', 'Schultervor', 'Renvers', 'Traversale', 'Schaukel',
                                'Traversalverschiebungen', 'Kehrtwendevorhand', 'Kehrtwendehinterhand', 'halbe Pirouette',
                                'Spanischer Tritt', 'Ballotade', 'Courbette', 'Croupade', 'Kapriole', 'Levade', 'Pesade', 'Mezair', 'Terre à Terre', 'Spanischer Trab', 'Sarabande']
        self.springen_headings = ['Springen', 'Steilsprung', 'Wassergraben', '2er Kombination', '3er Kombination', 'Mauer', 'Eisenbahnschranken', 'Gatter', 'Rick', 'Kreuz', 'Planke', 'Palisade',
                                  'Oxer', 'Triplebarre', 'Überbautes Wasser', 'Buschoxer', 'Birkenoxer', 'Doppelrick',
                                  'Pulvermanns Grab', 'Irische Wälle', 'Holsteiner Wegesprünge', 'Wall']
        self.military_headings = ['Military', 'Bank', 'Hecke', 'Coffin', 'Eulenloch', 'Normandiebank', 'Schmales Hindernis', 'Sunkenroad',
                                  'Hogback', 'Wasser', 'Billiard', 'Graben', 'Schweinerücken', 'Bürste', 'Ecke', 'Trakehnergraben',
                                  'Wassereinsprung', 'Wasseraussprung', 'Tiefsprung', 'Tisch', 'Strohsprung', 'Bullfinish', '4 Phasen Gelände']
        self.western_headings = ['Western', 'Sliding Stop', 'Spin', 'Back Up', 'Tempowechsel', 'Cutting', 'Pole Bending',
                                 'Barrel Race', 'Roll Back', 'Trail', 'Roping', 'Horsemanship', 'Showmanship at Halter',
                                 'Turn', 'Circles', 'Rundown', 'Railwork', 'Sidepass', 'Sidewalk']
        self.rennen_headings = ['Rennen', 'Hürdenrennen', 'Trabrennen', 'Galopprennen', 'Distanzrennen', 'Jagdrennen', 'Töltrennen', 'Passrennen',
                                'Endspurt', 'Start', 'Fliegender Start', 'Autostart', 'Bänderstart', 'Startbox']
        self.fahren_headings = ['Fahren', 'Dressurfahren', 'Geländefahren', 'Hindernisfahren', 'Kegelfahren',
                                'Einspänner', 'Zweispänner', 'Tandem', 'Dreispänner', 'Random', 'Einhorn', 'Verkehrtes Einhorn', 'Quadriga', 'Vierspänner', 'Fünfspänner', 'Sechsspänner', 'Wildgang']

        # result containers
        self.name = ''
        self.facts_values = dict()
        self.details_values = dict()
        self.gesundheit_values, self.charakter_values, self.exterieur_values = dict(), dict(), dict()
        self.training_values = dict()
        self.ausbildung_values, self.gangarten_values, self.dressur_values, self.springen_values = dict(), dict(), dict(), dict()
        self.military_values, self.western_values, self.rennen_values, self.fahren_values = dict(), dict(), dict(), dict()
        self.training_max = dict()
        self.ausbildung_max, self.gangarten_max, self.dressur_max, self.springen_max = dict(), dict(), dict(), dict()
        self.military_max, self.western_max, self.rennen_max, self.fahren_max = dict(), dict(), dict(), dict()
        self.image_urls = []
        self.ancestors = []
        self.pedigree_id_temp = 0
        self.pedigree_unknown_counter = 0
        self.alert_type = ''

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
                        date = data_content[1][data_content[1].index('(')+1:data_content[1].index(')')]
                        self.facts_values['Fohlen'] = date
                    elif data_content[1].strip() == 'Stute':
                        self.facts_values['Geschlecht'] = 'Stute'
                    elif data_content[1].strip() == 'Hengst':
                        self.facts_values['Geschlecht'] = 'Hengst'
        if not self.is_in_block() and tag == 'div' and len(attrs) > 0:
            if len(self.name) == 0 and attrs[0] == ('class', 'main'):
                # Start des Seiteninhalts. Das nächste Stück Text (h2-Überschrift) beinhaltet den Namen des Pferdes
                self.enter_block('name')

            if ('role', 'alert') in attrs:
                # grey alert area above name. Includes market price etc.
                self.enter_block('alert')
                self.alert_type = ''

            elif attrs[0] == ('id', 'facts'):
                self.enter_block('facts')

            elif attrs[0] == ('id', 'health'):
                self.enter_block('details')

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

            elif attrs[0] == ('id', 'pedigree'):
                self.enter_block('pedigree')

        # ============================ Incrementing tag counter ================================================================
        elif self.is_in_block():
            if tag == 'div':
                self.tag_counter += 1

        # ============================ Block specifics - only executed if in block =============================================
            if self.block in self.training_block_types:
                if tag == 'span' and len(attrs) > 0:
                    self.span_id = attrs[0][1]

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

    def handle_endtag(self, tag):
        # =========================== Decrementing tag counter and exiting block ================================================
        if self.is_in_block():
            if tag == 'div':
                self.tag_counter -= 1
                if self.tag_counter == 0:
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
                self.in_name = False
                self.tag_counter = 0

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
            if 'deckstation' in content.lower():
                self.alert_type = 'deckstation'
            elif 'verkauf' in content.lower():
                self.alert_type = 'verkauf'
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
            block_headings = [self.training_headings, self.ausbildung_headings, self.gangarten_headings, self.dressur_headings, self.springen_headings,
                              self.military_headings, self.western_headings, self.rennen_headings, self.fahren_headings][list_index]
            block_values = [self.training_values, self.ausbildung_values, self.gangarten_values, self.dressur_values, self.springen_values,
                            self.military_values, self.western_values, self.rennen_values, self.fahren_values][list_index]
            block_max = [self.training_max, self.ausbildung_max, self.gangarten_max, self.dressur_max, self.springen_max,
                         self.military_max, self.western_max, self.rennen_max, self.fahren_max][list_index]
            # if len(self.next_data_type) == 0 and content in block_headings:
            if content in block_headings:
                self.next_data_type = content
            elif len(self.next_data_type) > 0 and len(content) > 0:
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
                    elif len(content) > 1 and content.startswith('/'):
                        # We are not in a span -> normally there is just a dash, which we don't want to store
                        # but sometimes they failed to put the second value in a span and it just follows the dash -> then we need to extract it
                        content_stripped = content[1:].strip()
                        try:
                            content_stripped = int(content_stripped)
                        except:
                            pass
                        block_max[self.next_data_type] = content_stripped

        if self.block == 'pedigree':
            if content.lower() == 'unbekannt':
                self.pedigree_unknown_counter += 1


class PonyExtractor:
    def __init__(self):
        self.parser = MyHTMLParser()
        self.pony_image = None
        self.data = ''
        self.session = None
        self.post_login_url = 'https://noblehorsechampion.com/index.php'
        self.request_url_base = 'https://noblehorsechampion.com/inside/horse.php?id={}'
        self.organize_url_base = 'https://noblehorsechampion.com/inside/organizehorses.php?id={}'
        self.base_url = 'https://noblehorsechampion.com/inside/'
        self.payload = {'email': '', 'password': '', 'login': ''}
        self.race_dict = {'Alle': 0,
                    'Trakehner': 1,
                     'Andalusier': 2,
                     'Holsteiner': 3,
                     'Englisches Vollblut': 4,
                     'Tinker': 5,
                     'American Paint Horse': 6,
                     'Araber': 7,
                     'Welsh Mountain Pony': 8,
                     'Isländer': 9,
                     'Friese': 10}
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
        self.log = []
        self.insidepage_length_threshold = 40000
        self.loginpage_length_threshold = 10000

    def __del__(self):
        if self.session is not None:
            self.session.close()

    def _login_if_required(self):
        if self.session is None:
            if len(self.payload['email']) == 0:
                try:
                    with open('login', 'r') as f:
                        self.payload['email'] = f.readline().strip()
                        self.payload['password'] = f.readline().strip()
                except IOError:
                    self.log.append('Login at {} failed. Email/Password combination wrong?'.format(self.post_login_url))
                    return False
            self.session = requests.Session()
            self.session.max_redirects = 3
            # login
            try:
                r1 = self.session.get(self.post_login_url)
            except Exception:
                traceback.print_exc()
                self.log.append('Login at {} failed. Unexpected error. Exception was printed.'.format(self.post_login_url))
                return False
            if len(r1.text) < self.loginpage_length_threshold:
                self.log.append('Contacting login page at {} failed'.format(self.post_login_url))
                self.session.close()
                self.session = None
                return False
            post = self.session.post(self.post_login_url, data=self.payload)
            if len(post.text) < self.insidepage_length_threshold:
                self.log.append('Login at {} failed. Email/Password combination wrong?'.format(self.post_login_url))
                self.session.close()
                self.session = None
                return False
        return True

    def get_own_ponies(self):
        if not self._login_if_required():
            return False
        r1 = self.session.get(self.base_url)
        text = r1.text
        if len(text) < self.loginpage_length_threshold:
            self.log.append('Contacting start page at {} failed'.format(self.base_url))
            return False
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

        r2 = self.session.get(self.organize_url_base.format(organize_id))
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


    def browse_horses(self, deckstation=False, race='Alle', sort_by='gp', pages=3):
        if deckstation:
            url = self.base_url + 'stud.php'
        else:
            url = self.base_url + 'horsetrade.php'
        race_num = self.race_dict[race] if race in self.race_dict.keys() else 0
        if not self._login_if_required():
            return False
        form_data = {'rasse': race_num, 'filter': sort_by, 'submit': ''}
        if not deckstation:
            form_data['geschlecht'] = 'gall'
        post = self.session.post(url, data=form_data)
        text = post.text
        if len(text) < self.insidepage_length_threshold:
            self.log.append('Posting to {} failed.'.format(url))
            return False

        page = 1
        horse_ids = []
        while page <= pages:
            if page > 1:
                r = self.session.get(url + '?page={}'.format(page))
                text = r.text
                if len(text) < self.insidepage_length_threshold:
                    self.log.append('Retrieving {} failed.'.format(url))
                    return False

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

        return horse_ids


    def _request_pony_file(self, pony_id, cached=True):
        cache_path = Path('.cache/{}/'.format(pony_id))
        cache_path.mkdir(parents=True, exist_ok=True)
        write_file = Path('.cache/{}/ponyfile.html'.format(pony_id))
        if cached:
            if len(self.data) > 0 and self.pony_id == pony_id:
                # we still have the data stored
                return True
            self.pony_id = pony_id
            if write_file.exists():
                # we can load the file from disk
                with open(write_file, 'r') as f:
                    self.data = f.read()
                return True
        if not self._login_if_required():
            return False
        request_url = self.request_url_base.format(pony_id)
        try:
            r = self.session.get(request_url)
        except requests.exceptions.TooManyRedirects:
            self.log.append('Retrieving pony page at {} failed. Too many redirects.'.format(request_url))
            self.del_pony_cache(pony_id)
            return False
        except Exception:
            traceback.print_exc()
            self.log.append('Retrieving pony page at {} failed. Unexpected error. Exception was printed.'.format(request_url))
            self.del_pony_cache(pony_id)
            return False
        if len(r.text) < self.insidepage_length_threshold:
            self.log.append('Retrieving pony page at {} failed. Server reply too short.'.format(request_url))
            self.del_pony_cache(pony_id)
            return False
        self.data = str(r.text)
        # store to disk
        with open(write_file, 'w', encoding='utf-8') as f:
            f.write(self.data)
        return True

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
                    shutil.rmtree(pa)

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
                return True
        if not self._request_pony_file(pony_id):
            return False
        self.pony_id = pony_id
        self.parser = MyHTMLParser()
        self.parser.feed(self.data)
        self.parser.gesundheit_values = {k: self.parser.details_values[k] for k in self.parser.gesundheit_headings}
        self.parser.charakter_values = {k: self.parser.details_values[k] for k in self.parser.charakter_headings}
        self.parser.exterieur_values = {k: self.parser.details_values[k] for k in self.parser.exterieur_headings}
        with open(write_file, 'wb') as f:
            pickle.dump(self.parser, f)
        return True

    def request_pony_images(self, cached=True):
        Path('.cache/{}/'.format(self.pony_id)).mkdir(parents=True, exist_ok=True)
        write_file = Path('.cache/{}/{}_image.png'.format(self.pony_id, self.pony_id))
        if not (write_file.exists() and cached):
            if not self._login_if_required():
                return False
            for ind, url in enumerate(self.parser.image_urls):
                full_url = self.base_url + url
                try:
                    ri = self.session.get(full_url)
                except requests.exceptions.TooManyRedirects:
                    self.log.append('Retrieving image at {} failed. Too many redirects.'.format(full_url))
                    continue
                except Exception:
                    traceback.print_exc()
                    self.log.append('Retrieving pony page at {} failed. Unexpected error. Exception was printed.'.format(full_url))
                    continue
                if 'DOCTYPE html' in ri.text or len(ri.text) < 100:
                    self.log.append('Retrieving image at {} failed. Image file too short or not an image.'.format(full_url))
                    # return False
                else:
                    with open('.cache/{}/img{:02d}.png'.format(self.pony_id, ind), 'wb') as out_file:
                        out_file.write(ri.content)
                del ri

        if write_file.exists():
            write_file.unlink()   # delete file so it is not in the mixture. In the end it is overwritten anyway
        imlist = sorted(Path('.cache/{}/'.format(self.pony_id)).glob('*.png'))
        if len(imlist) == 0:
            return False
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
                    this_im = add_margin(this_im, y_dif, 0, 0, 0, (0,0,0,0))
                elif y_dif < 0:
                    last_im = add_margin(last_im, -y_dif, 0, 0, 0, (0,0,0,0))
                if x_dif > 0:
                    this_im = add_margin(this_im, 0, x_dif, 0, 0, (0,0,0,0))
                elif x_dif < 0:
                    last_im = add_margin(last_im, 0, -x_dif, 0, 0, (0,0,0,0))
                last_im = Image.alpha_composite(last_im, this_im)
            else:
                last_im = this_im
        last_im = last_im.crop(last_im.getbbox())
        last_im.save(write_file)
        self.pony_image = last_im
        return True

    def export_data(self, file_path):
        all_dict = {**self.parser.facts_values, **self.parser.details_values, **self.parser.training_max,
                    **self.parser.ausbildung_max, **self.parser.gangarten_max, **self.parser.dressur_max, **self.parser.springen_max,
                    **self.parser.military_max, **self.parser.western_max, **self.parser.rennen_max, **self.parser.fahren_max}
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
                gesundheit = (self.parser.details_values['Gesundheit']-400)/200
                charakter = self.parser.details_values['Charakter'] / 1200
                exterieur = self.parser.details_values['Exterieur'] / 800
                ausbildung = self.parser.training_max['Ausbildung'] / 2200
                gangarten = self.parser.training_max['Gangarten'] / 3100
                dressur = self.parser.training_max['Dressur'] /3300
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