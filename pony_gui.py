# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import font
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image, ImageTk
from pathlib import Path
import csv

import lang
import stats_parser
import html_clipboard
import dialog

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

        # Create gui elements here
        # banner
        self.imorg = Image.open("4logo-sm.png")
        dim = self.dims_by_scale(0.01 * self.default_size)[0]
        fac = float(dim) / self.imorg.size[0]
        dim2 = int(self.imorg.size[1] * fac)
        imobj = self.imorg.resize((dim, dim2), Image.ANTIALIAS)
        self.banner = ImageTk.PhotoImage(imobj)
        self.banner_label = tk.Label(self.root, image=self.banner, bg=self.bg)
        self.banner_label.grid(rowspan=6)

        self.title_frame = tk.Frame(self.root)
        self.title_frame.grid(row=0, column=1, columnspan=2, padx=self.default_size)
        self.name_label = tk.Label(self.title_frame, text='', font=self.big_bold_font, bg=self.bg)
        self.name_label.grid()
        self.id_label = tk.Label(self.title_frame, text='', font=self.bold_font, bg=self.bg)
        self.id_label.grid()

        tk.Label(self.root, text=lang.PONY_ID, font=self.default_font, bg=self.bg).grid(row=1, column=1)
        self.id_spin = tk.Spinbox(self.root, width=6, from_=0, to=999999, bg=self.bg)
        self.id_spin.grid(row=1, column=2)

        self.a_button_frame = tk.Frame(self.root)
        self.a_button_frame.grid(row=2, column=1, columnspan=2, padx=self.default_size)
        self.request_button = tk.Button(self.a_button_frame, text=lang.REQUEST, command=self.request, bg=self.bg)
        self.request_button.pack(side=tk.LEFT, padx=self.default_size//2)
        try:
            with open('login', 'r') as f:
                _ = f.readline().strip()
                _ = f.readline().strip()
        except IOError:
            self.request_button.configure(state=tk.DISABLED)
        self.login_button = tk.Button(self.a_button_frame, text=lang.LOGIN_BUTTON, command=self.enter_login, bg=self.bg)
        self.login_button.pack(side=tk.LEFT, padx=self.default_size//2)

        self.export_button = tk.Button(self.root, text=lang.EXPORT, width=self.default_size, command=self.export, bg=self.bg, state=tk.DISABLED)
        self.export_button.grid(row=3, column=1, columnspan=2, padx=self.default_size)

        self.radio_frame = tk.Frame(self.root)
        self.radio_frame.grid(row=5, column=1, columnspan=2, padx=self.default_size)
        self.export_format_var = tk.IntVar()
        self.export_format_var.set(0)
        tk.Radiobutton(self.radio_frame, text=lang.RADIO_HTML, variable=self.export_format_var, value=0, bg=self.bg).grid(row=0, column=0, padx=int(self.default_size/2))
        tk.Radiobutton(self.radio_frame, text=lang.RADIO_CSV, variable=self.export_format_var, value=1, bg=self.bg).grid(row=0, column=1, padx=int(self.default_size / 2))
        self.export_method_var = tk.IntVar()
        self.export_method_var.set(0)
        tk.Radiobutton(self.radio_frame, text=lang.RADIO_CLIPBOARD, variable=self.export_method_var, value=0, bg=self.bg).grid(row=1, column=0, padx=int(self.default_size / 2))
        tk.Radiobutton(self.radio_frame, text=lang.RADIO_FILE, variable=self.export_method_var, value=1, bg=self.bg).grid(row=1, column=1, padx=int(self.default_size / 2))


        self.checkbox_frame = tk.Frame(self.root)
        self.checkbox_frame.grid(row=6, column=1, columnspan=2, padx=self.default_size)
        
        self.check_all_var = tk.IntVar()
        self.check_all_var.set(0)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_ALL, font=self.bold_font, variable=self.check_all_var, command=self.toggle_all_var, bg=self.bg).grid(row=0, column=0,
                                                                                                                                                                 padx=int(self.default_size/2))
        self.check_var_container = []
        self.check_gesundheit_var = tk.IntVar()
        self.check_gesundheit_var.set(0)
        self.check_var_container.append(self.check_gesundheit_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_GESUNDHEIT, font=self.default_font, variable=self.check_gesundheit_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=0,
                                                                                                                                                                     padx=int(self.default_size / 2))
        self.check_charakter_var = tk.IntVar()
        self.check_charakter_var.set(0)
        self.check_var_container.append(self.check_charakter_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_CHARAKTER, font=self.default_font, variable=self.check_charakter_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=1,
                                                                                                                                                                    padx=int(self.default_size / 2))
        self.check_exterieur_var = tk.IntVar()
        self.check_exterieur_var.set(0)
        self.check_var_container.append(self.check_exterieur_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_EXTERIEUR, font=self.default_font, variable=self.check_exterieur_var, command=self.toggle_all_off, bg=self.bg).grid(row=1, column=2,
                                                                                                                                                                    padx=int(self.default_size / 2))
        self.check_training_var = tk.IntVar()
        self.check_training_var.set(0)
        self.check_var_container.append(self.check_training_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_TRAINING, font=self.default_font, variable=self.check_training_var, command=self.toggle_all_off, bg=self.bg).grid(row=2, column=0,
                                                                                                                                                                        padx=int(self.default_size/2))
        self.check_training_details_var = tk.IntVar()
        self.check_training_details_var.set(0)
        self.check_var_container.append(self.check_training_details_var)
        tk.Checkbutton(self.checkbox_frame, text=lang.CHECK_TRAINING_DETAILS, font=self.default_font, variable=self.check_training_details_var, command=self.toggle_all_off,
                       bg=self.bg).grid(row=2, column=1,padx=int(self.default_size / 2))

        self.checkbox_frame2 = tk.Frame(self.root)
        self.checkbox_frame2.grid(row=7, column=1, columnspan=2, padx=self.default_size)

        self.check_table_headings_var = tk.IntVar()
        self.check_table_headings_var.set(0)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_TABLE_HEADINGS, font=self.default_font, variable=self.check_table_headings_var, bg=self.bg).grid(row=0, column=0,
                                                                                                                                                                       padx=int(self.default_size / 2))
        self.check_sum_values_var = tk.IntVar()
        self.check_sum_values_var.set(0)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_SUM_VALUES, font=self.default_font, variable=self.check_sum_values_var, bg=self.bg).grid(row=0, column=1,
                                                                                                                                                              padx=int(self.default_size / 2))
        self.check_complete_gesundheit_var = tk.IntVar()
        self.check_complete_gesundheit_var.set(0)
        tk.Checkbutton(self.checkbox_frame2, text=lang.CHECK_COMPLETE_GESUNDHEIT, font=self.default_font, variable=self.check_complete_gesundheit_var, bg=self.bg).grid(row=1, column=0,
                                                                                                                                                                        padx=int(self.default_size / 2))
        
        self.root.mainloop()

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

    def enter_login(self):
        _ = LoginWindow(self.root, self, lang.LOGIN_TITLE)
        if len(self.user) > 0 and len(self.pw) > 0:
            self.request_button.configure(state=tk.NORMAL)

    def export(self):
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
            write_dict.update({k: self.extractor.parser.training_values[k] for k in list(self.extractor.parser.training_values.keys())[int(delete_first):]})
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
        write_headers = write_dict.keys()

        if self.export_format_var.get() == 1:  # csv
            if self.export_method_var.get() == 1: # file
                filename = filedialog.asksaveasfilename(initialdir="/", initialfile="{}-{}.csv".format(self.extractor.pony_id, self.extractor.parser.name),
                                                        title=lang.SELECT_FILE, filetypes=[(lang.CSV_FILES, "*.csv")])
                if not filename.endswith('.csv'):
                    filename = filename + '.csv'
                file_path = Path(filename)
                try:
                    with open(file_path, 'w') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=write_headers)
                        if self.check_table_headings_var.get():
                            writer.writeheader()
                        writer.writerow(write_dict)
                except IOError:
                    messagebox.showerror(title=lang.IO_ERROR, message=lang.CSV_WRITE_ERROR)
            else: # clipboard
                messagebox.showerror(title=lang.NOT_SUPPORTED_ERROR, message=lang.NOT_SUPPORTED_ERROR)
        else: # html
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
            if self.export_method_var.get() == 1:  # file
                filename = filedialog.asksaveasfilename(initialdir="/", initialfile="{}-{}.html".format(self.extractor.pony_id, self.extractor.parser.name),
                                                        title=lang.SELECT_FILE, filetypes=[(lang.HTML_FILES, "*.html")])
                if not filename.endswith('.html'):
                    filename = filename + '.html'
                file_path = Path(filename)
                try:
                    with open(file_path, 'w') as htmlfile:
                        htmlfile.write(html_string)
                except IOError:
                    messagebox.showerror(title=lang.IO_ERROR, message=lang.HTML_WRITE_ERROR)
            else: # clipboard
                html_clipboard.PutHtml(html_string)
                # with open("clip.txt", "w") as f:
                #     f.write(html_clipboard.GetHtml())


    def dims_by_scale(self, scale):
        if hasattr(scale, '__iter__'):
            return [int(el * sc) for el, sc in zip(self.screen_resolution,scale)]
        return [int(el * scale) for el in self.screen_resolution]

if __name__ == '__main__':
    ponyGUI = PonyGUI()
