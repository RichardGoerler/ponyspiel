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
import win32clipboard
import webbrowser

import lang
import stats_parser
import html_clipboard
import dialog

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
        if not self.gui.exterior_search_requested:
            own_file = Path('./owned_ponies')
            all_ids = []
            if own_file.is_file():
                with open(own_file, 'r') as f:
                    all_ids = f.read().split()
        else:
            all_ids = self.gui.exterior_search_ids

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
        if not lname == lang.EXTERIEUR_LISTING:
            lfile = self.gui.listing_files[self.gui.listing_names.index(lname)]
            with open(lfile, 'r', encoding='utf-8') as f:
                config = f.read().splitlines()
            if self.gui.exterior_search_requested:
                config[0] = self.gui.race_var.get()   # race to filter for always equals the race the market search was filtered for
                config.append('=')
                config.append('id')
        else:
            config = [self.gui.race_var.get(), 'Exterieur: Haltung, Ausdruck, Kopf, Halsansatz, Rückenlinie, Beinstellung', '=', 'id']
        races = [r.strip() for r in config[0].split(',')]
        if 'Alle'.strip("'") in races:
            races = list(self.gui.extractor.race_dict.keys())
            config.append('Rasse')
        self.props = []
        divider_found = False
        self.additional = []
        p = self.gui.extractor.parser
        valid_keys = [p.gesundheit_headings, p.charakter_headings, p.exterieur_headings, p.ausbildung_headings, p.gangarten_headings, p.dressur_headings,
                      p.springen_headings, p.military_headings, p.western_headings, p.rennen_headings, p.fahren_headings, ['id']]
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

        self.button_frame = tk.Frame(master, bg=self.gui.bg)
        self.button_frame.grid(row=0, column=0, padx=self.def_size, pady=self.def_size)
        self.sex_all_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_ALL, font=self.def_font, command=lambda: self.filter_sex(0), bg=self.gui.bg)
        self.sex_all_button.grid(row=0, column=0, padx=int(self.def_size / 2))
        self.sex_female_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_FEMALE, font=self.def_font, command=lambda: self.filter_sex(1), bg=self.gui.bg)
        self.sex_female_button.grid(row=0, column=1, padx=int(self.def_size / 2))
        self.sex_male_button = tk.Button(self.button_frame, text=lang.LISTING_SEX_MALE, font=self.def_font, command=lambda: self.filter_sex(2), bg=self.gui.bg)
        self.sex_male_button.grid(row=0, column=2, padx=int(self.def_size / 2))

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

        self.objects = []
        self.data_table = []
        self.sex = []
        self.banners = []
        self.images = []
        for id in all_ids:
            progressbar.step(str(id))
            if not self.gui.extractor.get_pony_info(id):
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                progressbar.close()
                return
            if self.gui.extractor.parser.facts_values['Rasse'] in races:
                self.gui.race_ids.append(id)
                if not self.gui.extractor.request_pony_images():
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                    im = self.gui.imorg
                else:
                    im = self.gui.extractor.pony_image
                object_row = []
                table_row = []
                dim = self.gui.dims_by_scale(0.001 * self.def_size)[0]
                fac = float(dim) / im.size[0]
                dim2 = int(im.size[1] * fac)
                im = im.resize((dim, dim2), Image.ANTIALIAS)
                self.images.append(im)
                self.banners.append(ImageTk.PhotoImage(im))
                object_row.append(tk.Label(self.table_frame, image=self.banners[-1], bg=self.gui.bg))
                object_row.append(tk.Label(self.table_frame, text=self.gui.extractor.parser.name[:self.MAX_LEN_NAME], font=self.bol_font, bg=self.gui.bg))
                table_row.append(self.gui.extractor.parser.name)

                age = self.get_age()
                table_row.append(age)
                pony_months = age.days
                pony_years = pony_months // 12
                pony_months %= 12
                object_row.append(tk.Label(self.table_frame, text='{}/{}'.format(pony_years, pony_months), font=self.def_font, bg=self.gui.bg))

                table_row.append(self.gui.extractor.parser.training_max['Gesamtpotenzial'])
                object_row.append(tk.Label(self.table_frame, text=table_row[-1], font=self.bol_font, bg=self.gui.bg))

                avg_done = False
                for prop_list in [self.props, self.additional]:
                    for prop in prop_list:
                        if prop[0] == 'id':
                            normval = textval = id
                            object_row.append(tk.Label(self.table_frame, text=str(textval), font=self.def_font, bg=self.gui.bg, cursor="hand2"))
                            object_row[-1].bind("<Button-1>", lambda e, url=self.gui.extractor.base_url + 'horse.php?id={}'.format(id): webbrowser.open(url))
                        else:
                            if len(prop) == 1:
                                val, norm = self.gui.get_prop_value_and_count(prop[0])
                            else:
                                norm = len(prop[1])
                                val = 0
                                for subprop in prop[1]:
                                    val += self.gui.get_prop_value(subprop)
                            if isinstance(val, (int, float)):
                                normval = val/norm
                                textval = str(round(normval, 1))
                            else:
                                normval = textval = val
                            object_row.append(tk.Label(self.table_frame, text=textval, font=self.def_font, bg=self.gui.bg))
                        table_row.append(normval)

                    for key in self.max_prop_dict.keys():
                        this_val = self.gui.get_prop_value(key)
                        if self.max_prop_dict[key] < this_val:
                            self.max_prop_dict[key] = this_val

                    # total average - only done once
                    if not avg_done:
                        table_row.append(sum(table_row[NUM_NON_USER_PROP:])/(len(table_row)-NUM_NON_USER_PROP))
                        object_row.append(tk.Label(self.table_frame, text=str(round(table_row[-1], 1)), font=self.bol_font, bg=self.gui.bg))
                        avg_done = True

                self.objects.append(object_row)
                self.data_table.append(table_row)

                if self.gui.extractor.parser.facts_values['Geschlecht'] == 'Stute':
                    self.sex.append(1)
                else:
                    self.sex.append(2)

                if pony_years < 3:
                    for el in object_row:
                        el.configure(fg='red')

        for hdi, hd in enumerate(self.data_headers):
            if hd in self.max_prop_dict.keys():
                self.header_max_labels[hdi].configure(text=str(self.max_prop_dict[hd]))

        progressbar.step(lang.PROGRESS_DRAWING_SCALING)
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

    def get_age(self):
        birthday_split = self.gui.extractor.parser.facts_values['Geburtstag'].split('-')
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
        self.button_frame.grid(row=0, column=0, padx=self.def_size, pady=self.def_size)
        self.sex_all_button.grid(row=0, column=0, padx=int(self.def_size / 2))
        self.sex_female_button.grid(row=0, column=1, padx=int(self.def_size / 2))
        self.sex_male_button.grid(row=0, column=2, padx=int(self.def_size / 2))
        for ii, im in enumerate(self.images):
            dim = self.gui.dims_by_scale(0.001 * self.def_size)[0]
            fac = float(dim) / im.size[0]
            dim2 = int(im.size[1] * fac)
            im = im.resize((dim, dim2), Image.ANTIALIAS)
            self.banners[ii] = ImageTk.PhotoImage(im)
            self.objects[ii][0].configure(image=self.banners[ii])
        self.table_frame.grid(row=1, column=0, padx=self.def_size)
        for ci, el in enumerate(self.header_objects):
            el.grid(row=1, column=ci + 1, padx=int(self.def_size / 2))
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
        table_sorted = []
        sex_sorted = []
        for id in sorted_idx:
            objects_sorted.append(self.objects[id])
            table_sorted.append(self.data_table[id])
            sex_sorted.append(self.sex[id])
        self.objects = objects_sorted
        self.data_table = table_sorted
        self.sex = sex_sorted
        self.draw_objects()

