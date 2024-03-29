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
import os
import sys
import subprocess
import requests
import traceback

import lang
import stats_parser
import html_clipboard
import dialog
import build_count

HALLOWEEN = False

SCHECKUNGEN = ['tovero', 'overo', 'maximum tobiano', 'tobiano', 'splashed white',
               'roan spotted blanket', 'spotted blanket', 'blanket', 'few spot leopard', 'leopard',
               'snowcap', 'snowflake', 'mottled', 'varnish roan', 'rabicano', 'birdcatcher spots',
               'brindle', 'reverse dapples', 'macchiato', 'minimalsabino', 'sabino']

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(".")

    return base_path / relative_path


class ProgressWindow(tk.Toplevel):
    def __init__(self, parent, gui, title=lang.PROGRESS, steps=100, initial_text='', shutdown_button=True):

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

        self.gui.shutdown_var.set(0)
        if shutdown_button:
            self.gui.checkbox_shutdown.grid(row=2, column=0, columnspan=3)

    def set_steps(self, n_steps):
        self.steps = n_steps
        self.stepsize = self.max_value/self.steps

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
            if self.gui.shutdown_var.get() == 1:
                subprocess.call(["shutdown", "-f", "-s", "-t", "2"])
                # print('shutdown')
        self.gui.root.update()

    def set_text_only(self, text):
        self.pb_text.configure(text=self.pad_str(text))
        self.gui.root.update()

    def close(self):
        self.destroy()
        
    def destroy(self):
        self.gui.checkbox_shutdown.grid_forget()
        super(ProgressWindow, self).destroy()


def argsort(seq, ascending=False):
    #http://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python/3382369#3382369
    #by unutbu
    if ascending:
        return sorted(range(len(seq)), key=seq.__getitem__)
    else:
        return sorted(range(len(seq)), key=seq.__getitem__)[::-1]


class StudfeeWindow(dialog.Dialog):
    def body(self, master):
        self.pony_id = self.gui.stud_id
        self.stud_file = Path('./studs')
        self.stud_lines = []
        if self.stud_file.is_file():
            with open(self.stud_file, 'r') as f:
                self.stud_lines = f.read().splitlines()
        self.stud_fees_quick_file = Path('./stud_fees_quick')
        self.stud_fees_quick = []
        if self.stud_fees_quick_file.is_file():
            with open(self.stud_fees_quick_file, 'r') as f:
                for fee_l in f.read().splitlines():
                    try:
                        self.stud_fees_quick.append(int(fee_l))
                    except ValueError:
                        continue
        self.gui.stud_fee = 0
        del_ind = None
        for li, l in enumerate(self.stud_lines):
            spl = l.split()
            if int(spl[0]) == int(self.pony_id):
                self.gui.stud_fee = int(spl[1])
                del_ind = li
                break
        if del_ind is not None:
            del self.stud_lines[del_ind]
        if len(self.stud_lines) > 0 and len(self.stud_lines[-1]) < 4:
            del self.stud_lines[-1]
        tk.Label(master, bg=self.gui.bg, text=lang.STUDFEE_LABEL).grid(row=0, column=0, padx=int(self.gui.default_size/2))
        self.spin = tk.Spinbox(master, width=6, from_=0, to=999999, bg=self.gui.bg)
        self.spin.delete(0, "end")
        self.spin.insert(0, self.gui.stud_fee)
        self.quick_frame = tk.Frame(master, bg=self.gui.bg)
        for i, fee_v in enumerate(self.stud_fees_quick):
            tk.Button(self.quick_frame, bg=self.gui.bg, text=str(fee_v), command=lambda x=fee_v: self.ok_val(x)).grid(row=i // 3, column=int(i % 3))
        self.quick_frame.grid(row=1, column=0, columnspan=2, pady=(self.gui.default_size))
        self.spin.grid(row=0, column=1, padx=int(self.gui.default_size/2))

    def header(self, master):
        pass

    def ok_val(self, val):
        self.spin.delete(0, "end")
        print(val)
        self.spin.insert(0, str(val))
        self.ok()

    def apply(self):
        self.gui.stud_fee = int(self.spin.get())
        if self.gui.stud_fee > 0:
            self.stud_lines.append('{} {}'.format(self.pony_id, self.gui.stud_fee))
        with open(self.stud_file, 'w') as f:
            for l in self.stud_lines:
                f.write(str(l) + '\n')


class FilterWindow(dialog.Dialog):
    def body(self, master):
        self.preset_file = Path('./filter_presets')
        filter_preset_lines = []
        if self.preset_file.is_file():
            with self.preset_file.open('r') as f:
                filter_preset_lines = f.read().splitlines()
        self.filter_presets = {'': ''}
        for l in filter_preset_lines:
            spl = l.split(':')
            if len(spl) > 1:
                self.filter_presets[spl[0]] = spl[1]
        self.preset_var = tk.StringVar()
        self.preset_var.set('')  # default value
        tk.Label(master, bg=self.gui.bg, text=lang.FILTER_WINDOW_TEXT, wraplength=450, justify=tk.LEFT).grid(row=0, column=0, padx=int(self.gui.default_size/2))
        self.entry = tk.Entry(master, bg=self.gui.bg)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.gui.listing_filter)
        self.entry.grid(row=1, column=0, padx=int(self.gui.default_size/2), pady=int(self.gui.default_size/2))
        tk.Label(master, bg=self.gui.bg, text=lang.FILTER_PRESETS_TEXT, wraplength=450, justify=tk.LEFT).grid(row=2, column=0, padx=int(self.gui.default_size / 2))
        tk.OptionMenu(master, self.preset_var, *self.filter_presets.keys(), command=lambda v: self.set_entry(self.filter_presets[v])).grid(row=3, column=0)

    def header(self, master):
        pass

    def apply(self):
        self.gui.listing_filter = self.entry.get()

    def set_entry(self, v):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, v)
        
        
