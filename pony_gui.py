# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import font
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path
import csv
from datetime import datetime
from datetime import timedelta
import win32clipboard
import webbrowser
import time
import multiprocessing
import sys
import subprocess
import requests

import lang
import stats_parser
import html_clipboard
import dialog
import build_count

HALLOWEEN = False

class ProgressWindow(tk.Toplevel):
    def __init__(self, parent, gui, title=lang.PROGRESS, steps=100, initial_text=''):

        tk.Toplevel.__init__(self, parent)
        self.configure(bg="#EDEEF3")
        try:
            self.iconbitmap("favicon.ico")
        except:
            pass
        self.gui = gui
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.max_value = 100
        self.steps = steps
        self.stepsize = self.max_value/self.steps
        self.value = 0

        self.frame = tk.Frame(self, bg=self.gui.bg)

        self.pb_text = tk.Label(self.frame, text=initial_text, font=self.gui.default_font, bg=self.gui.bg)
        self.pb_text.pack()
        self.pb = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.pb.pack()

        self.frame.pack()

        self.attributes('-disabled', True)

    def pad_str(self, text):
        PAD_TO = 50
        l = len(text)
        if not l >= 30:
            pad_to_half = PAD_TO // 2
            l_half = l // 2
            text = text.rjust(pad_to_half+l_half)
            text = text.ljust(PAD_TO)
        return text


    def step(self, text=None):
        if text is not None:
            self.pb_text.configure(text=self.pad_str(text))
        self.value += self.stepsize
        self.pb['value'] = self.value
        if self.value > self.max_value-self.stepsize/2:
            self.destroy()
        self.gui.root.update()

    def close(self):
        self.destroy()


def argsort(seq):
    #http://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python/3382369#3382369
    #by unutbu
    return sorted(range(len(seq)), key=seq.__getitem__)[::-1]