class LoginWindow(dialog.Dialog):
    def header(self, master):
        pass

    def body(self, master):
        try:
            with open('login', 'r') as f:
                user_loaded = f.readline().strip()
                pw_loaded = f.readline().strip()
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

    def apply(self):
        self.gui.user = self.user_var.get().strip()
        self.gui.pw = self.pw_var.get().strip()
        with open('login', 'w') as f:
            f.write('{}\n{}'.format(self.gui.user, self.gui.pw))


class PonyGUI:
    def __init__(self):
        self.extractor = stats_parser.PonyExtractor()
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.user = ''
        self.pw = ''
        self.bg = "#EDEEF3"
        self.screenwidth = self.root.winfo_screenwidth()
        self.screenheight = self.root.winfo_screenheight()
        self.screen_resolution = [self.screenwidth, self.screenheight]
        self.hdfactor = self.screenheight/1080.
        self.default_size = int(round(15*self.hdfactor))
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(size=self.default_size)
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

        self.own_button = tk.Button(self.root, text=lang.OWN_BUTTON, command=self.load_own_ponies, bg=self.bg)
        self.own_button.grid(row=7, column=0, padx=self.default_size)
        self.interactive_elements.append(self.own_button)

        self.exterior_frame = tk.Frame(self.root, bg=self.bg)
        self.exterior_frame.grid(row=8, column=1, columnspan=2, padx=self.default_size, pady=self.default_size)

        tk.Label(self.exterior_frame, text=lang.EXTERIEUR_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=0, columnspan=2, padx=int(self.default_size/2))

        self.horse_pages = ['Pferdehandel', 'Deckstation']
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

        n_pages_list = ['1', '2', '3', '4']
        self.n_pages_var = tk.StringVar()
        self.n_pages_var.set(n_pages_list[0])  # default value
        tk.OptionMenu(self.exterior_frame, self.n_pages_var, *n_pages_list).grid(row=1, column=4)

        self.cache_frame = tk.Frame(self.root, bg=self.bg)
        self.cache_frame.grid(row=8, column=0, padx=self.default_size, pady=self.default_size)

        tk.Label(self.cache_frame, text=lang.CACHE_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=1, padx=int(self.default_size / 2))
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

        self.root.mainloop()

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

    def get_prop_value_and_count(self, prop):
        p = self.extractor.parser
        l = [p.facts_values, p.gesundheit_values, p.charakter_values, p.exterieur_values, p.ausbildung_max, p.gangarten_max, p.dressur_max,
             p.springen_max, p.military_max, p.western_max, p.rennen_max, p.fahren_max]
        for l_list in l:
            if prop in list(l_list.keys()):
                return (l_list[prop], len(l_list)-1)
        return (0,1)

    def get_prop_value(self, prop):
        p = self.extractor.parser
        l = [p.gesundheit_values, p.charakter_values, p.exterieur_values, p.ausbildung_max, p.gangarten_max, p.dressur_max,
             p.springen_max, p.military_max, p.western_max, p.rennen_max, p.fahren_max]
        for l_list in l:
            if prop in list(l_list.keys()):
                return l_list[prop]
        return 0

    def exterior_search(self):
        sort_by_key = self.sort_by_var.get()
        sort_by_value = self.extractor.sort_by_dict[sort_by_key]
        self.exterior_search_ids = self.extractor.browse_horses(self.horse_page_type_var.get() == 'Deckstation', race=self.race_var.get(), sort_by=sort_by_value, pages=int(self.n_pages_var.get()))
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
        else:
            self.extractor.del_pony_cache_all()
            self.this_cache_button['state'] = tk.DISABLED


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
        self.this_cache_button['state'] = tk.NORMAL
        self.this_cache_button.configure(text=str(pony_id))
        self.ownership_checkbutton['state'] = tk.NORMAL
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
    ponyGUI = PonyGUI()