class AdvancedFilterWindow(dialog.Dialog):
    def body(self, master):
        self.parent.advanced_filter_var.set(0)    # will be set if successful
        self.attribute_vars = []
        self.checkvars = []  # for Fellfarbe
        self.attribute_names = ([p[0] for p in self.parent.props] + [lang.LISTING_HEADER_AVERAGE] + [p[0] for p in self.parent.additional])
        tk.Label(master, bg=self.gui.bg, font=self.parent.bol_font, text=lang.ADV_FILTER_ALL).grid(row=0, column=1, padx=int(self.gui.default_size/2))
        tk.Label(master, bg=self.gui.bg, font=self.parent.bol_font, text=lang.ADV_FILTER_STUD).grid(row=0, column=2, padx=int(self.gui.default_size/2))
        tk.Label(master, bg=self.gui.bg, font=self.parent.bol_font, text=lang.ADV_FILTER_MARE).grid(row=0, column=3, padx=int(self.gui.default_size/2))
        for i, nam in enumerate(self.attribute_names):
            tk.Label(master, bg=self.gui.bg, font=self.parent.def_font, text=nam).grid(row=i+1, column=0, padx=int(self.gui.default_size/2))
            snumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            vars = []
            for j in range(3):
                numvar = tk.StringVar()
                numvar.set(snumbers[0])  # default value
                if j == 0:
                    om = tk.OptionMenu(master, numvar, *snumbers, command=lambda v, row_i=i: self.numvar_sel(v, row_i))
                else:
                    om = tk.OptionMenu(master, numvar, *snumbers)
                om['bg'] = self.gui.bg
                om.grid(row=i+1, column=j+1)
                vars.append(numvar)
            self.attribute_vars.append(vars)
            if nam == 'Fellfarbe':
                for pi, prop in enumerate(self.attribute_names[:len(self.parent.props)+1]):
                    checkvar = tk.IntVar()
                    checkvar.set(0)
                    tk.Checkbutton(master, text=prop, variable=checkvar, bg=self.gui.bg).grid(row=i+1, column=5+pi)
                    self.checkvars.append(checkvar)

        self.radio_frame = tk.Frame(master, bg=self.gui.bg)
        self.radio_frame.grid(row=len(self.attribute_names)+1, column=0, columnspan=4)
        tk.Label(self.radio_frame, bg=self.gui.bg, font=self.parent.bol_font, text=lang.ADV_FILTER_RADIO_TITLE).grid(row=0, column=0)
        self.display_selected_var = tk.IntVar()
        self.display_selected_var.set(0)
        tk.Radiobutton(self.radio_frame, font=self.parent.def_font, text=lang.ADV_FILTER_RADIO_HIDE, variable=self.display_selected_var, value=0, bg=self.gui.bg).grid(row=1, column=0)
        tk.Radiobutton(self.radio_frame, font=self.parent.def_font, text=lang.ADV_FILTER_RADIO_DISPLAY, variable=self.display_selected_var, value=1, bg=self.gui.bg).grid(row=2, column=0)

    def numvar_sel(self, value, row_i):
        val = int(value)
        row = self.attribute_vars[row_i]
        new_val = (val-1) // 2
        stud_var = row[1]
        mare_var = row[2]
        if not int(stud_var.get()):
            stud_var.set(str(new_val))
        if not int(mare_var.get()):
            mare_var.set(str(new_val))

    def header(self, master):
        pass

    def apply(self):
        data = self.parent.data_table
        filt = [True] * len(data)
        for ivar, vars in enumerate(self.attribute_vars):
            column_data = [row[ivar+self.parent.num_non_user_prop] for row in data]
            column_data_studs = [column_data[i] for i in range(len(column_data)) if self.parent.sex[i] == 2]
            stud_indices = [i for i in range(len(column_data)) if self.parent.sex[i] == 2]
            column_data_mares = [column_data[i] for i in range(len(column_data)) if self.parent.sex[i] == 1]
            mare_indices = [i for i in range(len(column_data)) if self.parent.sex[i] == 1]
            num_all = int(vars[0].get())
            num_studs = int(vars[1].get())
            num_mares = int(vars[2].get())
            if self.attribute_names[ivar] == 'Fellfarbe':
                column_data = list(map(lambda x: x.lower(), column_data))
                for scheck in SCHECKUNGEN:
                    column_data = list(map(lambda x: x.replace(scheck, ''), column_data))
                column_data = list(map(lambda x: x.strip(), column_data))
                check_list = [ch.get() for ch in self.checkvars]
                for ci, ch in enumerate(check_list):
                    if ch:
                        inds_to_drop = self.fellfarbe_func(fellfarbe_data=column_data, n_all=num_all, n_studs=num_studs, n_mares=num_mares, ivar=ci)
                        for drop_id in inds_to_drop:
                            filt[drop_id] = False
            else:
                sortind = argsort(column_data)
                sortind_studs = argsort(column_data_studs)
                sortind_mares = argsort(column_data_mares)
                for i_all in range(num_all):
                    filt[sortind[i_all]] = False
                for i_all in range(num_studs):
                    filt[stud_indices[sortind_studs[i_all]]] = False
                for i_all in range(num_mares):
                    filt[mare_indices[sortind_mares[i_all]]] = False
        if self.display_selected_var.get():   # reverse if selected should be displayed instead of hidden
            filt = [not fi for fi in filt]
        self.parent.advanced_filter_var.set(1)   # success
        self.parent.filter = filt

    def fellfarbe_func(self, fellfarbe_data, n_all, n_studs, n_mares, ivar):
        var_data = [row[ivar+self.parent.num_non_user_prop] for row in self.parent.data_table]
        identity_indices = list(range(len(var_data)))
        var_data_studs = [var_data[i] for i in range(len(var_data)) if self.parent.sex[i] == 2]
        stud_indices = [i for i in range(len(var_data)) if self.parent.sex[i] == 2]
        var_data_mares = [var_data[i] for i in range(len(var_data)) if self.parent.sex[i] == 1]
        mare_indices = [i for i in range(len(var_data)) if self.parent.sex[i] == 1]
        sortind = argsort(var_data)
        sortind_studs = argsort(var_data_studs)
        sortind_mares = argsort(var_data_mares)
        # sortind is the argsorted list, but sortind_studs and sortind_mares are both shorter than sortind
        # if i is an index from sortind_studs, then real_i = stud_indices[i] is the index of the respective pony in
        # var_data. Same for sortind_mares and mare_indices.
        inds_to_drop = []
        for sortind_this, indices_this, n_this in zip([sortind, sortind_studs, sortind_mares],
                                                      [identity_indices, stud_indices, mare_indices],
                                                      [n_all, n_studs, n_mares]):
            if n_this == 0:
                # No pony will ever be added to the list so we can skip that
                continue
            dat_dict = {}
            # keys will be fellfarben and values will be the occurence counts. When long as the occurrence count is
            # smaller or equal to the respective n (value from OptionMenu), the index of the occurrence will be added to
            # the inds_to_drop list, which is returned in the end.
            for i in sortind_this:
                real_i = indices_this[i]
                dat = fellfarbe_data[real_i]
                dat_dict[dat] = dat_dict[dat] + 1 if dat in dat_dict else 1
                if dat_dict[dat] <= n_this:
                    inds_to_drop.append(real_i)

        return inds_to_drop