class ListingWindow(dialog.Dialog):
    def cancel(self, event=None):
        self.gui.enable_buttons()
        dialog.Dialog.cancel(self, event)

    def header(self, master):
        pass

    def body(self, master):
        quick_display = self.gui.quick_display
        self.gui.quick_display = False
        too_many_redirects_ids = []
        if not self.gui.exterior_search_requested:
            own_file = Path('./owned_ponies')
            all_ids = []
            if own_file.is_file():
                with open(own_file, 'r') as f:
                    all_ids = f.read().split()
        else:
            all_ids = self.gui.exterior_search_ids

        beauty_file = Path('./beauty_ponies')
        self.beauty_ids = []
        if beauty_file.is_file():
            with open(beauty_file, 'r') as f:
                self.beauty_ids = f.read().split()

        progressbar = ProgressWindow(self, self.gui, steps=len(all_ids)+3, initial_text=lang.PROGRESS_READING_CONFIG)
        self.MAXROWS = 25
        self.MAX_LEN_NAME = 20
        self.MAX_LEN_PROP = 3
        self.max_prop_dict = dict()
        for key in self.gui.extractor.parser.training_headings:
            self.max_prop_dict[key] = 0
        self.now = datetime.now()
        self.def_size = self.gui.default_size
        self.def_font = font.Font(family=self.gui.default_font['family'], size=self.def_size)
        self.bol_font = font.Font(family=self.gui.default_font['family'], size=self.def_size, weight='bold')
        self.show_sex = 0  # 0: all, 1: female, 2: male
        lname = self.gui.market_listing_var.get() if self.gui.exterior_search_requested else self.gui.option_var.get()
        price_type = self.gui.horse_page_type_var.get() if self.gui.exterior_search_requested else ''
        if not lname == lang.EXTERIEUR_LISTING:
            lfile = self.gui.listing_files[self.gui.listing_names.index(lname)]
            with open(lfile, 'r', encoding='utf-8') as f:
                config = f.read().splitlines()
            if self.gui.exterior_search_requested:
                config[0] = self.gui.race_var.get()   # race to filter for always equals the race the market search was filtered for
                # config.append('=')
                # config.append('id')
                if len(price_type) != 0 and price_type != lang.HORSE_PAGE_ALL and 'all' not in price_type:
                    config.extend(['=', lang.LISTING_HEADER_PRICE])
        else:
            # config = [self.gui.race_var.get(), 'Exterieur: Haltung, Ausdruck, Kopf, Halsansatz, Rückenlinie, Beinstellung', '=', 'id']
            config = [self.gui.race_var.get(), 'Exterieur: Haltung, Ausdruck, Kopf, Halsansatz, Rückenlinie, Beinstellung']
            if len(price_type) != 0 and price_type != lang.HORSE_PAGE_ALL and 'all' not in price_type:
                config.extend(['=', lang.LISTING_HEADER_PRICE])
        races = [r.strip() for r in config[0].split(',')]
        if 'Alle'.strip("'") in races:
            races = list(self.gui.extractor.race_dict.keys())
            config.append('=')
            config.append('Rasse')
        self.props = []
        divider_found = False
        self.additional = []
        p = self.gui.extractor.parser
        valid_keys = [p.gesundheit_headings, p.charakter_headings, p.exterieur_headings, p.ausbildung_headings, p.gangarten_headings, p.dressur_headings,
                      p.springen_headings, p.military_headings, p.western_headings, p.rennen_headings, p.fahren_headings, ['id', lang.LISTING_HEADER_PRICE]]
        for l in config[1:]:
            if '=' in l:
                divider_found = True
                valid_keys.append(p.facts_headings)
                continue
            if not divider_found:
                append_to = self.props
            else:
                append_to = self.additional
            colon_split = l.split(':')
            part = [colon_split[0]]
            if len(colon_split) > 1:
                part.append([attr.strip() for attr in colon_split[1].split(',')])
            else:
                part_ok = False           # Anything that is not in the parser keys does not make sense here. facts are additionaly allowed if we are after the divider (which means no average has to be computed)
                for keylist in valid_keys:
                    if part[0] in keylist:
                        part_ok = True
                if not part_ok:
                    continue
            append_to.append(part)

        progressbar.step(lang.PROGRESS_MAKING_HEADERS)

        self.objects = []
        self.cache_exists_for_row = []    # after get_pony_info is called, extractor.cache_exists specifies whether a valid cache folder exists for that pony. If it doesn't, pony should be excluded
                                          # when determining relatives
        self.data_table = []
        self.data_table_sum = []
        self.object_colors = []
        self.sex = []
        self.banners = []
        self.images = []

        self.button_frame = tk.Frame(master, bg=self.gui.bg)
        self.button_frame.grid(row=0, column=0, padx=self.def_size, pady=self.def_size, sticky=tk.W)
        self.check_sum_var = tk.IntVar()  # Whether to show averaged values for attribute categories (0), or the sum values (1) (the latter are the numbers displayed on the HTML)
        self.check_sum_var.set(1)
        self.sum_checkbutton = tk.Checkbutton(self.button_frame, text=lang.CHECK_LISTING_SUM, font=self.def_font, variable=self.check_sum_var, command=self.toggle_show_sum, bg=self.gui.bg)
        self.sum_checkbutton.grid(row=0, column=0, padx=int(self.def_size / 2))
        self.sex_all_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_ALL, font=self.def_font, command=lambda: self.filter_sex(0), bg=self.gui.bg)
        self.sex_all_button.grid(row=0, column=1, padx=int(self.def_size / 2))
        self.sex_female_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_FEMALE, font=self.def_font, command=lambda: self.filter_sex(1), bg=self.gui.bg)
        self.sex_female_button.grid(row=0, column=2, padx=int(self.def_size / 2))
        self.sex_male_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_MALE, font=self.def_font, command=lambda: self.filter_sex(2), bg=self.gui.bg)
        self.sex_male_button.grid(row=0, column=3, padx=int(self.def_size / 2))

        self.gui.race_ids = []
        self.table_frame = tk.Frame(master, bg=self.gui.bg)
        self.table_frame.grid(row=1, column=0, padx=self.def_size)
        self.header_objects = [tk.Button(self.table_frame, text=lang.LISTING_HEADER_NAME[:self.MAX_LEN_NAME], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_NAME: self.sort(p), bg=self.gui.bg)]
        self.header_max_labels = [tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg)]
        self.data_headers = [lang.LISTING_HEADER_NAME]
        self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AGE[:self.MAX_LEN_PROP], command=lambda p=lang.LISTING_HEADER_AGE: self.sort(p), bg=self.gui.bg))
        self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
        self.data_headers.append(lang.LISTING_HEADER_AGE)
        self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_POTENTIAL[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_POTENTIAL: self.sort(p), bg=self.gui.bg))
        self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
        self.data_headers.append(lang.LISTING_HEADER_POTENTIAL)
        NUM_NON_USER_PROP = 3  # number of entries in the data table that is not defined by the user (and which the average is calculated over). Does not include the image!
        avg_done = False
        for prop_list in [self.props, self.additional]:
            for prop in prop_list:
                self.header_objects.append(tk.Button(self.table_frame, text=prop[0][:self.MAX_LEN_PROP], command=lambda p=prop[0]: self.sort(p), bg=self.gui.bg))
                self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
                self.data_headers.append(prop[0])
            if not avg_done:
                self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AVERAGE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_AVERAGE: self.sort(p), bg=self.gui.bg))
                self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
                self.data_headers.append(lang.LISTING_HEADER_AVERAGE)
                self.BOLD_COLUMNS = [0, 2, len(self.data_headers) - 1]
                avg_done = True
        for ci, el in enumerate(self.header_max_labels):
            el.grid(row=0, column=ci+1, padx=int(self.def_size / 2))
        for ci, el in enumerate(self.header_objects):
            el.grid(row=1, column=ci+1, padx=int(self.def_size / 2))   # ci + 1 because the image does not have a corresponding header!

        for idx, id in enumerate(all_ids):
            progressbar.step(str(id))
            if quick_display:
                parser = stats_parser.FakeParser(self.gui.extractor.images[idx], self.gui.extractor.ponies[idx])
            else:
                if not self.gui.extractor.get_pony_info(id):
                    if 'too many redirects' in self.gui.extractor.log[-1].lower():
                        too_many_redirects_ids.append(id)
                        continue
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                    progressbar.close()
                    return
                parser = self.gui.extractor.parser
            if parser.facts_values['Rasse'] in races:
                self.gui.race_ids.append(id)
                if quick_display:
                    self.cache_exists_for_row.append(False)   # No relatives display if we are in quick mode
                else:
                    self.cache_exists_for_row.append(self.gui.extractor.cache_exists)
                if quick_display:
                    im = self.gui.imorg
                elif not self.gui.extractor.request_pony_images(urls=parser.image_urls, pony_id=id):
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                    im = self.gui.imorg
                else:
                    im = self.gui.extractor.pony_image
                object_row = []
                table_row = []
                table_row_sum = []

                dim = self.gui.dims_by_scale(0.001 * self.def_size)[0]
                fac = float(dim) / im.size[0]
                dim2 = int(im.size[1] * fac)
                im = im.resize((dim, dim2), Image.ANTIALIAS)
                self.images.append(im)
                self.banners.append(ImageTk.PhotoImage(im))
                object_row.append(tk.Label(self.table_frame, image=self.banners[-1], bg=self.gui.bg, cursor="hand2"))
                object_row[-1].bind("<Button-1>", lambda e, pid=id: self.del_cache(e, pid))
                object_row[-1].bind("<Button-3>", lambda e, pid=id: self.toggle_beauty(e, pid))
                object_row[-1].configure(borderwidth=1*int(id in self.beauty_ids), relief="solid")
                object_row.append(tk.Label(self.table_frame, text=parser.name[:self.MAX_LEN_NAME], font=self.bol_font, bg=self.gui.bg, cursor="hand2"))
                object_row[-1].bind("<Button-1>", lambda e, url=self.gui.extractor.base_url + 'horse.php?id={}'.format(id): webbrowser.open(url))
                object_row[-1].bind("<Button-3>", lambda e, hid=id: self.mark_relatives(hid))
                table_row.append(parser.name)
                table_row_sum.append(parser.name)

                age = self.get_age(parser)
                if age is None:
                    object_row.append(tk.Label(self.table_frame, text=lang.LISTING_DEAD, font=self.def_font, bg=self.gui.bg))
                    pony_years = -1
                    age = timedelta()
                else:
                    pony_months = age.days
                    pony_years = pony_months // 12
                    pony_months %= 12
                    object_row.append(tk.Label(self.table_frame, text='{}/{}'.format(pony_years, pony_months), font=self.def_font, bg=self.gui.bg))
                table_row.append(age)
                table_row_sum.append(age)

                table_row.append(parser.training_max['Gesamtpotenzial'])
                table_row_sum.append(parser.training_max['Gesamtpotenzial'])
                object_row.append(tk.Label(self.table_frame, text=table_row[-1], font=self.bol_font, bg=self.gui.bg))

                avg_done = False
                for prop_list in [self.props, self.additional]:
                    for prop in prop_list:
                        if prop[0] == 'id':
                            normval = textval = id
                            object_row.append(tk.Label(self.table_frame, text=str(textval), font=self.def_font, bg=self.gui.bg, cursor="hand2"))
                            object_row[-1].bind("<Button-1>", lambda e, url=self.gui.extractor.base_url + 'horse.php?id={}'.format(id): webbrowser.open(url))
                        elif prop[0] == lang.LISTING_HEADER_PRICE:
                            if price_type == lang.HORSE_PAGE_STUD:
                                pkey = 'deckstation'
                            elif price_type == lang.HORSE_PAGE_TRADE:
                                pkey = 'verkauf'
                            else:
                                continue
                            try:
                                normval = textval = parser.facts_values[pkey]
                            except:
                                normval = textval = 0
                                print('could not read key {} from pony {}. Price was set to 0. Deleting Cache might help.'.format(pkey, id))
                            object_row.append(tk.Label(self.table_frame, text=str(textval), font=self.def_font, bg=self.gui.bg))
                        else:
                            if len(prop) == 1:
                                val, norm = self.gui.get_prop_value_and_count(prop[0], parser=parser)
                            else:
                                norm = len(prop[1])
                                val = 0
                                for subprop in prop[1]:
                                    val += self.gui.get_prop_value(subprop, parser=parser)
                            if isinstance(val, (int, float)):
                                normval = val/norm
                                textval = str(round(normval, 1))
                            else:
                                normval = textval = val
                            object_row.append(tk.Label(self.table_frame, text=textval, font=self.def_font, bg=self.gui.bg))
                        table_row.append(normval)
                        if len(prop) == 1 and (prop[0] in ['Gesundheit', 'Charakter', 'Exterieur'] or prop[0] in parser.training_headings):
                            table_row_sum.append(val)      # referenced before assignment only if lang.LISTING_HEADER_PRICE in details_topheadings or training_headings, which is not the case
                        else:
                            table_row_sum.append(normval)

                    for key in self.max_prop_dict.keys():
                        this_val = self.gui.get_prop_value(key, parser=parser)
                        if self.max_prop_dict[key] < this_val:
                            self.max_prop_dict[key] = this_val

                    # total average - only done once
                    if not avg_done:
                        table_row.append(sum(table_row[NUM_NON_USER_PROP:])/(len(table_row)-NUM_NON_USER_PROP))
                        table_row_sum.append(sum(table_row[NUM_NON_USER_PROP:]) / (len(table_row) - NUM_NON_USER_PROP))
                        object_row.append(tk.Label(self.table_frame, text=str(round(table_row[-1], 1)), font=self.bol_font, bg=self.gui.bg))
                        avg_done = True

                self.objects.append(object_row)
                self.data_table.append(table_row)
                self.data_table_sum.append(table_row_sum)

                if parser.facts_values['Geschlecht'] == 'Stute':
                    self.sex.append(1)
                else:
                    self.sex.append(2)

                if pony_years < 0:    # dead
                    col = 'dim gray'
                elif pony_years < 3:
                    if self.sex[-1] == 1:
                        col = 'hot pink'
                    else:
                        col = 'dodger blue'
                else:
                    if self.sex[-1] == 1:
                        col = 'red4'
                    else:
                        col = 'blue'
                for el in object_row:
                    el.configure(fg=col)
                self.object_colors.append(col)

        for hdi, hd in enumerate(self.data_headers):
            if hd in self.max_prop_dict.keys():
                self.header_max_labels[hdi].configure(text=str(self.max_prop_dict[hd]))

        progressbar.step(lang.PROGRESS_DRAWING_SCALING)
        self.toggle_show_sum()
        self.draw_objects()

        redraw = False
        while 2.5*self.def_size*(min(self.MAXROWS, len(self.data_table))+4) + 2.5*self.gui.default_size > self.gui.screenheight*0.8:
            redraw = True
            self.def_size -= 1
            self.def_font['size'] = self.def_size
            self.bol_font['size'] = self.def_size
        if redraw:
            self.redraw()

        progressbar.step(lang.PROGRESS_DONE)

        if len(too_many_redirects_ids) > 0:
            message = lang.REDIRECTS_WARNING_MESSAGE
            for pid in too_many_redirects_ids:
                message += ('\n' + str(pid))
            messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def mark_relatives(self, id):
        rels = self.get_relatives(id)
        for orow, ocol, oid in zip(self.objects, self.object_colors, self.gui.race_ids):
            if int(oid) in rels:
                col = 'Black'
            else:
                col = ocol
            for o in orow:
                o.configure(fg=col)

    def toggle_show_sum(self):
        show_sum = self.check_sum_var.get()
        data_table = self.data_table_sum if show_sum else self.data_table
        for ri, object_row in enumerate(self.objects):
                for ci, el in enumerate(object_row):
                    if ci < 4:
                        continue   # objects begin with image, Name, age, Potential, which are never converted
                    val = data_table[ri][ci-1]
                    if type(val) == int:
                        val = str(val)
                    elif type(val) == float:
                        val = str(round(val, 1))
                    el.configure(text=val)
        self.redraw()

    def get_relatives(self, pid_str):
        pid = int(pid_str)
        result = [pid]
        if self.cache_exists_for_row[self.gui.race_ids.index(pid_str)]:
            self.gui.extractor.get_pony_info(pid)
            # Nur ersten und dritten Vorfahr wählen. Das sind Vater und Mutter. Vorfahren werden wie folgt eingelsen:
            # [Vater, Großvater(V), Großmutter(V), Mutter, Großvater(M), Großmutter(M)]
            # Falls Vater Systempferd ist, wird der Vater als Großeltern wiederholt eingetragen. Beispiel:
            # [System-Vater, Vater, Vater, Mutter, Großvater(M), Großmutter(M)]
            # Die Liste ist also entweder leer, oder hat 6 Einträge oder 4 Einträge (Wenn beide Entern Systempferde).
            anc_list = self.gui.extractor.parser.ancestors
            if len(anc_list) == 6 or len(anc_list) == 0 or len(anc_list) == 4:
                this_ancestors = list(anc_list[::3])
            else:
                messagebox.showerror(title='error', message='invalid ancestor list')
                return []
            this_ancestors.append(pid)
            for comp_id, cache_bool in zip(self.gui.race_ids, self.cache_exists_for_row):
                comp_id = int(comp_id)
                if comp_id != pid:
                    if comp_id in this_ancestors:
                        result.append(comp_id)
                        continue
                    if cache_bool:
                        self.gui.extractor.get_pony_info(comp_id)
                        comp_ancestors = self.gui.extractor.parser.ancestors[::3]
                        for comp_an in comp_ancestors:
                            if comp_an in this_ancestors:
                                result.append(comp_id)
                                break
        return result

    def toggle_beauty(self, event, pid):
        lab = event.widget
        if lab['borderwidth'] == 1:
            lab['borderwidth'] = 0
            self.beauty_ids.remove(pid)
        else:
            lab['borderwidth'] = 1
            self.beauty_ids.append(pid)
        beauty_file = Path('./beauty_ponies')
        with open(beauty_file, 'w') as f:
            for pid in self.beauty_ids:
                f.write(str(pid) + '\n')

    def del_cache(self, event, pid):
        lab = event.widget
        if lab['state'] == tk.NORMAL:
            lab['state'] = tk.DISABLED
            lab['cursor'] = ''
            self.gui.del_cache(pid)

    def get_age(self, parser):
        if 'Geburtstag' in parser.facts_values.keys() and parser.facts_values['Geburtstag'] != 0:
            birthday_split = parser.facts_values['Geburtstag'].split('-')
            date_str = birthday_split[0].strip()
            time_str = birthday_split[1].strip()
            time_split = time_str.split(':')
            hour = int(time_split[0])
            minute = int(time_split[1])
            date_split = date_str.split('.')
            year = int(date_split[2])
            month = int(date_split[1])
            day = int(date_split[0])
            return self.now - datetime(year, month, day, hour, minute)
        else:
            if 'Alter' in parser.facts_values.keys():
                if 'gestorben' in parser.facts_values['Alter'].lower():
                    return None  # dead pony
                else:
                    age = parser.facts_values['Alter']
                    agesplit = age.split()
                    years = 0
                    months = 0
                    # probably quick mode, extract timedelta from format [1 Monat / 6 Monate / 1 Jahr / 1 Jahr 1 Monat / 1 Jahr 6 Monate / 2 Jahre / 2 Jahre 1 Monat / 2 Jahre 6 Monate]
                    if 'Monat' in age:
                        if 'Jahr' in age:
                            years = int(agesplit[0])
                            months = int(agesplit[2])
                        else:
                            months = int(agesplit[0])
                    else:
                        if 'Jahr' in age:
                            years = int(agesplit[0])
                    # a month is one day
                    return timedelta(days=years*12+months)
            else:
                return timedelta()  # some error

    def draw_objects(self):
        if self.show_sex == 0:
            disp_sex = [1,2]
        else:
            disp_sex = [self.show_sex]
        row_index = 0
        for ri, object_row in enumerate(self.objects):
            if self.sex[ri] in disp_sex:
                for ci, el in enumerate(object_row):
                    rindex = row_index % self.MAXROWS
                    cindex = ci + len(object_row) * (row_index // self.MAXROWS)
                    el.grid(row=rindex+2, column=cindex, padx=int(self.def_size/2))
                row_index += 1

    def redraw(self):
        self.sum_checkbutton.grid_forget()
        self.sex_all_button.grid_forget()
        self.sex_female_button.grid_forget()
        self.sex_male_button.grid_forget()
        self.button_frame.grid_forget()
        self.table_frame.grid_forget()
        for i, h in enumerate(self.header_objects):
            h.grid_forget()
            if i in self.BOLD_COLUMNS:
                h.configure(font=self.bol_font)
            else:
                h.configure(font=self.def_font)
        for i, h in enumerate(self.header_max_labels):
            h.grid_forget()
            h.configure(font=self.def_font)
        for ri, object_row in enumerate(self.objects):
            for ci, el in enumerate(object_row):
                if (ci-1) in self.BOLD_COLUMNS:  # ci - 1 because BOLD_COLUMNS is for header columns (without) image. So 1 here corresponds to 0 in BOLD_COLUMNS
                    el.configure(font=self.bol_font)
                else:
                    el.configure(font=self.def_font)
                el.grid_forget()
        self.sex_all_button.configure(font=self.def_font)
        self.sex_female_button.configure(font=self.def_font)
        self.sex_male_button.configure(font=self.def_font)
        self.button_frame.grid(row=0, column=0, padx=self.def_size, pady=self.def_size, sticky=tk.W)
        self.sum_checkbutton.grid(row=0, column=0, padx=int(self.def_size / 2))
        self.sex_all_button.grid(row=0, column=1, padx=int(self.def_size / 2))
        self.sex_female_button.grid(row=0, column=2, padx=int(self.def_size / 2))
        self.sex_male_button.grid(row=0, column=3, padx=int(self.def_size / 2))
        for ii, im in enumerate(self.images):
            dim = self.gui.dims_by_scale(0.001 * self.def_size)[0]
            fac = float(dim) / im.size[0]
            dim2 = int(im.size[1] * fac)
            im = im.resize((dim, dim2), Image.ANTIALIAS)
            self.banners[ii] = ImageTk.PhotoImage(im)
            self.objects[ii][0].configure(image=self.banners[ii])
        self.table_frame.grid(row=1, column=0, padx=self.def_size)
        for ci, el in enumerate(self.header_objects):
            el.grid(row=1, column=ci + 1, padx=int(self.def_size / 2))  # ci + 1 because is for header columns are without image.
        for ci, el in enumerate(self.header_max_labels):
            el.grid(row=0, column=ci + 1, padx=int(self.def_size / 2))
        self.draw_objects()

    def filter_sex(self, sex_identifier):
        self.show_sex = sex_identifier
        for ri, object_row in enumerate(self.objects):
            for ci, el in enumerate(object_row):
                el.grid_forget()
        self.draw_objects()

    def sort(self, prop):
        if self.show_sex == 0:
            disp_sex = [1,2]
        else:
            disp_sex = [self.show_sex]
        row_to_sort_by = self.data_headers.index(prop)
        avgs = [row[row_to_sort_by] for row in self.data_table]
        sorted_idx = argsort(avgs)
        for ri, object_row in enumerate(self.objects):
            for ci, el in enumerate(object_row):
                el.grid_forget()
        objects_sorted = []
        object_colors_sorted = []
        table_sorted = []
        table_sorted_sum = []
        sex_sorted = []
        race_ids_sorted = []
        cache_exists_for_row_sorted = []
        for pid in sorted_idx:
            objects_sorted.append(self.objects[pid])
            object_colors_sorted.append(self.object_colors[pid])
            table_sorted.append(self.data_table[pid])
            table_sorted_sum.append(self.data_table_sum[pid])
            sex_sorted.append(self.sex[pid])
            race_ids_sorted.append(self.gui.race_ids[pid])
            cache_exists_for_row_sorted.append(self.cache_exists_for_row[pid])
        self.objects = objects_sorted
        self.object_colors = object_colors_sorted
        self.data_table = table_sorted
        self.data_table_sum = table_sorted_sum
        self.sex = sex_sorted
        self.gui.race_ids = race_ids_sorted
        self.cache_exists_for_row = cache_exists_for_row_sorted
        self.draw_objects()

class LoginWindow(dialog.Dialog):
    def header(self, master):
        pass

    def body(self, master):
        try:
            with open('login', 'r') as f:
                user_loaded = f.readline().strip()
                pw_loaded = f.readline().strip()
                tel_loaded = f.readline().strip()
        except IOError:
            user_loaded = ''
            pw_loaded = ''
        tk.Label(master, text=lang.USER_LABEL, font=self.gui.default_font, bg=self.gui.bg).grid(row=0, column=0, padx=self.gui.default_size//2)
        self.user_var = tk.StringVar()
        self.user_var.set(user_loaded)
        self.user_entry = tk.Entry(master, textvariable=self.user_var, bg=self.gui.bg)
        self.user_entry.grid(row=0, column=1)
        tk.Label(master, text=lang.PASSWORD_LABEL, font=self.gui.default_font, bg=self.gui.bg).grid(row=1, column=0, padx=self.gui.default_size//2)
        self.pw_var = tk.StringVar()
        self.pw_var.set(pw_loaded)
        self.pw_entry = tk.Entry(master, textvariable=self.pw_var, bg=self.gui.bg)
        self.pw_entry.grid(row=1, column=1)
        tk.Label(master, text=lang.TELEGRAM_LABEL, font=self.gui.default_font, bg=self.gui.bg).grid(row=2, column=0, padx=self.gui.default_size // 2)
        self.tel_var = tk.StringVar()
        self.tel_var.set(tel_loaded)
        self.tel_entry = tk.Entry(master, textvariable=self.tel_var, bg=self.gui.bg)
        self.tel_entry.grid(row=2, column=1)

    def apply(self):
        self.gui.user = self.user_var.get().strip()
        self.gui.pw = self.pw_var.get().strip()
        self.gui.telegram_id = self.tel_var.get().strip()
        with open('login', 'w') as f:
            f.write('{}\n{}\n{}'.format(self.gui.user, self.gui.pw, self.gui.telegram_id))

class Notification:
    def __init__(self, pid, pony_name, stud=True):
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.bg = "#EDEEF3"
        try:
            self.root.iconbitmap("favicon.ico")
        except:
            pass
        self.base_url = 'https://noblehorsechampion.com/inside/'
        self.screenwidth = self.root.winfo_screenwidth()
        self.screenheight = self.root.winfo_screenheight()
        self.screen_resolution = [self.screenwidth, self.screenheight]
        self.hdfactor = self.screenheight / 1080.
        self.default_size = int(round(15 * self.hdfactor))
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(size=self.default_size)
        self.root.title(lang.NOTIFICATION_TITLE)
        self.root.configure(bg=self.bg)
        self.frame = tk.Frame(self.root, bg=self.bg)
        self.frame.grid(padx=self.default_size, pady=self.default_size//2)
        message_text = lang.NOTIFICATION_STUD if stud else lang.NOTIFICATION_TRADE
        self.lbl = tk.Label(self.frame, text=message_text.format(pid, pony_name), font=self.default_font, bg=self.bg, cursor="hand2")
        self.lbl.grid(pady=self.default_size//2)
        self.lbl.bind("<Button-1>", lambda e, url=self.base_url + 'horse.php?id={}'.format(pid): webbrowser.open(url))
        tk.Button(self.frame, text='OK', command=self.on_closing, bg=self.bg).grid(pady=self.default_size//2)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes("-toolwindow", 1)
        self.root.mainloop()

    def on_closing(self):
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

def poll_function(id):
    extractor = stats_parser.PonyExtractor()
    done = False

    while not done:
        if extractor.get_pony_info(id, cached=False):
            stud = None
            if 'deckstation' in extractor.parser.facts_values.keys():
                stud = True
            elif 'verkauf' in extractor.parser.facts_values.keys():
                stud = False
            if stud is not None:
                # print("Deckstation! ({})".format(id))
                pony_name = extractor.parser.name
                message_text = lang.NOTIFICATION_STUD.format(id, pony_name) if stud else lang.NOTIFICATION_TRADE.format(id, pony_name)
                _ = extractor.telegram_bot_sendtext(message_text)
                # print(test)
                _ = Notification(id, pony_name, stud=stud)
                # messagebox.showinfo(lang.NOTIFICATION_TITLE, lang.NOTIFICATION_TEXT.format(id, pony_name))
                done = True
            else:
                pass
                # print("Noch nicht... ({})".format(id))
        else:
            print("Request Failed for poll id {}".format(id))
            print(extractor.log[-1])
        time.sleep(60)

def halloween_poll():
    extractor = stats_parser.PonyExtractor()
    done = False
    found_counter = 1

    URLS = ['https://noblehorsechampion.com/inside/index.php',
            'https://noblehorsechampion.com/inside/contests.php',
            'https://noblehorsechampion.com/inside/estate.php',
            'https://noblehorsechampion.com/inside/competitions.php',
            'https://noblehorsechampion.com/inside/wiki.php']
    url_index = 0

    while not done:
        url = URLS[url_index]
        # print('Checking URL {}'.format(url))
        text = extractor.open_page_in_browser(url)
        if text:
            if 'Belohnungen einzutauschen' in text:
                print('Halloween-Item gefunden nach {} Aufrufen'.format(found_counter))
                found_counter = 1
                # Gefunden!
                time.sleep(61)
            else:
                found_counter += 1
                time.sleep(1)
        url_index += 1
        url_index %= len(URLS)


class PonyGUI:
    def __init__(self):
        self.__version__ = build_count.__version__
        self.extractor = stats_parser.PonyExtractor()
        own_file = Path('./owned_ponies')
        beauty_file = Path('./beauty_ponies')
        if not own_file.is_file():
            with open(own_file, 'w') as f:
                pass
        if not beauty_file.is_file():
            with open(beauty_file, 'w') as f:
                pass
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.user = ''
        self.pw = ''
        self.telegram_id = ''
        self.poll_ids = []
        self.poll_processes = []
        self.halloween_process = None
        # self.chromedriver_process = None
        self.bg = "#EDEEF3"
        self.screenwidth = self.root.winfo_screenwidth()
        self.screenheight = self.root.winfo_screenheight()
        self.screen_resolution = [self.screenwidth, self.screenheight]
        self.hdfactor = self.screenheight/1080.
        self.default_size = int(round(15*self.hdfactor))
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(size=self.default_size)
        self.small_font = self.default_font.copy()
        self.small_font.configure(size=self.default_size//2)
        self.small_bold_font = self.small_font.copy()
        self.small_bold_font.configure(weight="bold")
        self.text_font = font.nametofont("TkTextFont")
        self.text_font.configure(size=self.default_size)
        self.bold_font = self.default_font.copy()
        self.bold_font.configure(weight="bold")
        self.big_bold_font = self.bold_font.copy()
        self.big_bold_font.configure(size=int(1.33*self.default_size))
        try:
            self.root.iconbitmap("favicon.ico")
        except:
            pass
        self.root.title(lang.MAIN_TITLE)
        self.root.configure(bg=self.bg)
        self.exterior_search_requested = False
        self.quick_display = False
        self.exterior_search_ids = []

        self.interactive_elements = []

        # Create gui elements here
        # banner
        self.imorg = Image.open("4logo-sm.png")
        dim = self.dims_by_scale(0.01 * self.default_size)[0]
        fac = float(dim) / self.imorg.size[0]
        dim2 = int(self.imorg.size[1] * fac)
        imobj = self.imorg.resize((dim, dim2), Image.ANTIALIAS)
        self.banner = ImageTk.PhotoImage(imobj)
        self.banner_label = tk.Label(self.root, image=self.banner, bg=self.bg)
        self.banner_label.grid(rowspan=6, padx=(self.default_size, 0), pady=(self.default_size, 0))

        self.quality_label = tk.Label(self.root, text='', bg=self.bg)
        self.quality_label.grid(row=6, column=0)

        self.title_frame = tk.Frame(self.root, bg=self.bg)
        self.title_frame.grid(row=0, column=1, columnspan=2, padx=self.default_size)
        self.name_label = tk.Label(self.title_frame, text='', font=self.big_bold_font, bg=self.bg)
        self.name_label.grid()
        self.id_label = tk.Label(self.title_frame, text='', font=self.bold_font, bg=self.bg)
        self.id_label.grid()

        self.id_frame = tk.Frame(self.root, bg=self.bg)
        self.id_frame.grid(row=1, column=1, columnspan=2, padx=self.default_size)
        tk.Label(self.id_frame, text=lang.PONY_ID, font=self.default_font, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size/2))
        self.id_spin = tk.Spinbox(self.id_frame, width=6, from_=0, to=999999, bg=self.bg)
        self.id_spin.grid(row=0, column=1, padx=int(self.default_size/2))
        self.check_ownership_var = tk.IntVar()
        self.check_ownership_var.set(0)
        self.ownership_checkbutton = tk.Checkbutton(self.id_frame, text=lang.CHECK_OWN, font=self.default_font, variable=self.check_ownership_var, command=self.update_owned, bg=self.bg)
        self.ownership_checkbutton.grid(row=0, column=2, padx=int(self.default_size/2))
        self.ownership_checkbutton.configure(state=tk.DISABLED)
        self.interactive_elements.append(self.ownership_checkbutton)
        self.check_poll_var = tk.IntVar()
        self.check_poll_var.set(0)
        self.poll_checkbutton = tk.Checkbutton(self.id_frame, text=lang.AVAILABILITY_POLL, font=self.small_font, wraplength=120, justify=tk.LEFT, variable=self.check_poll_var, command=self.deckstation_poll_toggle, bg=self.bg)
        self.poll_checkbutton.bind("<Button-3>", lambda e: self.deckstation_poll_cancel_all())
        self.poll_checkbutton.grid(row=0, column=3, padx=int(self.default_size/2))
        self.poll_checkbutton.configure(state=tk.DISABLED)
        self.interactive_elements.append(self.poll_checkbutton)

        self.a_button_frame = tk.Frame(self.root, bg=self.bg)
        self.a_button_frame.grid(row=2, column=1, columnspan=2, padx=self.default_size)
        self.request_button = tk.Button(self.a_button_frame, text=lang.REQUEST, command=self.request, bg=self.bg)
        self.request_button.grid(row=0, column=0, padx=self.default_size//2, pady=int(self.default_size/2))
        try:
            with open('login', 'r') as f:
                _ = f.readline().strip()
                _ = f.readline().strip()
        except IOError:
            self.request_button.configure(state=tk.DISABLED)
        self.interactive_elements.append(self.request_button)
        self.login_button = tk.Button(self.a_button_frame, text=lang.LOGIN_BUTTON, command=self.enter_login, bg=self.bg)
        self.login_button.grid(row=0, column=1, padx=self.default_size//2, pady=int(self.default_size/2))
        self.interactive_elements.append(self.login_button)

        self.export_button = tk.Button(self.a_button_frame, text=lang.EXPORT, command=self.export, bg=self.bg, state=tk.DISABLED)
        self.export_button.grid(row=1, column=0, padx=int(self.default_size/2), pady=int(self.default_size/2))
        self.interactive_elements.append(self.export_button)

        # self.radio_frame = tk.Frame(self.root, bg=self.bg)
        # self.radio_frame.grid(row=4, column=1, columnspan=2, padx=self.default_size)
        # self.export_format_var = tk.IntVar()
        # self.export_format_var.set(0)
        # tk.Radiobutton(self.radio_frame, text=lang.RADIO_HTML, variable=self.export_format_var, value=0, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size/2))
        # tk.Radiobutton(self.radio_frame, text=lang.RADIO_CSV, variable=self.export_format_var, value=1, bg=self.bg).grid(row=0, column=1, padx=int(self.default_size / 2))
        # self.export_method_var = tk.IntVar()
        # self.export_method_var.set(0)
        # tk.Radiobutton(self.radio_frame, text=lang.RADIO_CLIPBOARD, variable=self.export_method_var, value=0, bg=self.bg).grid(row=1, column=0, padx=int(self.default_size / 2))
        # tk.Radiobutton(self.radio_frame, text=lang.RADIO_FILE, variable=self.export_method_var, value=1, bg=self.bg).grid(row=1, column=1, padx=int(self.default_size / 2))

        self.checkbox_frame = tk.Frame(self.root, bg=self.bg)
        self.checkbox_frame.grid(row=3, column=1, columnspan=2, padx=self.default_size)
        
        self.check_all_var = tk.IntVar()
        self.check_all_var.set(0)
        tk.Checkbutton(self.a_button_frame, text=lang.CHECK_ALL, font=self.bold_font, variable=self.check_all_var, command=self.toggle_all_var, bg=self.bg).grid(row=1, column=1,
                                                                                                                                                                 padx=int(self.default_size/2))
        self.check_var_container = []
        self.check_gesundheit_var = tk.IntVar()
        self.check_gesundheit_var.set(1)
        self.check_var_container.append(self.check_gesundheit_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_GESUNDHEIT, font=self.default_font, variable=self.check_gesundheit_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=0,
                                                                                                                                                                     padx=int(self.default_size / 2))
        self.check_charakter_var = tk.IntVar()
        self.check_charakter_var.set(1)
        self.check_var_container.append(self.check_charakter_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_CHARAKTER, font=self.default_font, variable=self.check_charakter_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=1,
                                                                                                                                                                    padx=int(self.default_size / 2))
        self.check_exterieur_var = tk.IntVar()
        self.check_exterieur_var.set(1)
        self.check_var_container.append(self.check_exterieur_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_EXTERIEUR, font=self.default_font, variable=self.check_exterieur_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=2,
                                                                                                                                                                    padx=int(self.default_size / 2))
        self.check_training_var = tk.IntVar()
        self.check_training_var.set(1)
        self.check_var_container.append(self.check_training_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_TRAINING, font=self.default_font, variable=self.check_training_var, command=self.toggle_all_off, bg=self.bg).grid(row=2, column=0,
                                                                                                                                                                        padx=int(self.default_size/2))
        self.check_training_details_var = tk.IntVar()
        self.check_training_details_var.set(0)
        self.check_var_container.append(self.check_training_details_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_TRAINING_DETAILS, font=self.default_font, variable=self.check_training_details_var, command=self.toggle_all_off,
                       bg=self.bg).grid(row=2, column=1,padx=int(self.default_size / 2))

        self.check_facts_var = tk.IntVar()
        self.check_facts_var.set(0)
        self.check_var_container.append(self.check_facts_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_FACTS, font=self.default_font, variable=self.check_facts_var, command=self.toggle_all_off,
                       bg=self.bg).grid(row=2, column=2, padx=int(self.default_size / 2))

        self.checkbox_frame2 = tk.Frame(self.root, bg=self.bg)
        self.checkbox_frame2.grid(row=4, column=1, columnspan=2, padx=self.default_size)

        self.check_table_headings_var = tk.IntVar()
        self.check_table_headings_var.set(0)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_TABLE_HEADINGS, font=self.default_font, variable=self.check_table_headings_var, bg=self.bg).grid(row=0, column=0,
                                                                                                                                                                       padx=int(self.default_size / 2))
        self.check_sum_values_var = tk.IntVar()
        self.check_sum_values_var.set(1)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_SUM_VALUES, font=self.default_font, variable=self.check_sum_values_var, bg=self.bg).grid(row=0, column=1,
                                                                                                                                                              padx=int(self.default_size / 2))
        self.check_complete_gesundheit_var = tk.IntVar()
        self.check_complete_gesundheit_var.set(0)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_COMPLETE_GESUNDHEIT, font=self.default_font, variable=self.check_complete_gesundheit_var, bg=self.bg).grid(row=1, column=0,
                                                                                                                                                                        padx=int(self.default_size / 2))

        self.b_button_frame = tk.Frame(self.root, bg=self.bg)
        self.b_button_frame.grid(row=5, column=1, columnspan=2, padx=self.default_size)

        self.description_button = tk.Button(self.b_button_frame, text=lang.DESCRIPTION, command=self.clipboard_description, bg=self.bg, state=tk.DISABLED)
        self.description_button.grid(row=0, column=0, padx=int(self.default_size / 2), pady=int(self.default_size / 2))
        self.interactive_elements.append(self.description_button)

        self.note_button = tk.Button(self.b_button_frame, text=lang.NOTE, command=self.clipboard_note, bg=self.bg, state=tk.DISABLED)
        self.note_button.grid(row=0, column=1, padx=int(self.default_size / 2), pady=int(self.default_size / 2))
        self.interactive_elements.append(self.note_button)

        self.listing_frame = tk.Frame(self.root, bg=self.bg)
        self.listing_frame.grid(row=6, column=1, columnspan=2, padx=self.default_size, pady=self.default_size)

        tk.Label(self.listing_frame, text=lang.LISTING_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size/2))

        self.listing_files, self.listing_names = self.get_listing_files()
        self.option_var = tk.StringVar()
        self.option_var.set(self.listing_names[0])  # default value
        tk.OptionMenu(self.listing_frame, self.option_var, *self.listing_names).grid(row=1, column=0, padx=int(self.default_size / 2))

        self.listing_button = tk.Button(self.listing_frame, text=lang.LISTING_BUTTON, command=self.make_listing, bg=self.bg)
        self.listing_button.grid(row=1, column=1, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.listing_button)

        self.left_frame = tk.Frame(self.root, bg=self.bg)
        self.left_frame.grid(row=7, column=0)

        tk.Label(self.left_frame, text=lang.OWN_AREA, font=self.bold_font, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size / 2))
        self.own_button = tk.Button(self.left_frame, text=lang.LOAD_OWN_BUTTON, command=self.load_own_ponies, bg=self.bg)
        self.own_button.grid(row=0, column=1, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.own_button)
        self.care_all_button = tk.Button(self.left_frame, text=lang.CARE_OWN_BUTTON, command=self.care_all, bg=self.bg)
        self.care_all_button.grid(row=0, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.care_all_button)
        self.train_all_button = tk.Button(self.left_frame, text=lang.TRAIN_OWN_BUTTON, command=self.train_all, bg=self.bg)
        self.train_all_button.grid(row=0, column=3, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.train_all_button)
        self.beauty_all_button = tk.Button(self.left_frame, text=lang.BEAUTY_OWN_BUTTON, command=self.beauty_all, bg=self.bg)
        self.beauty_all_button.grid(row=0, column=4, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.beauty_all_button)

        self.individual_frame = tk.Frame(self.root, bg=self.bg)
        self.individual_frame.grid(row=7, column=1, columnspan=2)
        self.train_individual_button = tk.Button(self.individual_frame, text=lang.TRAIN_INDIVIDUAL_BUTTON, command=self.train_this, bg=self.bg, state=tk.DISABLED)
        self.train_individual_button.grid(row=7, column=1, padx=self.default_size, pady=self.default_size)
        self.interactive_elements.append(self.train_individual_button)

        self.care_individual_button = tk.Button(self.individual_frame, text=lang.CARE_INDIVIDUAL_BUTTON, command=self.care_this, bg=self.bg, state=tk.DISABLED)
        self.care_individual_button.grid(row=7, column=2, padx=self.default_size, pady=self.default_size)
        self.interactive_elements.append(self.care_individual_button)

        self.beauty_individual_button = tk.Button(self.individual_frame, text=lang.BEAUTY_INDIVIDUAL_BUTTON, command=self.beauty_this, bg=self.bg, state=tk.DISABLED)
        self.beauty_individual_button.grid(row=7, column=3, padx=self.default_size, pady=self.default_size)
        self.interactive_elements.append(self.beauty_individual_button)

        self.exterior_frame = tk.Frame(self.root, bg=self.bg)
        self.exterior_frame.grid(row=8, column=1, columnspan=2, padx=self.default_size, pady=self.default_size)

        tk.Label(self.exterior_frame, text=lang.EXTERIEUR_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size/2))
        self.quick_display_var = tk.IntVar()
        self.quick_display_var.set(0)
        tk.Checkbutton(self.exterior_frame, variable=self.quick_display_var, font=self.default_font, text=lang.QUICK_DISPLAY, bg=self.bg).grid(row=0, column=1, padx=(int(self.default_size/2)))

        self.horse_pages = [lang.HORSE_PAGE_TRADE, lang.HORSE_PAGE_STUD, lang.HORSE_PAGE_ALL]
        self.horse_page_type_var = tk.StringVar()
        self.horse_page_type_var.set(self.horse_pages[0])  # default value
        tk.OptionMenu(self.exterior_frame, self.horse_page_type_var, *self.horse_pages).grid(row=0, column=2, padx=int(self.default_size / 2))

        races = list(self.extractor.race_dict.keys())
        self.race_var = tk.StringVar()
        self.race_var.set(races[0])  # default value
        tk.OptionMenu(self.exterior_frame, self.race_var, *races).grid(row=0, column=3, columnspan=2, padx=int(self.default_size / 2))

        self.listing_names_plus_ext = list(self.listing_names)
        self.listing_names_plus_ext.append('Exterieur')
        self.market_listing_var = tk.StringVar()
        self.market_listing_var.set(self.listing_names_plus_ext[-1])
        tk.OptionMenu(self.exterior_frame, self.market_listing_var, *self.listing_names_plus_ext).grid(row=1, column=1, padx=int(self.default_size / 2))

        sort_bys = list(self.extractor.sort_by_dict.keys())
        self.sort_by_var = tk.StringVar()
        self.sort_by_var.set(sort_bys[7])  # default value
        tk.OptionMenu(self.exterior_frame, self.sort_by_var, *sort_bys).grid(row=1, column=0, padx=int(self.default_size / 2))

        self.ext_button = tk.Button(self.exterior_frame, text=lang.EXTERIEUR_BUTTON, command=self.exterior_search, bg=self.bg)
        self.ext_button.grid(row=1, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.ext_button)

        tk.Label(self.exterior_frame, text=lang.N_PAGES_LABEL, font=self.default_font, bg=self.bg).grid(row=1, column=3, padx=int(self.default_size / 2))

        n_pages_list = ['1', '2', '3', '4', '5', '6']
        self.n_pages_var = tk.StringVar()
        self.n_pages_var.set(n_pages_list[0])  # default value
        tk.OptionMenu(self.exterior_frame, self.n_pages_var, *n_pages_list).grid(row=1, column=4)

        self.cache_frame = tk.Frame(self.root, bg=self.bg)
        self.cache_frame.grid(row=8, column=0, padx=self.default_size, pady=self.default_size)

        tk.Label(self.cache_frame, text=lang.CACHE_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=1, padx=int(self.default_size / 2))
        self.halloween_button = tk.Button(self.cache_frame, text='Halloween Start', command=self.halloween_toggle, bg=self.bg)
        self.halloween_button.grid(row=1, column=3, padx=self.default_size)
        self.all_cache_button = tk.Button(self.cache_frame, text=lang.CACHE_ALL_BUTTON, command=lambda: self.del_cache('all'), bg=self.bg)
        self.all_cache_button.grid(row=1, column=0, padx=int(self.default_size / 2))
        self.not_owned_cache_button = tk.Button(self.cache_frame, text=lang.CACHE_NOT_OWNED_BUTTON, command=lambda: self.del_cache('not_owned'), bg=self.bg)
        self.not_owned_cache_button.grid(row=1, column=1, padx=int(self.default_size / 2))
        self.this_cache_button = tk.Button(self.cache_frame, text=lang.CACHE_THIS_BUTTON, command=lambda: self.del_cache('this'), bg=self.bg, state=tk.DISABLED)
        self.this_cache_button.grid(row=1, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.all_cache_button)
        self.interactive_elements.append(self.not_owned_cache_button)
        self.interactive_elements.append(self.this_cache_button)

        self.interactive_states = [0]*len(self.interactive_elements)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not self.check_for_updates():
            self.start_poll_on_boot()
            self.root.mainloop()

    def check_for_updates(self):
        check_path = Path('./pony_gui.py')
        if check_path.exists():    # if we are in script directory (means we are executing the script and not the exe), don't do anything
            # print('we are in script dir, return')
            return False
        remote_version_url = 'https://raw.githubusercontent.com/RichardGoerler/ponyspiel/master/build_count.py'
        r = requests.get(remote_version_url, allow_redirects=True)
        f = r.text.splitlines()[0]
        v = int(f.split('=')[1].strip())
        # print('v', v, 'self.__version__', self.__version__)
        if v > self.__version__:
            if tk.YES == messagebox.askyesno(title=lang.UPDATE_TITLE, message=lang.UPDATE_MESSAGE):
                remote_updater_url = 'https://github.com/RichardGoerler/ponyspiel/raw/master/dist/updater.exe'
                r = requests.get(remote_updater_url, allow_redirects=True)
                p = Path('./updater.exe')
                with open(p, 'wb') as f:
                    f.write(r.content)
                updater_path = Path('./updater.exe').absolute()
                _ = subprocess.Popen([str(updater_path)], startupinfo=subprocess.CREATE_NEW_CONSOLE).pid
                return True
        return False

    def beauty_all(self):
        too_many_redirects_ids = []
        own_file = Path('./owned_ponies')
        all_ids = []
        if own_file.is_file():
            with open(own_file, 'r') as f:
                all_ids = f.read().split()
        beauty_ids = []
        beauty_file = Path('./beauty_ponies')
        if beauty_file.is_file():
            with open(beauty_file, 'r') as f:
                beauty_ids = f.read().split()
        own_beauty = [pid for pid in all_ids if pid in beauty_ids]
        if len(own_beauty) > 0:
            progressbar = ProgressWindow(self.root, self, title=lang.BEAUTY_OWN_BUTTON, steps=len(own_beauty), initial_text=str(own_beauty[0]))
            for pid in own_beauty:
                if not self.extractor.login_beauty(pid):
                    if 'too many redirects' in self.extractor.log[-1].lower():
                        too_many_redirects_ids.append(pid)
                    else:
                        messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                        return
                progressbar.step(str(pid))

        if len(too_many_redirects_ids) > 0:
            message = lang.REDIRECTS_WARNING_MESSAGE
            for pid in too_many_redirects_ids:
                message += ('\n' + str(pid))
            messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def beauty_this(self):
        pid = self.id_label.cget('text').strip()
        if len(pid) > 0 and pid.isnumeric():
            if not self.extractor.login_beauty(pid):
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                return

    def train_all(self):
        too_many_redirects_ids = []
        own_file = Path('./owned_ponies')
        all_ids = []
        if own_file.is_file():
            with open(own_file, 'r') as f:
                all_ids = f.read().split()
        no_train_ids = []
        no_train_file = Path('./no_train')
        if no_train_file.is_file():
            with open(no_train_file, 'r') as f:
                no_train_ids = f.read().split()
        train_ids = [pid for pid in all_ids if pid not in no_train_ids]
        progressbar = ProgressWindow(self.root, self, title=lang.TRAIN_OWN_BUTTON, steps=len(train_ids), initial_text=str(train_ids[0]))
        for this_id in train_ids:
            if not self.extractor.train_pony(this_id):
                if 'too many redirects' in self.extractor.log[-1].lower():
                    too_many_redirects_ids.append(this_id)
                    progressbar.step(str(this_id))
                    continue
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                progressbar.close()
                return
            # check whether pony is fully trained
            if len(self.extractor.log) > 0 and this_id in self.extractor.log[-1] and 'fully trained' in self.extractor.log[-1] and self.extractor.parser.charakter_training_headings[0] in self.extractor.parser.charakter_training_values.keys():
                flag = True
                for k in self.extractor.parser.charakter_training_values.keys():
                    if self.extractor.parser.charakter_training_values[k] < self.extractor.parser.charakter_training_max[k]:
                        flag = False
                        break
                if flag:
                    no_train_ids.append(this_id)
                    with open(no_train_file, 'w') as f:
                        for pid in no_train_ids:
                            f.write(str(pid) + '\n')
            progressbar.step(str(this_id))

        if len(too_many_redirects_ids) > 0:
            message = lang.REDIRECTS_WARNING_MESSAGE
            for pid in too_many_redirects_ids:
                message += ('\n' + str(pid))
            messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def train_this(self):
        id = self.id_label.cget('text').strip()
        if len(id) > 0 and id.isnumeric():
            if not self.extractor.train_pony(id):
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                return

    def care_all(self):
        too_many_redirects_ids = []
        own_file = Path('./owned_ponies')
        all_ids = []
        if own_file.is_file():
            with open(own_file, 'r') as f:
                all_ids = f.read().split()
        progressbar = ProgressWindow(self.root, self, title=lang.CARE_OWN_BUTTON, steps=len(all_ids), initial_text=str(all_ids[0]))
        for this_id in all_ids:
            if not self.extractor.care_pony(this_id):
                if 'too many redirects' in self.extractor.log[-1].lower():
                    too_many_redirects_ids.append(this_id)
                else:
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                    progressbar.close()
                    return
            progressbar.step(str(this_id))

        if len(too_many_redirects_ids) > 0:
            message = lang.REDIRECTS_WARNING_MESSAGE
            for pid in too_many_redirects_ids:
                message += ('\n' + str(pid))
            messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def care_this(self):
        id = self.id_label.cget('text').strip()
        if len(id) > 0 and id.isnumeric():
            if not self.extractor.care_pony(id):
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                return

    def halloween_toggle(self):
        if self.halloween_process is None:
            # driver_path = Path('./chromedriver.exe').absolute()
            # self.chromedriver_process = subprocess.Popen([str(driver_path)], startupinfo=subprocess.CREATE_NEW_CONSOLE)

            self.halloween_process = multiprocessing.Process(target=halloween_poll)
            self.halloween_process.start()

            self.halloween_button['text'] = 'Halloween Stopp'
        else:
            self.halloween_process.terminate()
            self.halloween_process = None
            # if self.chromedriver_process is not None:
            #     self.chromedriver_process.terminate()
            self.halloween_button['text'] = 'Halloween Start'

    def start_poll_on_boot(self):
        poll_file = Path('./avail_poll')
        if poll_file.is_file():
            with open(poll_file, 'r') as f:
                self.poll_ids = f.read().split()
            for pid in self.poll_ids:
                t = multiprocessing.Process(target=poll_function, args=(pid,))
                self.poll_processes.append(t)
                t.start()
            if len(self.poll_ids) > 0:
                self.poll_checkbutton.configure(font=self.small_bold_font)
            else:
                self.poll_checkbutton.configure(font=self.small_font)

        if HALLOWEEN:
            # driver_path = Path('./chromedriver.exe').absolute()
            # self.chromedriver_process = subprocess.Popen([str(driver_path)], startupinfo=subprocess.CREATE_NEW_CONSOLE)

            self.halloween_process = multiprocessing.Process(target=halloween_poll)
            self.halloween_process.start()

    def _update_poll_file(self):
        poll_file = Path('./avail_poll')
        if len(self.poll_ids) > 0:
            with open(poll_file, 'w') as f:
                for pid in self.poll_ids:
                    f.write(str(pid) + '\n')
        elif poll_file.exists():
            poll_file.unlink()

    def on_closing(self):
        if self.halloween_process is not None:
            self.halloween_process.terminate()
        # if self.chromedriver_process is not None:
        #     self.chromedriver_process.terminate()
        running_proc_indices = [i for i in range(len(self.poll_processes)) if self.poll_processes[i].is_alive()]
        self.poll_processes = [self.poll_processes[i] for i in running_proc_indices]
        self.poll_ids = [self.poll_ids[i] for i in running_proc_indices]
        self._update_poll_file()
        if len(self.poll_ids) > 0:
            if messagebox.askokcancel(lang.QUIT_HEADING, lang.QUIT_TEXT):
                for p in self.poll_processes:
                    p.terminate()
                self.root.destroy()
        else:
            self.root.destroy()

    def deckstation_poll_toggle(self):
        pid = self.id_label.cget('text')
        pollvar = self.check_poll_var.get()
        if pollvar == 1 and pid not in self.poll_ids:
            t = multiprocessing.Process(target=poll_function, args=(pid, ))
            self.poll_ids.append(pid)
            self.poll_processes.append(t)
            self._update_poll_file()
            t.start()
        if pollvar == 0 and pid in self.poll_ids:
            ind = self.poll_ids.index(pid)
            self.poll_processes[ind].terminate()
            del self.poll_processes[ind]
            del self.poll_ids[ind]
            self._update_poll_file()
        if len(self.poll_ids) > 0:
            self.poll_checkbutton.configure(font=self.small_bold_font)
        else:
            self.poll_checkbutton.configure(font=self.small_font)

    def deckstation_poll_cancel_all(self):
        if len(self.poll_processes) > 0:
            if messagebox.askokcancel(lang.POLL_CANCEL_HEADING, lang.POLL_CANCEL_TEXT):
                for p in self.poll_processes:
                    p.terminate()
                self.poll_ids = []
                self._update_poll_file()
                self.poll_checkbutton.configure(font=self.small_font)
                self.check_poll_var.set(0)

    def disable_buttons(self):
        for i, el in enumerate(self.interactive_elements):
            self.interactive_states[i] = el['state']
            el['state'] = tk.DISABLED

    def enable_buttons(self):
        for i, el in enumerate(self.interactive_elements):
            el['state'] = self.interactive_states[i]

    def clipboard_note(self):
        pony_id_str = self.id_label.cget('text')
        if not self.extractor.get_pony_info(int(pony_id_str)):
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
            return
        p = self.extractor.parser
        athmos = ['Halle', 'Arena', 'draußen']
        gelaeuf = ['Sand', 'Gras', 'Erde', 'Schnee', 'Lehm', 'Späne']
        haerte = ['sehr weich', 'weich', 'mittel', 'hart', 'sehr hart']
        lists = [athmos, gelaeuf, haerte]
        note = ''
        for li, l in enumerate(lists):
            for i, k in enumerate(l):
                note += '{:s}: {:d}'.format(k, p.ausbildung_max[k])
                if i < len(l)-1:
                    note += ' | '
            if li < len(lists)-1:
                note += '\n'

        self.text_to_clipboard(note)

    def clipboard_description(self):
        pony_id_str = self.id_label.cget('text')
        if not self.extractor.get_pony_info(int(pony_id_str)):
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
            return
        this_race = self.extractor.parser.facts_values['Rasse']
        file_list, name_list = self.get_description_files()
        if this_race not in name_list:
            this_race = 'default'
        f_index = name_list.index(this_race)
        load_file = file_list[f_index]
        with open(load_file, 'r', encoding='utf-8') as f:
            config = f.read().splitlines()
        prefixes = []
        props = []
        p = self.extractor.parser
        valid_keys = [p.gesundheit_headings, p.charakter_headings, p.exterieur_headings, p.ausbildung_headings, p.gangarten_headings, p.dressur_headings,
                      p.springen_headings, p.military_headings, p.western_headings, p.rennen_headings, p.fahren_headings, p.facts_headings, ['Gesamtpotenzial']]

        for l in config:
            colon_split = l.split(':')
            front_split = colon_split[0].split('_')
            prefix = ''
            if len(front_split) > 1:
                prefix = front_split[0].strip() + ' '
                part = [front_split[1].strip()]
            else:
                part = [front_split[0].strip()]
            if len(colon_split) > 1:
                part.append([attr.strip() for attr in colon_split[1].split(',')])
            else:
                part_ok = False  # Anything that is not in the parser keys does not make sense here. facts are additionaly allowed if we are after the divider (which means no average has to be computed)
                for keylist in valid_keys:
                    if part[0] in keylist:
                        part_ok = True
                if not part_ok:
                    continue
            props.append(part)
            prefixes.append(prefix)

        description_string = ''
        for it, (pref, prop) in enumerate(zip(prefixes, props)):
            if 0 < it:
                description_string += ' | '
            if len(prop) == 1:
                if prop[0] == 'Gesamtpotenzial':
                    val, norm = self.extractor.parser.training_max['Gesamtpotenzial'], 1
                else:
                    val, norm = self.get_prop_value_and_count(prop[0])
            else:
                norm = len(prop[1])
                val = 0
                for subprop in prop[1]:
                    val += self.get_prop_value(subprop)
            if isinstance(val, (int, float)):
                normval = val / norm
                textval = str(round(normval, 1)) if normval <= 100 else str(int(normval)) # if Gesamtpotenzial ( > 100), show as integer
            else:
                textval = val
            description_string += (pref + textval)

        self.text_to_clipboard(description_string)

    def text_to_clipboard(self, text):
        try:
            win32clipboard.OpenClipboard(0)
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_TEXT)
        finally:
            win32clipboard.CloseClipboard()

    def get_prop_value_and_count(self, prop, parser=None):
        if parser is None:
            p = self.extractor.parser
        else:
            p = parser
        l = [p.facts_values, p.gesundheit_values, p.charakter_values, p.exterieur_values, p.ausbildung_max, p.gangarten_max, p.dressur_max,
             p.springen_max, p.military_max, p.western_max, p.rennen_max, p.fahren_max]
        for l_list in l:
            if prop in list(l_list.keys()):
                return (l_list[prop], len(l_list)-1)
        return (0,1)

    def get_prop_value(self, prop, parser=None):
        if parser is None:
            p = self.extractor.parser
        else:
            p = parser
        l = [p.gesundheit_values, p.charakter_values, p.exterieur_values, p.ausbildung_max, p.gangarten_max, p.dressur_max,
             p.springen_max, p.military_max, p.western_max, p.rennen_max, p.fahren_max]
        for l_list in l:
            if prop in list(l_list.keys()):
                return l_list[prop]
        return 0

    def exterior_search(self):
        sort_by_key = self.sort_by_var.get()
        sort_by_value = self.extractor.sort_by_dict[sort_by_key]
        self.quick_display = bool(self.quick_display_var.get())
        self.exterior_search_ids = self.extractor.browse_horses(self.horse_pages.index(self.horse_page_type_var.get()), race=self.race_var.get(), sort_by=sort_by_value, pages=int(self.n_pages_var.get()), quick=self.quick_display)
        if self.exterior_search_ids == False:
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
        else:
            self.exterior_search_requested = True
            self.disable_buttons()
            _ = ListingWindow(self.root, self, lang.LISTING_TITLE)

    def del_cache(self, type='this'):
        pony_id_str = self.id_label.cget('text')
        if type == 'this':
            if len(pony_id_str) < 2:
                pony_id_str = self.extractor.pony_id
            self.extractor.del_pony_cache(pony_id_str)
            self.this_cache_button['state'] = tk.DISABLED
        elif type == 'not_owned':
            own_file = Path('./owned_ponies')
            own_ids = []
            if own_file.is_file():
                with open(own_file, 'r') as f:
                    own_ids = f.read().split()
            self.extractor.del_pony_cache_all(exclude=own_ids)
            if pony_id_str not in own_ids:
                self.this_cache_button['state'] = tk.DISABLED
        elif type == 'all':
            self.extractor.del_pony_cache_all()
            self.this_cache_button['state'] = tk.DISABLED
        elif str(type).isnumeric():
            # here we suppose argument is the id
            self.extractor.del_pony_cache(str(type))
            if self.this_cache_button['text'] == str(type):
                but_ind = self.interactive_elements.index(self.this_cache_button)
                self.interactive_states[but_ind] = tk.DISABLED
        else:
            pass


    def load_own_ponies(self):
        horse_ids = self.extractor.get_own_ponies()
        if horse_ids == False:
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
        else:
            own_file = Path('./owned_ponies')
            with open(own_file, 'w') as f:
                for id in horse_ids:
                    f.write(str(id) + '\n')

    def make_listing(self):
        self.exterior_search_requested = False
        self.disable_buttons()
        _ = ListingWindow(self.root, self, lang.LISTING_TITLE)

    def get_description_files(self):
        p = Path('./descriptions/').glob('**/*')
        file_list = [f for f in p if f.is_file()]
        name_list = [f.stem for f in file_list]
        if len(file_list) == 0:
            return ([''], [''])
        else:
            return (file_list, name_list)
        pass

    def get_listing_files(self):
        p = Path('./listings/').glob('**/*')
        file_list = [f for f in p if f.is_file()]
        name_list = [f.stem for f in file_list]
        if len(file_list) == 0:
            return ([''], [''])
        else:
            return (file_list, name_list)
        pass

    def update_owned(self):
        pony_id_str = self.id_label.cget('text')
        own_file = Path('./owned_ponies')
        content = []
        if own_file.is_file():
            with open(own_file, 'r') as f:
                content = f.read().split()
        if self.check_ownership_var.get():
            # We want to add id to the file if it does not exist
            if not pony_id_str in content:
                content.append(pony_id_str)
        else:
            # We want to delete id from the file if it does exist
            if pony_id_str in content:
                content.remove(pony_id_str)
        with open(own_file, 'w') as f:
            for c in content:
                f.write(c + '\n')

    def is_owned(self):
        pony_id_str = self.id_label.cget('text')
        own_file = Path('./owned_ponies')
        content = []
        if own_file.is_file():
            with open(own_file, 'r') as f:
                content = f.read().split()
        return pony_id_str in content

    def toggle_all_var(self):
        target = self.check_all_var.get()
        for v in self.check_var_container:
            v.set(target)

    def toggle_all_off(self):
        target = 1
        for v in self.check_var_container:
            if not v.get():
                target = 0
        self.check_all_var.set(target)

    def request(self):
        pony_id = int(self.id_spin.get())
        self.this_cache_button['state'] = tk.NORMAL
        self.this_cache_button.configure(text=str(pony_id))
        if not self.extractor.get_pony_info(pony_id):
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
            return
        if not self.extractor.request_pony_images():
            messagebox.showerror(title=lang.PONY_IMAGE_ERROR, message=self.extractor.log[-1])
        else:
            self.banner = ImageTk.PhotoImage(self.extractor.pony_image)
            self.banner_label.configure(image=self.banner)
        self.name_label.configure(text=self.extractor.parser.name)
        self.id_label.configure(text=str(pony_id))
        self.export_button['state'] = tk.NORMAL
        self.description_button['state'] = tk.NORMAL
        self.note_button['state'] = tk.NORMAL
        self.ownership_checkbutton['state'] = tk.NORMAL
        self.train_individual_button['state'] = tk.NORMAL
        self.care_individual_button['state'] = tk.NORMAL
        self.beauty_individual_button['state'] = tk.NORMAL
        running_proc_indices = [i for i in range(len(self.poll_processes)) if self.poll_processes[i].is_alive()]
        self.poll_processes = [self.poll_processes[i] for i in running_proc_indices]
        self.poll_ids = [self.poll_ids[i] for i in running_proc_indices]
        self.poll_checkbutton['state'] = tk.NORMAL
        if str(pony_id) in self.poll_ids:
            self.check_poll_var.set(1)
        else:
            self.check_poll_var.set(0)
        self.check_ownership_var.set(int(self.is_owned()))
        qual = self.extractor.get_pony_quality()
        self.quality_label.configure(text='Qualität: {:.0f}%'.format(qual*100))

    def enter_login(self):
        _ = LoginWindow(self.root, self, lang.LOGIN_TITLE)
        if len(self.user) > 0 and len(self.pw) > 0:
            self.request_button.configure(state=tk.NORMAL)

    def export(self):
        id_text = self.id_label.cget('text')
        if int(self.id_label.cget('text')) != self.extractor.pony_id:
            self.id_spin.delete(0, "end")
            self.id_spin.insert(0, id_text)
            # print('requesting again')
            self.request()
        write_dict = dict()
        delete_first = not self.check_sum_values_var.get()   # Sum value is always the first value
        if self.check_gesundheit_var.get():
            keys = list(self.extractor.parser.gesundheit_values.keys())
            if not self.check_complete_gesundheit_var.get():
                # If we only want the first two entries
                keys = keys[:3]
            keys = keys[int(delete_first):]
            write_dict.update({k: self.extractor.parser.gesundheit_values[k] for k in keys})
        if self.check_charakter_var.get():
            write_dict.update({k: self.extractor.parser.charakter_values[k] for k in list(self.extractor.parser.charakter_values.keys())[int(delete_first):]})
        if self.check_exterieur_var.get():
            write_dict.update({k: self.extractor.parser.exterieur_values[k] for k in list(self.extractor.parser.exterieur_values.keys())[int(delete_first):]})
        if self.check_training_var.get():
            write_dict.update({k: self.extractor.parser.training_max[k] for k in list(self.extractor.parser.training_max.keys())[int(delete_first):]})
        if self.check_training_details_var.get():
            write_dict.update({**{k: self.extractor.parser.ausbildung_max[k] for k in list(self.extractor.parser.ausbildung_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.gangarten_max[k] for k in list(self.extractor.parser.gangarten_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.dressur_max[k] for k in list(self.extractor.parser.dressur_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.springen_max[k] for k in list(self.extractor.parser.springen_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.military_max[k] for k in list(self.extractor.parser.military_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.western_max[k] for k in list(self.extractor.parser.western_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.rennen_max[k] for k in list(self.extractor.parser.rennen_max.keys())[int(delete_first):]},
                               **{k: self.extractor.parser.fahren_max[k] for k in list(self.extractor.parser.fahren_max.keys())[int(delete_first):]},
                               })
        if self.check_facts_var.get():
            write_dict.update({k: self.extractor.parser.facts_values[k] for k in list(self.extractor.parser.facts_values.keys())[int(delete_first):]})
        write_headers = write_dict.keys()

        # if self.export_format_var.get() == 1:  # csv
        #     if self.export_method_var.get() == 1: # file
        #         filename = filedialog.asksaveasfilename(initialdir="/", initialfile="{}-{}.csv".format(self.extractor.pony_id, self.extractor.parser.name),
        #                                                 title=lang.SELECT_FILE, filetypes=[(lang.CSV_FILES, "*.csv")])
        #         if not filename.endswith('.csv'):
        #             filename = filename + '.csv'
        #         file_path = Path(filename)
        #         try:
        #             with open(file_path, 'w') as csvfile:
        #                 writer = csv.DictWriter(csvfile, fieldnames=write_headers)
        #                 if self.check_table_headings_var.get():
        #                     writer.writeheader()
        #                 writer.writerow(write_dict)
        #         except IOError:
        #             messagebox.showerror(title=lang.IO_ERROR, message=lang.CSV_WRITE_ERROR)
        #     else: # clipboard
        #         messagebox.showerror(title=lang.NOT_SUPPORTED_ERROR, message=lang.NOT_SUPPORTED_ERROR)

        # else: # html
            # example_data = "<tr><th>Firstname</th><th>Lastname</th><th>Age</th></tr><tr><td>Jill</td><td>Smith</td><td>50</td></tr>"
        html_string = "\n\n<table>"
        if self.check_table_headings_var.get():
            html_string += "<tr>"
            # html_string += "<col><tr>"
            for header in write_headers:
                html_string += "<td>{}</td>\n\n".format(header)
            html_string += "</tr>"
        html_string += "<tr>"
        for value in write_dict.values():
            html_string += "<td>{}</td>\n\n".format(value)
        if self.check_table_headings_var.get():
            pass
        html_string += "</tr><!--EndFragment--></table>   "
        # if self.export_method_var.get() == 1:  # file
        #     filename = filedialog.asksaveasfilename(initialdir="/", initialfile="{}-{}.html".format(self.extractor.pony_id, self.extractor.parser.name),
        #                                             title=lang.SELECT_FILE, filetypes=[(lang.HTML_FILES, "*.html")])
        #     if not filename.endswith('.html'):
        #         filename = filename + '.html'
        #     file_path = Path(filename)
        #     try:
        #         with open(file_path, 'w') as htmlfile:
        #             htmlfile.write(html_string)
        #     except IOError:
        #         messagebox.showerror(title=lang.IO_ERROR, message=lang.HTML_WRITE_ERROR)
        # else: # clipboard
        html_clipboard.PutHtml(html_string)
            # with open("clip.txt", "w") as f:
            #     f.write(html_clipboard.GetHtml())


    def dims_by_scale(self, scale):
        if hasattr(scale, '__iter__'):
            return [int(el * sc) for el, sc in zip(self.screen_resolution,scale)]
        return [int(el * scale) for el in self.screen_resolution]

if __name__ == '__main__':
    multiprocessing.freeze_support()
    ponyGUI = PonyGUI()
