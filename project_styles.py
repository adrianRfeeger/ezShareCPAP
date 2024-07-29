import tkinter as tk
import tkinter.ttk as ttk
from PIL import Image, ImageTk, ImageDraw

def create_rounded_button_image(width, height, radius, color):
    image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width, height), radius, fill=color)
    return ImageTk.PhotoImage(image)

def setup_ttk_styles(master=None):
    style = ttk.Style(master)
    
    # Define colors
    colors = {
        '-fg': "#313131",
        '-bg': "#f0f0f0",
        '-disabledfg': "#9e9e9e",
        '-disabledbg': "#f0f0f0",
        '-selectfg': "#ffffff",
        '-selectbg': "#217346",
        '-highlight': "#00c4cc"
    }

    # Define fonts
    fonts = {
        'default': ("Helvetica", 14),
        'button': ("Helvetica", 14, 'bold'),
        'title': ("Helvetica", 18, 'bold'),
        'label': ("Helvetica", 14)
    }

    # Create rounded button images
    button_image_normal = create_rounded_button_image(100, 30, 15, colors['-selectbg'])
    button_image_active = create_rounded_button_image(100, 30, 15, colors['-highlight'])
    button_image_disabled = create_rounded_button_image(100, 30, 15, colors['-disabledbg'])

    # Register images to be used in styles
    master.tk.call('image', 'create', 'photo', 'button_normal', '-data', button_image_normal)
    master.tk.call('image', 'create', 'photo', 'button_active', '-data', button_image_active)
    master.tk.call('image', 'create', 'photo', 'button_disabled', '-data', button_image_disabled)

    # Check if the theme already exists
    if "park-light" not in style.theme_names():
        # Configure overall theme
        style.theme_create("park-light", parent="default", settings={
            ".": {
                "configure": {
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "troughcolor": colors["-bg"],
                    "focuscolor": colors["-highlight"],
                    "selectbackground": colors["-selectbg"],
                    "selectforeground": colors["-selectfg"],
                    "insertwidth": 1,
                    "insertcolor": colors["-fg"],
                    "fieldbackground": colors["-bg"],
                    "font": fonts['default'],
                    "borderwidth": 1,
                    "relief": "flat"
                },
                "map": {
                    "foreground": [("disabled", colors["-disabledfg"])],
                    "background": [("disabled", colors["-disabledbg"])],
                    "focuscolor": [("!focus", colors["-bg"]), ("focus", colors["-highlight"])],
                    "selectbackground": [("!selected", colors["-bg"]), ("selected", colors["-selectbg"])]
                }
            },
            "TButton": {
                "configure": {
                    "padding": [8, 4],
                    "anchor": "center",
                    "font": fonts['button'],
                    "relief": "flat",
                    "borderwidth": 0,
                    "background": 'button_normal',
                    "image": 'button_normal'
                },
                "map": {
                    "background": [("active", 'button_active'), ("disabled", 'button_disabled')],
                    "foreground": [("disabled", colors["-disabledfg"])]
                }
            },
            "Accent.TButton": {
                "configure": {
                    "padding": [8, 4],
                    "anchor": "center",
                    "font": fonts['button'],
                    "relief": "flat",
                    "borderwidth": 0,
                    "background": 'button_normal',
                    "image": 'button_normal'
                },
                "map": {
                    "background": [("active", 'button_active'), ("disabled", 'button_disabled')],
                    "foreground": [("disabled", colors["-disabledfg"])]
                }
            },
            "TCheckbutton": {
                "configure": {
                    "padding": 4,
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "font": fonts['default'],
                    "indicatorcolor": colors["-selectbg"]
                },
                "map": {
                    "indicatorcolor": [
                        ("selected", colors["-selectbg"]),
                        ("!selected", colors["-bg"])
                    ],
                    "foreground": [
                        ("selected", colors["-fg"]),
                        ("!selected", colors["-fg"])
                    ]
                }
            },
            "TRadiobutton": {
                "configure": {
                    "padding": 4,
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "font": fonts['default']
                }
            },
            "TEntry": {
                "configure": {
                    "padding": 4,
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "fieldbackground": colors["-bg"],
                    "borderwidth": 1,
                    "focusthickness": 3,
                    "focuscolor": colors["-highlight"],
                    "font": fonts['default']
                }
            },
            "TCombobox": {
                "configure": {
                    "padding": 4,
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "fieldbackground": colors["-bg"],
                    "borderwidth": 1,
                    "arrowcolor": colors["-fg"],
                    "font": fonts['default']
                },
                "map": {
                    "fieldbackground": [("readonly", colors["-bg"]), ("disabled", colors["-disabledbg"])],
                    "foreground": [("readonly", colors["-fg"]), ("disabled", colors["-disabledfg"])],
                    "background": [("active", colors["-highlight"])]
                }
            },
            "TLabel": {
                "configure": {
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "font": fonts['label']
                }
            },
            "TNotebook": {
                "configure": {
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "padding": 2
                }
            },
            "TNotebook.Tab": {
                "configure": {
                    "padding": [14, 4],
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "font": fonts['default']
                },
                "map": {
                    "background": [("selected", colors["-selectbg"]), ("active", colors["-highlight"])],
                    "foreground": [("selected", colors["-selectfg"]), ("active", colors["-selectfg"])]
                }
            },
            "TProgressbar": {
                "configure": {
                    "troughcolor": colors["-bg"],
                    "background": colors["-selectbg"]
                }
            },
            "Treeview": {
                "configure": {
                    "background": colors["-bg"],
                    "foreground": colors["-fg"],
                    "fieldbackground": colors["-bg"],
                    "font": fonts['default']
                },
                "map": {
                    "background": [("selected", colors["-selectbg"])],
                    "foreground": [("selected", colors["-selectfg"])]
                }
            }
        })

    # Use the newly created theme
    style.theme_use("park-light")

    # Apply similar styles to other widgets if needed
    style.configure("TLabel",
                    font=fonts['label'],
                    background=colors["-bg"],
                    foreground=colors["-fg"])
    style.configure("TCheckbutton",
                    font=fonts['default'],
                    background=colors["-bg"],
                    foreground=colors["-fg"])
    style.configure("TEntry",
                    font=fonts['default'],
                    background=colors["-bg"],
                    foreground=colors["-fg"],
                    fieldbackground=colors["-bg"],
                    borderwidth=1,
                    focusthickness=3,
                    focuscolor='none')

    # Configure styles for the main window
    if master:
        master.configure(background=colors["-bg"])