class ListingWindow(dialog.Dialog):
    def cancel(self, event=None):
        self.gui.enable_buttons()
        dialog.Dialog.cancel(self, event)

    def header(self, master):
        pass

    def body(self, master):
        quick_display = self.gui.quick_display
        no_images = not self.gui.listing_images_var.get()
        self.gui.quick_display = False
        too_many_redirects_ids = []
        self.stable_list = [lang.ALL_STABLES_NAME]
        if not self.gui.exterior_search_requested:
            all_ids, all_races, all_stables = read_own_file()
            for stab in all_stables:
                if stab not in self.stable_list:
                    self.stable_list.append(stab)

            exclude_ids = []
            exclude_file = Path('./listing_exclude')
            if exclude_file.is_file():
                with open(exclude_file, 'r') as f:
                    exclude_ids = f.read().split()

            not_exclude_list_indices = [i for i in range(len(all_ids)) if all_ids[i] not in exclude_ids]
            all_ids = [all_ids[i] for i in not_exclude_list_indices]
            all_races = [all_races[i] for i in not_exclude_list_indices]
            all_stables = [all_stables[i] for i in not_exclude_list_indices]
        else:
            all_ids = self.gui.exterior_search_ids
            all_stables = [lang.UNKNOWN_STABLES_NAME] * len(all_ids)

        beauty_file = Path('./beauty_ponies')
        self.beauty_ids = []
        if beauty_file.is_file():
            with open(beauty_file, 'r') as f:
                self.beauty_ids = f.read().split()

        stud_file = Path('./studs')
        stud_lines = []
        if stud_file.is_file():
            with open(stud_file, 'r') as f:
                stud_lines = f.read().splitlines()
        self.studs = [l.split()[0] for l in stud_lines]

        flag_file = Path('./flags')
        flag_lines = []
        if flag_file.is_file():
            with open(flag_file, 'r') as f:
                flag_lines = f.read().splitlines()
        self.flags = [l.split()[0] for l in flag_lines]

        self.discipline_ids, self.disciplines = read_train_file()
        self.fully_trained_file = Path('./fully_trained')
        self.fully_trained_ids = []
        if self.fully_trained_file.is_file():
            with open(self.fully_trained_file, 'r') as f:
                self.fully_trained_ids = f.read().split()

        self.last_column_sorted = -1   # index of the column that was last sorted. If -1, column sort will be always descending, if >= 0, sort of that specific column will be descending

        progressbar = ProgressWindow(self, self.gui, steps=len(all_ids)+3, initial_text=lang.PROGRESS_READING_CONFIG, shutdown_button=False)
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
        self.bol_font_strike = font.Font(family=self.gui.default_font['family'], size=int(self.def_size*0.8), weight='bold', overstrike=True)
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
        self.filter = []
        self.stables_match = []
        self.stable_filter = []
        self.filter_row = -1
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
        self.advanced_filter_var = tk.IntVar()
        self.advanced_filter_var.set(0)
        self.advanced_filter_checkbutton = tk.Checkbutton(self.button_frame, text=lang.CHECK_ADV_FILTER, font=self.def_font, variable=self.advanced_filter_var, command=self.toggle_advanced_filter, bg=self.gui.bg)
        self.advanced_filter_checkbutton.grid(row=0, column=4, padx=int(self.def_size / 2))
        self.reverse_filter_button = tk.Button(self.button_frame, text=lang.ADV_FILTER_REVERSE, font=self.def_font, command=self.reverse_advanced_filter, bg=self.gui.bg)
        self.stable_selected_var = tk.StringVar()
        self.stable_selected_var.set(self.stable_list[0])
        self.stable_selector = tk.OptionMenu(self.button_frame, self.stable_selected_var, *self.stable_list, command=self.set_stable_filter)
        self.stable_selector.config(bg=self.gui.bg, font=self.def_font)
        self.stable_selector.grid(row=0, column=6, padx=int(self.def_size / 2))

        self.gui.race_ids = []
        self.table_frame = tk.Frame(master, bg=self.gui.bg)
        self.table_frame.grid(row=1, column=0, padx=self.def_size)
        self.header_objects = [tk.Button(self.table_frame, text=lang.LISTING_HEADER_NAME[:self.MAX_LEN_NAME], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_NAME: self.sort(p), bg=self.gui.bg)]
        self.header_objects[-1].bind("<Button-3>", lambda e, p=lang.LISTING_HEADER_NAME: self.filter_function_wrapper(e, p))
        self.header_objects_copy = [tk.Button(self.table_frame, text=lang.LISTING_HEADER_NAME[:self.MAX_LEN_NAME], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_NAME: self.sort(p), bg=self.gui.bg)]
        self.header_objects_copy2 = [tk.Button(self.table_frame, text=lang.LISTING_HEADER_NAME[:self.MAX_LEN_NAME], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_NAME: self.sort(p), bg=self.gui.bg)]
        self.header_max_labels = [tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg)]
        self.data_headers = [lang.LISTING_HEADER_NAME]
        self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AGE[:self.MAX_LEN_PROP], command=lambda p=lang.LISTING_HEADER_AGE: self.sort(p), bg=self.gui.bg))
        self.header_objects[-1].bind("<Button-3>", lambda e, p=lang.LISTING_HEADER_AGE: self.filter_function_wrapper(e, p))
        self.header_objects_copy.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AGE[:self.MAX_LEN_PROP], command=lambda p=lang.LISTING_HEADER_AGE: self.sort(p), bg=self.gui.bg))
        self.header_objects_copy2.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AGE[:self.MAX_LEN_PROP], command=lambda p=lang.LISTING_HEADER_AGE: self.sort(p), bg=self.gui.bg))
        self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
        self.data_headers.append(lang.LISTING_HEADER_AGE)
        self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_POTENTIAL[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_POTENTIAL: self.sort(p), bg=self.gui.bg))
        self.header_objects[-1].bind("<Button-3>", lambda e, p=lang.LISTING_HEADER_POTENTIAL: self.filter_function_wrapper(e, p))
        self.header_objects_copy.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_POTENTIAL[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_POTENTIAL: self.sort(p), bg=self.gui.bg))
        self.header_objects_copy2.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_POTENTIAL[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_POTENTIAL: self.sort(p), bg=self.gui.bg))
        self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
        self.data_headers.append(lang.LISTING_HEADER_POTENTIAL)
        if not self.gui.exterior_search_requested:
            self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_TRAIN_STATE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_TRAIN_STATE: self.sort(p), bg=self.gui.bg))
            self.header_objects[-1].bind("<Button-3>", lambda e, p=lang.LISTING_HEADER_TRAIN_STATE: self.filter_function_wrapper(e, p))
            self.header_objects_copy.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_TRAIN_STATE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_TRAIN_STATE: self.sort(p), bg=self.gui.bg))
            self.header_objects_copy2.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_TRAIN_STATE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_TRAIN_STATE: self.sort(p), bg=self.gui.bg))
            self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
            self.data_headers.append(lang.LISTING_HEADER_TRAIN_STATE)
            self.num_non_user_prop = 4 # number of entries in the data table that is not defined by the user (and which the average is calculated over). Does not include the image!
        else:
            self.num_non_user_prop = 3
        avg_done = False
        for prop_list in [self.props, self.additional]:
            for prop in prop_list:
                self.header_objects.append(tk.Button(self.table_frame, text=prop[0][:self.MAX_LEN_PROP], command=lambda p=prop[0]: self.sort(p), bg=self.gui.bg))
                self.header_objects[-1].bind("<Button-3>", lambda e, p=prop[0]: self.filter_function_wrapper(e, p))
                self.header_objects_copy.append(tk.Button(self.table_frame, text=prop[0][:self.MAX_LEN_PROP], command=lambda p=prop[0]: self.sort(p), bg=self.gui.bg))
                self.header_objects_copy2.append(tk.Button(self.table_frame, text=prop[0][:self.MAX_LEN_PROP], command=lambda p=prop[0]: self.sort(p), bg=self.gui.bg))
                self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
                self.data_headers.append(prop[0])
            if not avg_done:
                self.header_objects.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AVERAGE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_AVERAGE: self.sort(p), bg=self.gui.bg))
                self.header_objects[-1].bind("<Button-3>", lambda e, p=lang.LISTING_HEADER_AVERAGE: self.filter_function_wrapper(e, p))
                self.header_objects_copy.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AVERAGE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_AVERAGE: self.sort(p), bg=self.gui.bg))
                self.header_objects_copy2.append(tk.Button(self.table_frame, text=lang.LISTING_HEADER_AVERAGE[:self.MAX_LEN_PROP], font=self.bol_font, command=lambda p=lang.LISTING_HEADER_AVERAGE: self.sort(p), bg=self.gui.bg))
                self.header_max_labels.append(tk.Label(self.table_frame, text='', font=self.def_font, bg=self.gui.bg))
                self.data_headers.append(lang.LISTING_HEADER_AVERAGE)
                self.BOLD_COLUMNS = [0, 2, len(self.data_headers) - 1]
                avg_done = True
        for ci, el in enumerate(self.header_max_labels):
            el.grid(row=0, column=ci+1, padx=int(self.def_size / 2))
        for ci, el in enumerate(self.header_objects):
            el.grid(row=1, column=ci+1, padx=int(self.def_size / 2))   # ci + 1 because the image does not have a corresponding header!

        races_numbers = [self.gui.extractor.race_dict[r] for r in races]
        for idx, id in enumerate(all_ids):
            progressbar.step(str(id))
            if quick_display:
                parser = stats_parser.FakeParser(self.gui.extractor.images[idx], self.gui.extractor.ponies[idx])
                if self.gui.filter_pre_selected:
                    x = parser.facts_values['Fellfarbe']
                    try:
                        if not eval(self.gui.listing_filter):
                            continue
                    except:
                        traceback.print_exc()
                        messagebox.showerror(title=lang.FILTER_ERROR_TITLE, message=lang.FILTER_ERROR_TEXT)
                        progressbar.close()
                        return
            else:
                if not self.gui.exterior_search_requested and all_races[idx] > 0:
                    if all_races[idx] not in races_numbers:
                        continue
                if not self.gui.extractor.get_pony_info(id):
                    if 'too many redirects' in self.gui.extractor.log[-1].lower():
                        too_many_redirects_ids.append(id)
                        continue
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                    progressbar.close()
                    return
                parser = self.gui.extractor.parser
                if not self.gui.exterior_search_requested:
                    all_races[idx] = self.gui.extractor.race_dict[parser.facts_values['Rasse']]
            if parser.facts_values['Rasse'] in races:
                self.gui.race_ids.append(id)
                if quick_display:
                    self.cache_exists_for_row.append(False)   # No relatives display if we are in quick mode
                else:
                    self.cache_exists_for_row.append(self.gui.extractor.cache_exists)
                if quick_display or no_images:
                    im = self.gui.imorg
                elif not self.gui.extractor.request_pony_images(urls=parser.image_urls, pony_id=id):
                    messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.gui.extractor.log[-1])
                    im = self.gui.imorg
                else:
                    im = self.gui.extractor.pony_image
                object_row = []
                table_row = []
                table_row_sum = []

                if id in self.discipline_ids:
                    dis_idx = self.discipline_ids.index(id)
                    dis_str = self.disciplines[dis_idx]
                    dis_list = [int(s) for s in dis_str]
                else:
                    dis_list = self.gui.default_disciplines

                dim = self.gui.dims_by_scale(0.001 * self.def_size)[0]
                fac = float(dim) / im.size[0]
                dim2 = int(im.size[1] * fac)
                im = im.resize((dim, dim2), Image.ANTIALIAS)
                self.images.append(im)
                self.banners.append(ImageTk.PhotoImage(im))
                object_row.append(tk.Label(self.table_frame, image=self.banners[-1], bg=self.gui.bg, cursor="hand2"))
                object_row[-1].bind("<Button-1>", lambda e, pid=id: self.del_cache(e, pid))
                object_row[-1].bind("<Button-2>", lambda e, hid=id: self.gui.clipboard_description(hid))
                object_row[-1].bind("<Button-3>", lambda e, pid=id: self.toggle_beauty(e, pid))
                object_row[-1].configure(borderwidth=1*int(id in self.beauty_ids), relief="solid")
                object_row.append(tk.Label(self.table_frame, text=parser.name[:self.MAX_LEN_NAME], font=self.bol_font, bg=self.gui.bg, cursor="hand2"))
                object_row[-1].bind("<Button-1>", lambda e, url=self.gui.extractor.base_url + 'horse.php?id={}'.format(id): webbrowser.open(url))
                object_row[-1].bind("<Button-3>", lambda e, hid=id: self.mark_relatives(hid))
                object_row[-1].bind("<Button-2>", lambda e, hid=id: self.enter_stud_fee(e, hid))
                object_row[-1].configure(borderwidth=1 * int(id in self.studs), relief="solid")
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
                object_row[-1].bind("<Button-1>", lambda e, pid=id: self.toggle_flag(e, pid))
                object_row[-1].configure(borderwidth=1 * int(id in self.flags), relief="solid")
                table_row.append(age)
                table_row_sum.append(age)

                table_row.append(parser.training_max['Gesamtpotenzial'])
                table_row_sum.append(parser.training_max['Gesamtpotenzial'])

                fo = self.bol_font
                bw = 0
                if len(dis_list) == 0:
                    fo = self.bol_font_strike
                elif stats_parser.PonyExtractor.KOMPLETT in dis_list:
                    bw = 1

                object_row.append(tk.Label(self.table_frame, text=table_row[-1], font=fo, bg=self.gui.bg, relief="solid", borderwidth=bw))
                object_row[-1].bind("<Button-1>", lambda e, pid=id, dis=-1: self.toggle_training(e, pid, dis))

                if not self.gui.exterior_search_requested:
                    try:
                        parser.train_state
                    except AttributeError:
                        parser.train_state = None

                    if parser.train_state is None:
                        self.gui.extractor.train_pony(pony_id=id, disciplines=dis_list, refresh_state_only=True)
                    if parser.train_state is None:
                        state_str = '?'
                    elif parser.train_state < 0:
                        state_str = 'N'
                    elif parser.train_state <= 1:
                        state_str = '{:d}%'.format(int(100 * parser.train_state))
                    else:
                        state_str = 'C{:d}%'.format(int(100 * parser.train_state - 100))
                    table_row.append(state_str)
                    table_row_sum.append(state_str)

                    object_row.append(tk.Label(self.table_frame, text=table_row[-1], font=self.def_font, bg=self.gui.bg))

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
                            if len(prop) == 1 and prop[0] in stats_parser.PonyExtractor.TRAINING_CONSTANT_DICT.keys():
                                this_discipline = stats_parser.PonyExtractor.TRAINING_CONSTANT_DICT[prop[0]]
                                if this_discipline in dis_list:
                                    object_row.append(tk.Label(self.table_frame, text=textval, font=self.def_font, bg=self.gui.bg, relief="solid", borderwidth=1))
                                else:
                                    object_row.append(tk.Label(self.table_frame, text=textval, font=self.def_font, bg=self.gui.bg, relief="solid", borderwidth=0))
                                object_row[-1].bind("<Button-1>", lambda e, pid=id, dis=this_discipline: self.toggle_training(e, pid, dis))
                            else:
                                object_row.append(tk.Label(self.table_frame, text=textval, font=self.def_font, bg=self.gui.bg))
                                if prop[0] == 'Fellfarbe':
                                    object_row[-1].bind("<Button-1>", lambda e, val=textval: self.fellfarbe_equal_filter(val))
                                    object_row[-1].bind("<Button-3>", lambda e, val=textval: self.fellfarbe_contains_filter(val))
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
                        table_row.append(sum(table_row[self.num_non_user_prop:])/(len(table_row)-self.num_non_user_prop))
                        table_row_sum.append(sum(table_row[self.num_non_user_prop:]) / (len(table_row) - self.num_non_user_prop))
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
                self.filter.append(True)
                self.stable_filter.append(True)
                self.stables_match.append(all_stables[idx])

        # update owned ponies race entries
        own_file = Path('./owned_ponies')
        end_ids, end_races, end_stables = read_own_file()
        lines = []
        for pid_loaded, race_loaded, stab_loaded in zip(end_ids, end_races, end_stables):
            if pid_loaded in all_ids:
                this_ind = all_ids.index(pid_loaded)
                new_race = all_races[this_ind]
            else:
                new_race = race_loaded
            lines.append(pid_loaded + ' ' + str(new_race) + ' ' + str(stab_loaded))
        with open(own_file, 'w') as f:
            for l in lines:
                f.write(l + '\n')

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

    def toggle_flag(self, e, pid):
        flag_file = Path('./flags')
        lab = e.widget
        flag_lines = []
        if flag_file.exists():
            with open(flag_file, 'r') as f:
                flag_lines = f.read().splitlines()
        if lab['borderwidth'] == 1:
            lab['borderwidth'] = 0
            fi = flag_lines.index(str(pid))
            del flag_lines[fi]
        else:
            lab['borderwidth'] = 1
            flag_lines.append(str(pid))
        with open(flag_file, 'w') as f:
            f.write('\n'.join(flag_lines))

    def fellfarbe_equal_filter(self, val):
        col_to_apply_on = self.data_headers.index('Fellfarbe')
        button = self.header_objects[col_to_apply_on]
        filt_str = f'x.lower() == "{val.lower()}"'
        self.filter_function(button, 'Fellfarbe', filter_str=filt_str)

    def fellfarbe_contains_filter(self, val):
        col_to_apply_on = self.data_headers.index('Fellfarbe')
        button = self.header_objects[col_to_apply_on]
        val = val.lower()
        for scheck in SCHECKUNGEN:
            val = val.replace(scheck, '')
        val = val.strip()
        filt_str = f'x.lower().startswith("{val}")'
        self.filter_function(button, 'Fellfarbe', filter_str=filt_str)

    def reverse_advanced_filter(self):
        self.filter = [not fi for fi in self.filter]
        self.redraw()

    def toggle_advanced_filter(self):
        if not self.advanced_filter_var.get():  # if advanced filter is now off
            self.filter = [True] * len(self.data_table)
            for but in self.header_objects:
                if but['fg'] == 'red':
                    but.configure(fg='black')
            self.reverse_filter_button.grid_forget()
            self.redraw()
        else:
            _ = AdvancedFilterWindow(self, self.gui, title=lang.CHECK_ADV_FILTER)
            if self.advanced_filter_var.get():  # window will deactivate if not successful
                for but in self.header_objects:
                    if but['fg'] == 'red':
                        but.configure(fg='black')
                self.redraw()
                self.reverse_filter_button.grid(row=0, column=5, padx=int(self.def_size / 2))

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

    def enter_stud_fee(self, event, pid):
        idx = self.gui.race_ids.index(pid)
        age = self.data_table[idx][1]
        pony_months = age.days
        pony_years = pony_months // 12
        if self.sex[idx] == 2 and pony_years >= 3:   # Hengst
            self.gui.stud_id = pid
            lab = event.widget
            _ = StudfeeWindow(self, self.gui, lang.STUDFEE_TITLE)
            if self.gui.stud_fee == 0:
                if lab['borderwidth'] == 1:
                    lab['borderwidth'] = 0
            else:
                if lab['borderwidth'] == 0:
                    lab['borderwidth'] = 1

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

    def toggle_training(self, event, pid, dis):
        lab = event.widget
        if pid not in self.discipline_ids:
            self.discipline_ids.append(pid)
            self.disciplines.append(str(stats_parser.PonyExtractor.GRUNDAUSBILDUNG))
            dis_idx = -1

        else:
            dis_idx = self.discipline_ids.index(pid)
        if dis == -1: # Gesamtpotential
            if lab['borderwidth'] == 1:
                lab['borderwidth'] = 0
                self.disciplines[dis_idx] = str(stats_parser.PonyExtractor.GRUNDAUSBILDUNG)
            elif lab['font'] == str(self.bol_font_strike):
                lab['font'] = self.bol_font
                lab['borderwidth'] = 1
                self.disciplines[dis_idx] = str(stats_parser.PonyExtractor.KOMPLETT)
            else:
                lab['font'] = self.bol_font_strike
                self.disciplines[dis_idx] = ''
        else:
            if lab['borderwidth'] == 0:
                if self.disciplines[dis_idx] != '' and str(stats_parser.PonyExtractor.KOMPLETT) not in self.disciplines[dis_idx]:
                    lab['borderwidth'] = 1
                    self.disciplines[dis_idx] += str(dis)
            else:
                lab['borderwidth'] = 0
                self.disciplines[dis_idx] = self.disciplines[dis_idx].replace(str(dis), '')
        train_dis_file = Path('./train_define')
        with open(train_dis_file, 'w') as f:
            for pi, s in zip(self.discipline_ids, self.disciplines):
                f.write(str(pi) + ' ' + str(s) + '\n')
        if str(pid) in self.fully_trained_ids:
            self.fully_trained_ids.remove(str(pid))
            with open(self.fully_trained_file, 'w') as f:
                for pi in self.fully_trained_ids:
                    f.write(str(pi) + '\n')

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
            if self.sex[ri] in disp_sex and self.filter[ri] and self.stable_filter[ri]:
                for ci, el in enumerate(object_row):
                    rindex = row_index % self.MAXROWS
                    block_id = (row_index // self.MAXROWS)
                    cindex = ci + len(object_row) * block_id
                    if block_id < 4:
                        # only draw four columns
                        el.grid(row=rindex+2, column=cindex, padx=int(self.def_size/2))
                row_index += 1
        if row_index > self.MAXROWS:
            for ci, el in enumerate(self.header_objects_copy):
                el.grid(row=1, column=ci + len(self.header_objects) + 2, padx=int(self.def_size / 2))
        if row_index > 2*self.MAXROWS:
            for ci, el in enumerate(self.header_objects_copy2):
                el.grid(row=1, column=ci + 2*len(self.header_objects) + 3, padx=int(self.def_size / 2))

    def redraw(self):
        self.sum_checkbutton.grid_forget()
        self.sex_all_button.grid_forget()
        self.sex_female_button.grid_forget()
        self.sex_male_button.grid_forget()
        self.advanced_filter_checkbutton.grid_forget()
        self.button_frame.grid_forget()
        self.table_frame.grid_forget()
        for i, h in enumerate(self.header_objects):
            h.grid_forget()
            if i in self.BOLD_COLUMNS:
                h.configure(font=self.bol_font)
            else:
                h.configure(font=self.def_font)
        if len(self.objects) > self.MAXROWS:
            for i, h in enumerate(self.header_objects_copy):
                h.grid_forget()
                if i in self.BOLD_COLUMNS:
                    h.configure(font=self.bol_font)
                else:
                    h.configure(font=self.def_font)
        if len(self.objects) > 2*self.MAXROWS:
            for i, h in enumerate(self.header_objects_copy2):
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
                # if (ci-1) in self.BOLD_COLUMNS:  # ci - 1 because BOLD_COLUMNS is for header columns (without) image. So 1 here corresponds to 0 in BOLD_COLUMNS
                #     el.configure(font=self.bol_font)
                # else:
                #     el.configure(font=self.def_font)
                el.grid_forget()
        self.sex_all_button.configure(font=self.def_font)
        self.sex_female_button.configure(font=self.def_font)
        self.sex_male_button.configure(font=self.def_font)
        self.advanced_filter_checkbutton.configure(font=self.def_font)
        self.reverse_filter_button.configure(font=self.def_font)
        self.button_frame.grid(row=0, column=0, padx=self.def_size, pady=self.def_size, sticky=tk.W)
        self.sum_checkbutton.grid(row=0, column=0, padx=int(self.def_size / 2))
        self.sex_all_button.grid(row=0, column=1, padx=int(self.def_size / 2))
        self.sex_female_button.grid(row=0, column=2, padx=int(self.def_size / 2))
        self.sex_male_button.grid(row=0, column=3, padx=int(self.def_size / 2))
        self.advanced_filter_checkbutton.grid(row=0, column=4, padx=int(self.def_size / 2))
        if self.advanced_filter_var.get():
            self.reverse_filter_button.grid(row=0, column=5, padx=int(self.def_size / 2))
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

    def set_stable_filter(self, e):
        selected_stable = self.stable_selected_var.get()
        if selected_stable == lang.ALL_STABLES_NAME:
            self.stable_filter = [True] * len(self.stables_match)
        else:
            self.stable_filter = [s == selected_stable for s in self.stables_match]
        self.redraw()

    def filter_function_wrapper(self, event, prop):
        self.filter_function(event.widget, prop)

    def filter_function(self, button, prop, filter_str=None):
        show_sum = self.check_sum_var.get()
        data_table = self.data_table_sum if show_sum else self.data_table
        self.gui.listing_filter = ''
        self.filter = [True] * len(data_table)
        col_to_apply_on = self.data_headers.index(prop)
        if self.filter_row == col_to_apply_on:
            self.filter = [True] * len(data_table)   # filter off if clicked the same button again
            self.filter_row = -1
            button.configure(fg='black')
        else:
            for but in self.header_objects:
                if but['fg'] == 'red':
                    but.configure(fg='black')
            if filter_str is None:
                _ = FilterWindow(self, self.gui, lang.FILTER_WINDOW_TITLE)
            else:
                self.gui.listing_filter = filter_str
            if len(self.gui.listing_filter) > 0:
                vals = [row[col_to_apply_on] for row in data_table]
                try:
                    self.filter = eval('[' + self.gui.listing_filter + ' for x in vals]')
                except:
                    traceback.print_exc()
                    messagebox.showerror(title=lang.FILTER_ERROR_TITLE, message=lang.FILTER_ERROR_TEXT)
                    self.gui.listing_filter = ''
                self.filter_row = col_to_apply_on
                button.configure(fg='red')
                self.advanced_filter_var.set(0)
                self.reverse_filter_button.grid_forget()
        self.redraw()

    def filter_sex(self, sex_identifier):
        self.show_sex = sex_identifier
        for ri, object_row in enumerate(self.objects):
            for ci, el in enumerate(object_row):
                el.grid_forget()
            for ci, el in enumerate(self.header_objects_copy2):
                el.grid_forget()
            for ci, el in enumerate(self.header_objects_copy):
                el.grid_forget()
        self.draw_objects()

    def sort(self, prop):
        if self.show_sex == 0:
            disp_sex = [1,2]
        else:
            disp_sex = [self.show_sex]
        row_to_sort_by = self.data_headers.index(prop)
        avgs = [row[row_to_sort_by] for row in self.data_table]
        if self.last_column_sorted == row_to_sort_by:
            sorted_idx = argsort(avgs, ascending=True)
            self.last_column_sorted = -1
        else:
            sorted_idx = argsort(avgs, ascending=False)
            self.last_column_sorted = row_to_sort_by
        for ri, object_row in enumerate(self.objects):
            for ci, el in enumerate(object_row):
                el.grid_forget()
        objects_sorted = []
        object_colors_sorted = []
        table_sorted = []
        table_sorted_sum = []
        sex_sorted = []
        filter_sorted = []
        stable_filter_sorted = []
        stables_match_sorted = []
        race_ids_sorted = []
        cache_exists_for_row_sorted = []
        for pid in sorted_idx:
            objects_sorted.append(self.objects[pid])
            object_colors_sorted.append(self.object_colors[pid])
            table_sorted.append(self.data_table[pid])
            table_sorted_sum.append(self.data_table_sum[pid])
            sex_sorted.append(self.sex[pid])
            filter_sorted.append(self.filter[pid])
            stable_filter_sorted.append(self.stable_filter[pid])
            stables_match_sorted.append(self.stables_match[pid])
            race_ids_sorted.append(self.gui.race_ids[pid])
            cache_exists_for_row_sorted.append(self.cache_exists_for_row[pid])
        self.objects = objects_sorted
        self.object_colors = object_colors_sorted
        self.data_table = table_sorted
        self.data_table_sum = table_sorted_sum
        self.sex = sex_sorted
        self.filter = filter_sorted
        self.stable_filter = stable_filter_sorted
        self.stables_match = stables_match_sorted
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
            tel_loaded = ''
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
    with stats_parser.PonyExtractor() as extractor:
    # extractor = stats_parser.PonyExtractor()
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
                    print('Event-Item gefunden nach {} Aufrufen'.format(found_counter))
                    found_counter = 1
                    # Gefunden!
                    time.sleep(61)
                else:
                    found_counter += 1
                    time.sleep(1)
            url_index += 1
            url_index %= len(URLS)


def read_own_file():
    own_file = Path('./owned_ponies')
    all_ids = []
    all_races = []
    all_stables = []
    if own_file.is_file():
        with open(own_file, 'r') as f:
            lines = f.read().splitlines()
        for l in lines:
            spl = l.split()
            all_ids.append(spl[0])
            if len(spl) > 1:
                all_races.append(int(spl[1]))
            else:
                all_races.append(-1)
            if len(spl) > 2:
                all_stables.append(' '.join(spl[2:]))
            else:
                all_stables.append(lang.UNKNOWN_STABLES_NAME)
    return all_ids, all_races, all_stables

def read_train_file():
    own_file = Path('./train_define')
    train_ids = []
    train_disciplines = []
    if own_file.is_file():
        with open(own_file, 'r') as f:
            lines = f.read().splitlines()
        for l in lines:
            spl = l.split()
            train_ids.append(spl[0])
            if len(spl) > 1:
                train_disciplines.append(spl[1])
            else:
                train_disciplines.append('')
    return train_ids, train_disciplines


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
        self.stud_id = 0
        self.listing_filter = ''
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
        self.bold_strikethrough_font = self.bold_font.copy()
        self.bold_strikethrough_font.configure(overstrike=1)
        self.big_bold_font = self.bold_font.copy()
        self.big_bold_font.configure(size=int(1.33*self.default_size))
        try:
            self.root.iconbitmap("favicon.ico")
        except:
            pass
        self.root.title(lang.MAIN_TITLE)
        self.root.configure(bg=self.bg)
        self.exterior_search_requested = False
        self.filter_pre_selected = False
        self.quick_display = False
        self.exterior_search_ids = []

        self.interactive_elements = []

        # Create gui elements here
        # banner
        self.imorg = Image.open(resource_path("4logo-sm.png"))
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
        om = tk.OptionMenu(self.listing_frame, self.option_var, *self.listing_names)
        om['bg'] = self.bg
        om.grid(row=1, column=0, padx=int(self.default_size / 2))

        self.listing_button = tk.Button(self.listing_frame, text=lang.LISTING_BUTTON, command=self.make_listing, bg=self.bg)
        self.listing_button.grid(row=1, column=1, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.listing_button)

        self.listing_images_var = tk.IntVar()
        self.listing_images_var.set(0)
        tk.Checkbutton(self.listing_frame, text=lang.CHECK_LISTING_IMAGES, font=self.default_font, variable=self.listing_images_var, bg=self.bg).grid(row=1, column=2, padx=int(self.default_size / 2))

        self.left_frame = tk.Frame(self.root, bg=self.bg)
        self.left_frame.grid(row=7, column=0)

        # tk.Label(self.left_frame, text=lang.OWN_AREA, font=self.bold_font, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size / 2))
        self.own_button = tk.Button(self.left_frame, text=lang.LOAD_OWN_BUTTON, command=self.load_own_ponies, bg=self.bg)
        self.own_button.grid(row=0, column=0, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.own_button)
        self.care_all_button = tk.Button(self.left_frame, text=lang.CARE_OWN_BUTTON, command=self.care_all, bg=self.bg)
        self.care_all_button.grid(row=0, column=1, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.care_all_button)
        self.train_what_var = tk.StringVar()
        self.train_all_button = tk.Button(self.left_frame, text=lang.TRAIN_OWN_BUTTON, command=lambda x=self.train_what_var.get: self.train_all(x() == lang.TRAIN_WHAT_OPTION_ONLY), bg=self.bg)
        self.train_all_button.grid(row=0, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.train_all_button)
        self.train_what_options_list = [lang.TRAIN_WHAT_OPTION_ALL, lang.TRAIN_WHAT_OPTION_ONLY]
        self.train_what_var.set(self.train_what_options_list[0])
        self.train_what_option = tk.OptionMenu(self.left_frame, self.train_what_var, *self.train_what_options_list)
        self.train_what_option.grid(row=1, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.train_what_option)
        self.beauty_all_button = tk.Button(self.left_frame, text=lang.BEAUTY_OWN_BUTTON, command=self.beauty_all, bg=self.bg)
        self.beauty_all_button.grid(row=0, column=3, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.beauty_all_button)
        self.deckstation_login_all_button = tk.Button(self.left_frame, text=lang.DECKSTATION_LOGIN_BUTTON, command=self.deckstation_login_all_wrapper, bg=self.bg)
        self.deckstation_login_all_button.grid(row=0, column=4, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.deckstation_login_all_button)
        self.deckstation_threshold_var = tk.StringVar()
        self.deckstation_threshold_list = [lang.DECKSTATION_THRESHOLD_ALL, '<= 2000'] + [f'<= {p*1000}' for p in range(5, 45, 5)]
        self.deckstation_threshold_var.set(self.deckstation_threshold_list[0])
        self.deckstation_threshold_option = tk.OptionMenu(self.left_frame, self.deckstation_threshold_var, *self.deckstation_threshold_list)
        self.deckstation_threshold_option.grid(row=1, column=4, padx=int(self.default_size / 2))

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
        om = tk.OptionMenu(self.exterior_frame, self.horse_page_type_var, *self.horse_pages)
        om['bg'] = self.bg
        om.grid(row=0, column=2, padx=int(self.default_size / 2))

        races = list(self.extractor.race_dict.keys())
        self.race_var = tk.StringVar()
        self.race_var.set(races[0])  # default value
        om = tk.OptionMenu(self.exterior_frame, self.race_var, *races)
        om['bg'] = self.bg
        om.grid(row=0, column=3, columnspan=2, padx=int(self.default_size / 2))

        self.listing_names_plus_ext = list(self.listing_names)
        self.listing_names_plus_ext.append('Exterieur')
        self.market_listing_var = tk.StringVar()
        self.market_listing_var.set(self.listing_names_plus_ext[-1])
        om = tk.OptionMenu(self.exterior_frame, self.market_listing_var, *self.listing_names_plus_ext)
        om['bg'] = self.bg
        om.grid(row=1, column=1, padx=int(self.default_size / 2))

        sort_bys = list(self.extractor.sort_by_dict.keys())
        self.sort_by_var = tk.StringVar()
        self.sort_by_var.set(sort_bys[7])  # default value
        om = tk.OptionMenu(self.exterior_frame, self.sort_by_var, *sort_bys)
        om['bg'] = self.bg
        om.grid(row=1, column=0, padx=int(self.default_size / 2))

        self.ext_button = tk.Button(self.exterior_frame, text=lang.EXTERIEUR_BUTTON, command=self.exterior_search, bg=self.bg)
        self.ext_button.grid(row=1, column=2, padx=int(self.default_size / 2))
        self.interactive_elements.append(self.ext_button)

        tk.Label(self.exterior_frame, text=lang.N_PAGES_LABEL, font=self.default_font, bg=self.bg).grid(row=1, column=3, padx=int(self.default_size / 2))

        n_pages_list = ['1', '2', '3', '4', '5', '6',
                        '10: ' + lang.N_PAGES_FILTER_TEXT, '50: ' + lang.N_PAGES_FILTER_TEXT, '100: ' + lang.N_PAGES_FILTER_TEXT,
                        '200: ' + lang.N_PAGES_FILTER_TEXT, '500: ' + lang.N_PAGES_FILTER_TEXT, '1000: ' + lang.N_PAGES_FILTER_TEXT]
        self.n_pages_var = tk.StringVar()
        self.n_pages_var.set(n_pages_list[0])  # default value
        om = tk.OptionMenu(self.exterior_frame, self.n_pages_var, *n_pages_list, command=self.market_search_pages_select)
        om['bg'] = self.bg
        om.grid(row=1, column=4)

        self.cache_frame = tk.Frame(self.root, bg=self.bg)
        self.cache_frame.grid(row=8, column=0, padx=self.default_size, pady=self.default_size)

        tk.Label(self.cache_frame, text=lang.CACHE_LABEL, font=self.bold_font, bg=self.bg).grid(row=0, column=1, padx=int(self.default_size / 2))
        self.halloween_button = tk.Button(self.cache_frame, text=lang.EVENT_BUTTON_START, command=self.halloween_toggle, bg=self.bg)
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

        self.shutdown_var = tk.IntVar()
        self.shutdown_var.set(0)
        self.checkbox_shutdown = tk.Checkbutton(self.cache_frame, text=lang.SHUTDOWN_CHECKBOX, variable=self.shutdown_var, bg=self.bg)

        self.interactive_states = [0]*len(self.interactive_elements)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        default_train_file = Path('./default_train')
        if default_train_file.exists():
            with open(default_train_file, 'r') as f:
                dis_str = f.read().split()[0].strip()
                self.default_disciplines = [int(s) for s in dis_str]
        else:
            self.default_disciplines = [self.extractor.GRUNDAUSBILDUNG]

        if not self.check_for_updates():
            self.start_poll_on_boot()
            self.root.mainloop()

    def market_search_pages_select(self, value):
        self.filter_pre_selected = False
        if lang.N_PAGES_FILTER_TEXT in value:
            self.listing_filter = ''
            _ = FilterWindow(self.root, self, lang.FILTER_WINDOW_TITLE)
            if len(self.listing_filter) == 0:
                self.n_pages_var.set('1')
                return
            self.filter_pre_selected = True

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

    def deckstation_login_all_wrapper(self):
        fee_thresh = None
        splt = self.deckstation_threshold_var.get().split('=')
        if len(splt) > 1:
            fee_thresh = int(splt[1])
        self.deckstation_login_all(fee_thresh)

    def deckstation_login_all(self, fee_threshold=None):
        too_many_redirects_ids = []
        all_ids, all_races, _ = read_own_file()
        stud_lines = []
        stud_file = Path('./studs')
        if stud_file.is_file():
            with open(stud_file, 'r') as f:
                stud_lines = f.read().splitlines()
        stud_ids = [l.split()[0] for l in stud_lines]
        own_stud_lines = [stud_lines[i].split() for i, pid in enumerate(stud_ids) if pid in all_ids]
        if len(own_stud_lines) > 0:
            progressbar = ProgressWindow(self.root, self, title=lang.DECKSTATION_LOGIN_BUTTON, steps=len(own_stud_lines), initial_text=str(own_stud_lines[0][0]))
            for pid, fee in own_stud_lines:
                if (fee_threshold is not None) and (int(fee) > fee_threshold):
                    continue
                cont = False
                brk = False
                for retry_num in range(11):
                    if not self.extractor.login_deckstation(pid, fee):
                        if 'too many redirects' in self.extractor.log[-1].lower():
                            too_many_redirects_ids.append(pid)
                            cont = True
                            break
                        if retry_num < 10:
                            # try again after 15s
                            progressbar.set_text_only(lang.WAITING_FOR_CONNECTION.format(retry_num + 1))
                            time.sleep(15)
                            progressbar.set_text_only(str(pid))
                        else:
                            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                            brk = True
                            break
                    else:
                        # beauty login was successful
                        break
                if cont:
                    # too many redirects occurred in inner loop
                    continue
                if brk:
                    # all retries in vain
                    return
                if len(self.extractor.log) > 0 and '25 years' in self.extractor.log[-1].lower() and pid in self.extractor.log[-1]:
                    print('Pony {} is older than 25 years. Removing from stud file.'.format(pid))
                    if stud_file.is_file():
                        # delete pid line from stud file
                        stud_lines = [l for l in stud_lines if pid not in l]
                        with open(stud_file, 'w') as f:
                            f.write('\n'.join(stud_lines))

                progressbar.step(str(pid))

        if len(too_many_redirects_ids) > 0:
            message = lang.REDIRECTS_WARNING_MESSAGE
            for pid in too_many_redirects_ids:
                message += ('\n' + str(pid))
            messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def beauty_all(self):
        too_many_redirects_ids = []
        all_ids, all_races, _ = read_own_file()
        beauty_ids = []
        beauty_file = Path('./beauty_ponies')
        if beauty_file.is_file():
            with open(beauty_file, 'r') as f:
                beauty_ids = f.read().split()
        own_beauty = [pid for pid in all_ids if pid in beauty_ids]
        if len(own_beauty) > 0:
            progressbar = ProgressWindow(self.root, self, title=lang.BEAUTY_OWN_BUTTON, steps=len(own_beauty), initial_text=str(own_beauty[0]))
            for pid in own_beauty:
                cont = False
                brk = False
                for retry_num in range(11):
                    if not self.extractor.login_beauty(pid):
                        if 'too many redirects' in self.extractor.log[-1].lower():
                            too_many_redirects_ids.append(pid)
                            cont = True
                            break
                        if retry_num < 10:
                            # try again after 15s
                            progressbar.set_text_only(lang.WAITING_FOR_CONNECTION.format(retry_num + 1))
                            time.sleep(15)
                            progressbar.set_text_only(str(pid))
                        else:
                            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                            brk = True
                            break
                    else:
                        # beauty login was successful
                        break
                if cont:
                    # too many redirects occurred in inner loop
                    continue
                if brk:
                    # all retries in vain
                    return
                if len(self.extractor.log) > 0 and '25 years' in self.extractor.log[-1].lower() and pid in self.extractor.log[-1]:
                    print('Pony {} is older than 25 years. Removing from beauty file.'.format(pid))
                    if beauty_file.is_file():
                        # delete pid line from stud file
                        beauty_ids = [l for l in beauty_ids if pid not in l]
                        with open(beauty_file, 'w') as f:
                            f.write('\n'.join(beauty_ids))
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

    def train_all(self, only_train=False):
        too_many_redirects_ids = []
        all_ids, all_races, _ = read_own_file()
        fully_trained_ids = []
        only_train_ids = []
        fully_trained_file = Path('./fully_trained')
        if fully_trained_file.is_file():
            with open(fully_trained_file, 'r') as f:
                fully_trained_ids = f.read().split()
        only_train_file = Path('./only_train')
        if only_train_file.is_file():
            with open(only_train_file, 'r') as f:
                only_train_ids = f.read().split()
        elif only_train:
            messagebox.showerror(lang.IO_ERROR, lang.ERROR_ONLY_TRAIN_FILE_MISSING)
            return
        if only_train:
            train_ids = [pid for pid in all_ids if (pid in only_train_ids and pid not in fully_trained_ids)]
        else:
            train_ids = [pid for pid in all_ids if pid not in fully_trained_ids]
        discipline_ids, disciplines = read_train_file()

        if len(train_ids) > 0:
            add_to_only_train = []
            add_to_fully_trained = []
            progressbar = ProgressWindow(self.root, self, title=lang.TRAIN_OWN_BUTTON, steps=len(train_ids), initial_text=str(train_ids[0]))
            for this_id in train_ids:
                if this_id in discipline_ids:
                    dis_idx = discipline_ids.index(this_id)
                    dis_str = disciplines[dis_idx]
                    dis_list = [int(s) for s in dis_str]
                else:
                    dis_list = self.default_disciplines

                cont = False
                brk = False
                for retry_num in range(11):
                    if not self.extractor.train_pony(this_id, disciplines=dis_list):
                        if 'too many redirects' in self.extractor.log[-1].lower():
                            too_many_redirects_ids.append(this_id)
                            progressbar.step(str(this_id))
                            cont = True
                            break
                        if retry_num < 10:
                            # try again after 15s
                            progressbar.set_text_only(lang.WAITING_FOR_CONNECTION.format(retry_num + 1))
                            time.sleep(15)
                            progressbar.set_text_only(str(this_id))
                        else:
                            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                            progressbar.close()
                            brk = True
                            break
                    else:
                        # training was successful
                        break
                if cont:
                    # too many redirects occurred in inner loop
                    continue
                if brk:
                    # all retries in vain
                    break
                # check whether pony is fully trained or in charakter training
                if len(self.extractor.log) > 0 and this_id in self.extractor.log[-1] \
                        and 'fully trained' in self.extractor.log[-1]:
                       # and len(self.extractor.parser.charakter_training_values) > 0:
                    years = int(self.extractor.parser.facts_values['Alter'].split('Jahre')[0].strip()) \
                        if 'Jahre' in self.extractor.parser.facts_values['Alter'] else 0
                    if years >= 3 or len(dis_list) == 0 or dis_list == [stats_parser.PonyExtractor.GRUNDAUSBILDUNG]:    # if younger than 3 years, pony can neither be fully trained nor in charakter training
                        # flag = True
                        # for k in self.extractor.parser.charakter_training_values.keys():
                        #     if self.extractor.parser.charakter_training_values[k] < self.extractor.parser.charakter_training_max[k]:
                        #         flag = False
                        #         add_to_only_train.append(this_id)   # if fully trained without charakter, pony is ready for charakter training
                        #         break
                        # if flag:
                        add_to_fully_trained.append(this_id)
                elif len(self.extractor.log) > 0 and this_id in self.extractor.log[-1] \
                        and 'charakter' in self.extractor.log[-1]:
                    add_to_only_train.append(this_id)
                progressbar.step(str(this_id))

                time.sleep(2)

            for new_id in add_to_fully_trained:
                fully_trained_ids.append(new_id)
                if new_id in only_train_ids:
                    remove_index = only_train_ids.index(new_id)
                    del only_train_ids[remove_index]
            for new_id in add_to_only_train:
                if new_id not in only_train_ids:
                    only_train_ids.append(new_id)
            with open(fully_trained_file, 'w') as f:
                f.write('\n'.join(fully_trained_ids))
            with open(only_train_file, 'w') as f:
                f.write('\n'.join(only_train_ids))

            if len(too_many_redirects_ids) > 0:
                message = lang.REDIRECTS_WARNING_MESSAGE
                for pid in too_many_redirects_ids:
                    message += ('\n' + str(pid))
                messagebox.showwarning(title=lang.REDIRECTS_WARNING_TITLE, message=message)

    def train_this(self):
        this_id = self.id_label.cget('text').strip()
        if len(this_id) > 0 and this_id.isnumeric():
            discipline_ids, disciplines = read_train_file()
            if this_id in discipline_ids:
                dis_idx = discipline_ids.index(this_id)
                dis_str = disciplines[dis_idx]
                dis_list = [int(s) for s in dis_str]
            else:
                dis_list = [stats_parser.PonyExtractor.GRUNDAUSBILDUNG]
            if not self.extractor.train_pony(this_id, disciplines=dis_list):
                messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                return

    def care_all(self):
        too_many_redirects_ids = []
        all_ids, all_races, _ = read_own_file()
        progressbar = ProgressWindow(self.root, self, title=lang.CARE_OWN_BUTTON, steps=len(all_ids), initial_text=str(all_ids[0]))
        for this_id in all_ids:
            cont = False
            brk = False
            for retry_num in range(11):
                if not self.extractor.care_pony(this_id):
                    if 'too many redirects' in self.extractor.log[-1].lower():
                        too_many_redirects_ids.append(this_id)
                        cont = True
                        break
                    if retry_num < 10:
                        # try again after 15s
                        progressbar.set_text_only(lang.WAITING_FOR_CONNECTION.format(retry_num + 1))
                        time.sleep(15)
                        progressbar.set_text_only(str(this_id))
                    else:
                        messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
                        progressbar.close()
                        brk = True
                        break
                else:
                    # care was successful
                    break
            if cont:
                # too many redirects occurred in inner loop
                continue
            if brk:
                # all retries in vain
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

            self.halloween_button['text'] = lang.EVENT_BUTTON_STOP
        else:
            self.halloween_process.terminate()
            self.halloween_process = None
            os.system('taskkill /IM chromedriver.exe /F')
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
        running_proc_indices = [i for i in range(len(self.poll_processes)) if self.poll_processes[i].is_alive()]
        self.poll_processes = [self.poll_processes[i] for i in running_proc_indices]
        self.poll_ids = [self.poll_ids[i] for i in running_proc_indices]
        # self._update_poll_file()    # deactivated to keep ponies in the file because they are supposed to be used multiple times
        if len(self.poll_ids) > 0:
            if messagebox.askokcancel(lang.QUIT_HEADING, lang.QUIT_TEXT):
                for p in self.poll_processes:
                    p.terminate()
            else:
                return
        if self.halloween_process is not None:
            self.halloween_process.terminate()
            os.system('taskkill /IM chromedriver.exe /F')
        # if self.chromedriver_process is not None:
        #     self.chromedriver_process.terminate()
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

    def clipboard_description(self, pid=None):
        if pid is not None:
            pony_id_str = str(pid)
        else:
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
                if round(normval, 1) == round(normval):   # if rounding to one decimal place yields x.0
                    textval = str(int(round(normval, 1)))
                else:
                    textval = str(round(normval, 1)) if normval <= 100 else str(int(normval))   # if Gesamtpotenzial ( > 100), show as integer
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
        for l_list in l: # list ist aber ein dict
            if prop in list(l_list.keys()):
                try:
                    prop_sum = sum(l_list.values()) - l_list[prop]
                    if prop_sum == 0:
                        raise TypeError('This is expected behavior')  # if all single values are 0, values are probably
                                                                      # coming from a FakeParser, which is made from
                                                                      # parsing a list with quick mode.
                except TypeError:
                    return (l_list[prop], len(l_list)-1)
                return (prop_sum, len(l_list)-1)
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
        if self.filter_pre_selected:
            self.quick_display_var.set(1)
            n_pages = int(self.n_pages_var.get().split(':')[0])
        else:
            n_pages = int(self.n_pages_var.get())
        self.quick_display = bool(self.quick_display_var.get())
        self.exterior_search_ids = self.extractor.browse_horses(self.horse_pages.index(self.horse_page_type_var.get()), race=self.race_var.get(), sort_by=sort_by_value, pages=n_pages, quick=self.quick_display)
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
            own_ids, own_races, _ = read_own_file()
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
        all_ids, all_races, all_stables = read_own_file()
        prog_wind = ProgressWindow(self.root, self, title=lang.LOAD_OWN_BUTTON, steps=10, initial_text=lang.GET_STABLE_LIST, shutdown_button=False)
        horse_ids, stable_names = self.extractor.get_own_ponies(prog_wind)
        if horse_ids == False:
            messagebox.showerror(title=lang.PONY_INFO_ERROR, message=self.extractor.log[-1])
        else:
            own_file = Path('./owned_ponies')
            with open(own_file, 'w') as f:
                for id, stab in zip(horse_ids, stable_names):
                    id_str = str(id)
                    this_race = all_races[all_ids.index(id_str)] if id_str in all_ids else -1
                    f.write(id_str + ' ' + str(this_race) + ' ' + str(stab) + '\n')

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
        all_ids, all_races, all_stables = read_own_file()
        if self.check_ownership_var.get():
            # We want to add id to the file if it does not exist
            if pony_id_str not in all_ids:
                if str(self.extractor.pony_id) != pony_id_str:
                    self.extractor.get_pony_info(pony_id_str)
                this_race = self.extractor.race_dict[self.extractor.parser.facts_values['Rasse']]
                all_ids.append(pony_id_str)
                all_races.append(str(this_race))
        else:
            # We want to delete id from the file if it does exist
            if pony_id_str in all_ids:
                ind = all_ids.index(pony_id_str)
                del all_ids[ind]
                del all_races[ind]
                del all_stables[ind]
        with open(own_file, 'w') as f:
            for pid, race, stab in zip(all_ids, all_races, all_stables):
                f.write(str(pid) + ' ' + str(race) + ' ' + str(stab) + '\n')

    def is_owned(self):

        def exist_in_file(pony_id_str, content):
            exist = False
            for ll in content:
                if ll.split()[0] == pony_id_str:
                    exist = True
                    break
            return exist

        pony_id_str = self.id_label.cget('text')
        all_ids, _, _ = read_own_file()
        return pony_id_str in all_ids

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
