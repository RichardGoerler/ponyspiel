try:
    import Tkinter as tk
except:
    import tkinter as tk

from PIL import Image, ImageTk

import lang

class Dialog(tk.Toplevel):

    def __init__(self, parent, gui, title=lang.DIALOG_TITLE):

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

        self.result = None

        head = tk.Frame(self, bg="#EDEEF3")
        self.header(head)
        head.pack()

        body = tk.Frame(self, bg="#EDEEF3")
        self.initial_focus = self.body(body)
        body.pack(padx=self.gui.default_size, pady=self.gui.default_size)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def header(self, master):
        # create dialog header.  this method should be overridden
        self.imorg = Image.open("ims/logo.png")
        dim = self.gui.dims_by_scale(0.015*self.gui.default_size)[1]
        imobj = self.imorg.resize((dim, dim), Image.ANTIALIAS)
        self.gui.logo = ImageTk.PhotoImage(imobj)
        self.header_image_label = tk.Label(master, image=self.gui.logo, bg="#EDEEF3")
        self.header_image_label.pack()

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = tk.Frame(self, bg="#EDEEF3")

        w = tk.Button(box, text=lang.DIALOG_OK, width=10, command=self.ok, default=tk.ACTIVE, bg="#EDEEF3")
        w.pack(side=tk.LEFT, padx=int(self.gui.default_size/2), pady=int(self.gui.default_size/2))
        w = tk.Button(box, text=lang.DIALOG_CANCEL, width=10, command=self.cancel, bg="#EDEEF3")
        w.pack(side=tk.LEFT, padx=int(self.gui.default_size/2), pady=int(self.gui.default_size/2))

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    #
    # standard button semantics

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override