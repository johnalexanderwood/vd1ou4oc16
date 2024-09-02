from collections import OrderedDict
import copy
import cv2
from functools import partial
import glob
import gzip
import importlib
import importlib.util
import PIL
import pickle
import os
import sys
from tkinter import filedialog
from tkinter import messagebox
from tkinter import EventType
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.dialogs import Messagebox

import rb_default_config
from rb_images import Images
from rb_copy_merge import CopyMergeDialog
from rb_splash import Splash

from rb_meter_ram import MeterRAM
from rb_types import *
# Note: The plugins are imported based on the config file in init


class RockBase(ttk.Frame):                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
    def __init__(self, *args, file_config, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.pack(fill=BOTH, expand=YES)
        self.window = args[0]

        # Create default and then try and load last saved config
        self.config = rb_default_config.Config()

        # If file exists overwrite the default config dictionary
        if os.path.isfile(file_config):
            with open (file_config, "r") as file_config:
                json_config = file_config.read()
                self.config = self.config.from_json(json_config)
        
        # UI Appearance
        self.config.view = View.DOUBLE      # Always start with Double View for easy of use 
        self.config.show_explorer = False   # Always start with explorer hidden
        self.keep_outline = True            # Always start with keep_outline shown
        self.mask_transparency = 0.5        # Could be pushed to config in future
        self.observ_transpareny = 0.5       # Could be pushed to config in future
        self.interp_transparency = 0.5      # Could be pushed to config in future

        # After getting config
        self.style = ttk.Style()
        self.widgets = {}
        
        # Need these to make the plugins
        self.ui_images_raw = {}
        self.ui_images = {}
        self.load_ui_images()

        # All plugin instances are kept here
        self.plugin_next_id = 0
        self.plugins = {}

        # Load plugin modules based on config file
        plugin_modules = []
        for name in self.config.plugin_modules:
            m_name, i_name = name[0], name[1]
            if i_name in sys.modules:
                print(f"{i_name!r} already in sys.modules")
            elif (spec := importlib.util.find_spec(m_name)) is not None:
                # If you chose to perform the actual import ...
                module = importlib.util.module_from_spec(spec)
                sys.modules[i_name] = module
                spec.loader.exec_module(module)
                plugin_modules.append(module)
                print(f"{i_name!r} has been imported")
            else:
                print(f"can't find the {i_name!r} module")

        # Application Features, Registers of plugins and there types
        self.feature_mask = False
        self.feature_interp = False
        self.feature_observ = False
        self.avaliable_plugins = OrderedDict()    
        self.register_plugins(plugin_modules)

        self.plugin_default = 'PanZoom'  # The plugin to always go back to
        self.current_plugin_type = self.plugin_default
        self.current_plugin_instance = 'PanZoom'
        
        # Make the images class
        self.images = Images(self.config, self.plugins)
        self.load_starting_images()  

        # File/Image Set/Directory information
        self.current_rgb_file = f"{self.config.starting_rgb_path.split('/')[-1]}"
        self.current_file_index = None
        self.rgb_file_names = None
        self.directory_path = None

        # Keep  track of mouse state etc
        self.mouse = {
            'event': 0,
            'screen_x': None, #1389//2,  # screen_x - mouse does not know about zoom etc
            'screen_y': None, #429//2,  # screen_y - mouse does not know about zoom etc
            'old_screen_x': None,
            'old_screen_y': None,
            'active': False,  # True is moving, dragging, any button down...
            'over_secondary': False,  # True if over the secondary image
            'flags': 0,
            'param': ''
        }

        # Need to have the application working meter update
        # None means not running, any or value means running
        self.meter_working_animate = True
        self.meter_working_value = 1

        # Crate and Configure frames
        self.frame_top = ttk.Frame(self, style=(DEFAULT))
        self.frame_top.pack(fill=X, pady=1, side=TOP)

        self.frame_top_seperator = ttk.Frame(self, style=(DEFAULT))
        self.frame_top_seperator.pack(fill=X, pady=1, side=TOP)

        self.frame_tools = ttk.Frame(self, style='bg.TFrame')
        self.frame_tools.pack(side=LEFT, fill=Y)

        self.frame_explorer_seperator = ttk.Frame(self, style=(DEFAULT))
        self.frame_explorer_seperator.pack(fill=Y, pady=1, side=LEFT)

        self.frame_explorer = ttk.Frame(self.frame_tools, style=DEFAULT) #, style='bg.TFrame')
        self.frame_explorer.pack(side=LEFT, fill=Y,)# padx=1, pady=1)

        self.frame_plugins = ttk.Frame(self, style=DEFAULT)
        self.frame_plugins.pack(side=RIGHT, fill=Y)

        self.frame_treeview = ttk.Frame(self.frame_plugins, style='bg.TFrame')
        self.frame_treeview.pack(side=TOP, fill=Y)

        self.frame_properties = ttk.Frame(self.frame_plugins, style='bg.TFrame')
        self.frame_properties.pack(fill=BOTH, padx=2, pady=2)

        self.frame_plugins_seperator = ttk.Frame(self, style=(DEFAULT))
        self.frame_plugins_seperator.pack(fill=Y, padx=4, pady=1, side=RIGHT)

        self.frame_view = ttk.Frame(self, style='bg.TFrame')
        self.widgets['frame_view'] = self.frame_view
        self.frame_view.pack(fill=BOTH, expand=YES)

        self.frame_bottom = ttk.Frame(self, style='bg.TFrame')
        self.frame_bottom.pack(side=BOTTOM, fill=X, expand=NO)   
        
        # # Setup widgets on frames including the plugin widgets
        self.make_frame_explorer_widgets()
        self.make_frame_explorer_seperator_widgets()
        self.make_frame_top_widgets()
        self.make_frame_top_seperator_widgets()
        self.make_frame_view_widgets()
        self.make_frame_plugins_seperator_widgets()
        self.make_frame_treeview_widgets()
        self.make_properties_end(Disabled=True)
        self.make_frame_tools_widgets() 
        self.make_frame_bottom_widgets()
        self.make_menu()

        self.apply_config()  #Sets the colour theme, recent files etc

        # Bind the main keyboard handler
        self.bind_all("<Key>", self.event_keyboard)

        # Start check if the images need updating (IE internal changes by plugin)
        self.polled_update_check()

    #region make widgets
    def make_frame_top_widgets(self):
        # Button Three D View
        self.ui_images['three_d_view_gray'] = self.ui_images_raw['three_d_view_gray'].resize((
            self.config.button_layout_width, 
            self.config.button_layout_height
        ))
        self.ui_images['three_d_view_gray'] = PIL.ImageTk.PhotoImage(self.ui_images['three_d_view_gray'])

        self.widgets['button_three_d_view'] = ttk.Button(
            self.frame_top,
            text=None, 
            command=self.event_three_d_view, 
            image=self.ui_images['three_d_view_gray'], 
            state=DISABLED,
            bootstyle=(SECONDARY,) 
        )

        self.widgets['button_three_d_view'].pack(
            self.config.standard_button_view
        )

        ToolTip(self.widgets['button_three_d_view'], text="[DISABLED] Preview 3D model in seperate window,  if avaliable.")

        # Button Dual View
        self.ui_images['dual_view_gray'] = self.ui_images_raw['dual_view_gray'].resize((
            self.config.button_layout_width, 
            self.config.button_layout_height
        ))
        self.ui_images['dual_view_gray'] = PIL.ImageTk.PhotoImage(self.ui_images['dual_view_gray'])

        self.widgets['button_dual_view'] = ttk.Button(
            self.frame_top,
            text=None, 
            command=partial(self.event_change_view, View.DOUBLE), 
            image=self.ui_images['dual_view_gray'], 
            state=ACTIVE,
            bootstyle=(SECONDARY,) 
        )

        self.widgets['button_dual_view'].pack(
            self.config.standard_button_view
        )

        ToolTip(self.widgets['button_dual_view'], text="View Double")

        # Button Single View
        self.ui_images['single_view_gray'] = self.ui_images_raw['single_view_gray'].resize((
            self.config.button_layout_width, 
            self.config.button_layout_height
        ))
        self.ui_images['single_view_gray'] = PIL.ImageTk.PhotoImage(self.ui_images['single_view_gray'])

        self.widgets['button_single_view'] = ttk.Button(
            self.frame_top,
            text=None, 
            command=partial(self.event_change_view, View.SINGLE), 
            image=self.ui_images['single_view_gray'], 
            state=ACTIVE,
            bootstyle=(SECONDARY,) 
        )

        self.widgets['button_single_view'].pack(
            self.config.standard_button_view
        )

        ToolTip(self.widgets['button_single_view'], text="View Single")

        # Frame top light_dark
        self.frame_top_light_dark = ttk.Frame(self.frame_top, style=(DEFAULT))
        self.frame_top_light_dark.pack(fill=X, pady=1, side=RIGHT)

        # label
        self.widgets['label_toggle_light_dark'] = ttk.Label(
            self.frame_top_light_dark,
            text='Light/Dark',
            state=ACTIVE,
            bootstyle=(DEFAULT,),
            foreground='gray',
        )

        self.widgets['label_toggle_light_dark'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Toggle light dark
        self.widgets['toggle_light_dark'] = ttk.Checkbutton(
            self.frame_top_light_dark,
            text="", 
            command=partial(self.event_invert_theme, None, None),
            state=ACTIVE,
            bootstyle=(DEFAULT, TOGGLE, ROUND)
        )
        
        self.widgets['toggle_light_dark'].pack(
            side=TOP,
            ipadx=5,
            ipady=5,
            padx=1,
            pady=1,
        )
        
        # Vertical Splitter 
        name = 'separator_keep_outline'
        self.widgets[name] = ttk.Separator(
            self.frame_top,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=RIGHT, 
            fill=X,
            ipadx=4,
            #ipady=4,
            padx=1,
            #pady=1,
        )

        # Frame top light_dark
        self.frame_top_keep_outline = ttk.Frame(self.frame_top, style=(DEFAULT))
        self.frame_top_keep_outline.pack(fill=X, pady=1, side=RIGHT)

        # label
        self.widgets['label_toggle_keep_outline'] = ttk.Label(
            self.frame_top_keep_outline,
            text='Keep Outline',
            state=ACTIVE,
            bootstyle=(DEFAULT,),
            foreground='gray',
        )

        self.widgets['label_toggle_keep_outline'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Toggle keep outline
        self.widgets['toggle_keep_outline'] = ttk.Checkbutton(
            self.frame_top_keep_outline,
            text="", 
            command=partial(self.event_invert_keep_outline), # TODO set the keep outline on or off
            state=ACTIVE,
            bootstyle=(DEFAULT, TOGGLE, ROUND)
        )
        
        self.widgets['toggle_keep_outline'].pack(
            side=TOP,
            ipadx=5,
            ipady=5,
            padx=1,
            pady=1,
        )

        self.widgets['toggle_keep_outline'].state(["selected"])

        # Vertical Splitter 
        name = 'separator_keep_scale'
        self.widgets[name] = ttk.Separator(
            self.frame_top,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=RIGHT, 
            fill=X,
            ipadx=4,
            #ipady=4,
            padx=1,
            #pady=1,
        )

        # frame for mask transp. label and scale
        self.frame_top_mask = ttk.Frame(self.frame_top, style=(DEFAULT))
        self.frame_top_mask.pack(fill=X, pady=1, side=RIGHT)

        # label
        self.widgets['label_mask_scale'] = ttk.Label(
            self.frame_top_mask,
            text='Mask Transparency',
            state=ACTIVE,
            bootstyle=(DEFAULT,),
            foreground='gray', 
        )

        self.widgets['label_mask_scale'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Mask Transparency Scale
        self.widgets['scale_mask'] = ttk.Scale(
            self.frame_top_mask,
            command=self.event_scale_mask_transparency_change,
            value=self.mask_transparency,  
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['scale_mask'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        ToolTip(self.widgets['scale_mask'], text="Transparency of Keep/Remove Masks")


        if self.feature_observ:
            # Vertical Splitter 
            name = 'separator_interp_scale'
            self.widgets[name] = ttk.Separator(
                self.frame_top,
                orient=VERTICAL,
                bootstyle=(DEFAULT),
            )
            self.widgets[name].pack(
                side=RIGHT, 
                fill=X,
                ipadx=4,
                #ipady=4,
                padx=1,
                #pady=1,
            )
            # frame for observ. transp. label and scale
            self.frame_top_observ = ttk.Frame(self.frame_top, style=(DEFAULT))
            self.frame_top_observ.pack(fill=X, pady=1, side=RIGHT)

            # label
            self.widgets['label_observ_scale'] = ttk.Label(
                self.frame_top_observ,
                text='Observ. Transparency',
                state=ACTIVE,
                bootstyle=(DEFAULT,),
                foreground='gray', 
            )

            self.widgets['label_observ_scale'].pack(
                side=TOP,
                ipadx=4,
                ipady=4,
                padx=1,
                pady=1,
            )

            # scale
            self.widgets['scale_observ'] = ttk.Scale(
                self.frame_top_observ,
                command=None, #self.event_scale_observ_transparency_change,  # Store the observ_transparency and make a method to handle it
                value=self.observ_transpareny,  
                state=ACTIVE,
                bootstyle=(DEFAULT,) 
            )

            self.widgets['scale_observ'].pack(
                side=TOP,
                ipadx=4,
                ipady=4,
                padx=1,
                pady=1,
            )

            ToolTip(self.widgets['scale_observ'], text="Transparency of observation(s)")

        # interp. transp. Vertical Splitter 
        name = 'separator_mid'
        self.widgets[name] = ttk.Separator(
            self.frame_top,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=RIGHT, 
            fill=X,
            ipadx=4,
            #ipady=4,
            padx=1,
            #pady=1,
        )

        # INFUTURE 
        # Do this during registation and have different modes for app in types.
        # IF there are plugins that generate an interp
        # TODO does this break the rendering as it needs the value from scale????
        # interp_generated = False
        # for plug in self.avaliable_plugins:
        #     if self.avaliable_plugins[plug].type_interp == True:
        #         interp_generated = True
        #         break
        if self.feature_interp:
            # frame for interp. transp. label and scale
            self.frame_top_interp = ttk.Frame(self.frame_top, style=(DEFAULT))
            self.frame_top_interp.pack(fill=X, pady=1, side=RIGHT)

            # label
            self.widgets['label_interp_scale'] = ttk.Label(
                self.frame_top_interp,
                text='Interp. Transparency',
                state=ACTIVE,
                bootstyle=(DEFAULT,),
                foreground='gray', 
            )

            self.widgets['label_interp_scale'].pack(
                side=TOP,
                ipadx=4,
                ipady=4,
                padx=1,
                pady=1,
            )

            # scale
            self.widgets['scale_interp'] = ttk.Scale(
                self.frame_top_interp,
                command=self.event_scale_interp_transparency_change,
                value=self.interp_transparency,  
                state=ACTIVE,
                bootstyle=(DEFAULT,) 
            )

            self.widgets['scale_interp'].pack(
                side=TOP,
                ipadx=4,
                ipady=4,
                padx=1,
                pady=1,
            )

            ToolTip(self.widgets['scale_interp'], text="Transparency of Interpretation(s)")

            # Vertical Splitter 
            name = 'separator_end'
            self.widgets[name] = ttk.Separator(
                self.frame_top,
                orient=VERTICAL,
                bootstyle=(DEFAULT),
            )
            self.widgets[name].pack(
                side=RIGHT, 
                fill=X,
                ipadx=4,
                #ipady=4,
                padx=1,
                #pady=1,
            )

        # Button Show / Hide Explorer
        parent = self.frame_top
        self.ui_images['explorer'] = self.ui_images_raw['explorer'].resize((
            self.config.button_layout_width, 
            self.config.button_layout_height
        ))
        self.ui_images['explorer'] = PIL.ImageTk.PhotoImage(self.ui_images['explorer'])

        self.widgets['button_explorer'] = ttk.Button(
            parent,
            text=None, 
            command=self.event_treeview_explorer_show_hide, 
            image=self.ui_images['explorer'], 
            state=ACTIVE,
            bootstyle=(SECONDARY,) 
        )

        special_config = copy.copy(self.config.standard_button_view)
        special_config['side'] = LEFT
        special_config['padx'] = 7
        self.widgets['button_explorer'].pack(
            special_config
        )

        ToolTip(self.widgets['button_explorer'], text="Show/Hide Explorer For Current Directory and/or Images.")

    def make_frame_top_seperator_widgets(self):
        # top_seperator
        self.widgets['Separator_top'] = ttk.Separator(
            self.frame_top_seperator,
            orient=HORIZONTAL,
            bootstyle=(SECONDARY),
        )
        
        self.widgets['Separator_top'].pack(side=BOTTOM, fill=X)

    def make_frame_tools_widgets(self):
        print('start making button tool from plugins')
        for _, plugin in self.avaliable_plugins.items():
            print('Plugins from dict:', _, plugin)
            plugin(config=self.config).make_button_tool(self, self.frame_tools)
        print('start making button tool from plugins')

    def make_frame_explorer_widgets(self):  
        # If there is not an explorer make but don't pack yet   
        if not self.widgets.get('treeview_explorer', False):
            side = LEFT 
            _style = DEFAULT
            parent = self.frame_explorer

            # Vertical Separator
            self.widgets['separator_explorer_vertical_left'] = ttk.Separator(
                self.frame_explorer,
                orient=VERTICAL,
                bootstyle=(DEFAULT),
            )


            # label explorer
            self.widgets['label_explorer'] = ttk.Label(
                parent,
                text='Explorer',
                state=ACTIVE,
                bootstyle=(_style,),
            )

            # Horizontal Separator
            self.widgets['separator_explorer_start'] = ttk.Separator(
                parent,
                orient=HORIZONTAL,
                bootstyle=(_style),
            )

            # Explorer Treeview
            name = 'treeview_explorer'
            self.widgets[name] = ttk.Treeview(
                parent, 
                show='tree',
                selectmode=BROWSE,
                style=_style,
            )

            self.widgets[name].tag_configure("disabled_row", 
                                            background=self.style.colors.get('danger'), 
                                            foreground="black")
            
            self.widgets[name].insert('',  'end', 'default', text='Starting Default File', open=False)
            self.widgets[name].insert('default',  'end', 'default_rgb', text='Default File RGB', open=True)
            self.widgets[name].insert('default',  'end', 'default_dip', text='Default File DIP', open=True)

            self.widgets[name].bind('<ButtonRelease-1>', self.event_treeview_explorer_select)
            self.widgets[name].pack(side=side, fill=BOTH, pady=2, padx=2)
            self.widgets[name].column('#0', width=240, anchor='w')

            # Treeview vertical scrollbar
            name = 'scrollbar_treeview_explorer'
            self.widgets[name]= ttk.Scrollbar(
                parent,
                orient=VERTICAL,
                command=self.widgets['treeview_explorer'].yview,
                style=(_style, ROUND),
            )

            self.widgets['treeview_explorer'].configure(yscrollcommand=self.widgets['scrollbar_treeview_explorer'].set)

        # If the explorer should be shown, pack all the elements
        if self.config.show_explorer:
            # Vertical Separator
            self.widgets["separator_explorer_vertical_left"].pack(
                side=RIGHT, 
                fill=Y,
                ipadx=1,
                ipady=1,
                padx=1,
                pady=1,
            )

            # Label explorer
            self.widgets['label_explorer'].pack(
                side=TOP,
                ipadx=4,
                ipady=4,
                padx=1,
                pady=1,
            )

            # Horizontal seperator
            self.widgets['separator_explorer_start'].pack(
                side=TOP, 
                fill=X,
                #ipadx=4,
                ipady=4,
                #padx=1,
                pady=1,
            )

            # Explorer Treeview
            name = 'treeview_explorer'
            self.widgets[name].pack(side=LEFT, fill=BOTH, pady=2, padx=2)
            
            # Treeview vertical scrollbar
            name = 'scrollbar_treeview_explorer'
            self.widgets[name].pack(
                side=LEFT, 
                fill=Y, 
                ipadx=2,
                ipady=2,
                padx=2,
                pady=2,
            )

            # Don't know if we really need this
            self.frame_explorer.pack(side=LEFT, fill=Y, padx=1, pady=1)
        else:
            # Hide all these widgets... but keep the frame
            for widget in self.frame_explorer.winfo_children():
                widget.forget()

            # Create a fake wdigets so frame_explorer is resized
            l = ttk.Label(self.frame_explorer, font=(NONE, 1)).pack(side=BOTTOM)

    def make_frame_explorer_seperator_widgets(self):
        # Vertical Separator
        name = 'separator_explorer_Vertical'
        self.widgets[name] = ttk.Separator(
            self.frame_explorer_seperator,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=LEFT, 
            fill=Y,
            ipadx=1,
            ipady=1,
            padx=1,
            pady=1,
        )

    def make_frame_view_widgets(self):
        parent = self.frame_view
        side = TOP

        # Upper label
        name = "label_view_upper"
        text = "Nothing loaded"
        self.widgets[name] = ttk.Label(
            parent,     
            text=text,
            borderwidth=2,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            fill=BOTH,
            expand=True,
            side=side,
        )
    
        # Lower label
        name = "label_view_lower"
        text = "Nothing loaded"
        self.widgets[name] = ttk.Label(
            parent,     
            text=text,
            borderwidth=2,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            fill=BOTH,
            expand=True,
            side=side,
        )

        # TODO - Move to plugin
        # Create plugin context aware popup menu - especially for setting RockType / Color
        self.widgets['popup_menu_view'] = ttk.Menu(self, tearoff=0)

        # Use this function to set the correct view, either single or dual
        # self.old_dual_value = False  # Always start with the wrong state, to force placement
        self.set_view_dual()

        # Event Bindings for the MainView.Label only
        widget = self.widgets['label_view_upper']
        widget.bind('<Button-1>', self.event_mouse)  # Left hand mouse button pressed
        widget.bind('<ButtonRelease-1>', self.event_mouse)  # Left hand mouse button released
        #widget.bind('<Button-2>', self.event_mouse)  # Right mouse button pressed
        widget.bind('<ButtonRelease-2>', self.event_mouse_button_2)  # Right mouse button released
        widget.bind('<Motion>', self.event_mouse_motion)
        widget.bind('<MouseWheel>', self.event_mouse)

        # Event Bindings for the MainView.Label_lower only
        widget = self.widgets['label_view_lower']
        widget.bind('<Button-1>', partial(self.event_mouse, over_secondary=True))  # Left hand mouse button pressed
        widget.bind('<ButtonRelease-1>', partial(self.event_mouse, over_secondary=True))  # Left hand mouse button released
        #widget.bind('<Button-2>', partial(self.event_mouse, over_secondary=True))  # Right mouse button pressed
        widget.bind('<ButtonRelease-2>', self.event_mouse_button_2)  # Right mouse button released
        widget.bind('<Motion>', self.event_mouse_motion_secondary)
        widget.bind('<MouseWheel>', partial(self.event_mouse, over_secondary=True))

        # Bind to the frame not the label/s
        self.bind('<Configure>', self.event_configure)

    def make_frame_plugins_seperator_widgets(self):
        # top_seperator
        self.widgets['Separator_plugins'] = ttk.Separator(
            self.frame_plugins_seperator,
            orient=VERTICAL,
            bootstyle=(SECONDARY),
        )
        
        self.widgets['Separator_plugins'].pack(side=RIGHT, fill=Y)
    
    def make_frame_treeview_widgets(self):
        parent = self.frame_treeview
        side = LEFT 

        # label Plugins
        self.widgets['label_Plugins'] = ttk.Label(
            parent,
            text='Plugins',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_Plugins'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Horizontal Separator
        name = 'separator_plugin_start'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )


        # Plugin Treeview
        name = 'treeview'
        self.widgets[name] = ttk.Treeview(
            parent, 
            show='tree',
            selectmode=BROWSE,
        )

        self.widgets[name].tag_configure("disabled_row", 
                                         background=self.style.colors.get('danger'), 
                                         foreground="black")
        
        self.widgets[name].insert('',  'end', 'local_plugins', text='Local', open=True)
        self.widgets[name].insert('', 'end', 'global_plugins', text='Global', open=True)
        self.widgets[name].bind('<ButtonRelease-1>', self.event_treeview_select)
        self.widgets[name].bind("<Shift-Button-1>", self.event_treeview_shift_select)
        self.widgets[name].bind("<Delete>", self.event_properties_button_delete)
        self.widgets[name].pack(side=side, fill=BOTH, pady=2, padx=2)
        self.widgets[name].column('#0', width=240, anchor='w')

        # Treeview vertical scrollbar
        name = 'scrollbar_treeview'
        self.widgets[name]= ttk.Scrollbar(
            parent,
            orient=VERTICAL,
            command=self.widgets['treeview'].yview,
            style=(PRIMARY, ROUND),
        )
        self.widgets[name].pack(
            side=side, 
            fill=Y, 
            ipadx=2,
            ipady=2,
            padx=2,
            pady=2,
            )

        self.widgets['treeview'].configure(yscrollcommand=self.widgets['scrollbar_treeview'].set)

    def make_frame_bottom_widgets(self):
        parent = self.frame_bottom
        side = LEFT

        # Meter Working Label
        name = "label_working"
        text = "Busy"
        self.widgets[name] = ttk.Label(
            parent,     
            text=text,
            bootstyle=(DEFAULT),
            foreground='gray',
        )
        self.widgets[name].pack(
            side=side,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

        # Meter to show things are working and busy
        self.widgets['meter_working'] = ttk.Meter(
            parent,
            bootstyle=SECONDARY, 
            metertype=FULL, 
            metersize=45, 
            wedgesize=90, 
            amountused=0,
            interactive=False,
            showtext=False,
            subtext="",
            subtextfont=(None, 1)
        )
        self.widgets['meter_working'].pack(
            side=LEFT,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

        # Separator
        name = 'Separator_bottom_meter_ram'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=side, 
            fill=X
        )

        # Meter to show how much RAM the system has avaliable
        self.widgets['meter_ram'] = MeterRAM(
            parent,
            size=45,
        )
        self.widgets['meter_ram'].pack(
            side=LEFT,
        )
        # self.widgets['meter_ram'].meter.update()
        # self.widgets['meter_ram'].get_ram_from_system()

        # Separator
        name = 'Separator_bottom_meter'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=side, 
            fill=X
        )

        # First Status Label
        name = "label_status_images"
        text = "Loaded: Default Image"
        self.widgets[name] = ttk.Label(
            parent,     
            text=text,
            bootstyle=(DEFAULT),
            foreground='gray',
        )
        self.widgets[name].pack(
            side=side,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

        # # Separator
        name = 'Separator_bottom'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=VERTICAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=side, 
            fill=X
        )

        # Second Status Label
        name = "label_status_plugins"
        text = ""
        self.widgets[name] = ttk.Label(
            parent,     
            text=text,
            bootstyle=(DEFAULT),
            foreground='gray',
        )
        self.widgets[name].pack(
            side=side,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

    def make_menu(self):
        root_menu = ttk.Menu(self)
        root_menu.delete(0)

        menu_file = ttk.Menu(root_menu, tearoff='off')
        menu_recent = ttk.Menu(menu_file, tearoff='off')
        menu_copy_merge = ttk.Menu(root_menu, tearoff='off')
        menu_about = ttk.Menu(root_menu, tearoff='off')
        root_menu.add_cascade(label="File", menu=menu_file)
        # Remove for now.
        # root_menu.add_cascade(label="Copy and Merge", menu=menu_copy_merge)
        root_menu.add_cascade(label="About", menu=menu_about)

        # Recent sub menu
        path = self.config.recent_path_0
        menu_recent.add_command(
            label=path, 
            command=partial(self.event_open_recent, path)    
        )
        path = self.config.recent_path_1
        menu_recent.add_command(
            label=path, 
            command=partial(self.event_open_recent, path)    
        )
        path = self.config.recent_path_2
        menu_recent.add_command(
            label=path, 
            command=partial(self.event_open_recent, path)    
        )

        # File 
        menu_file.add_command(
            label="Open Image(s)", 
            command=self.event_file_open_images
        )
        menu_file.add_command(
            label="Open Image Directory", 
            state=ACTIVE,
            command=self.event_file_open_image_directory,
        )
        # Not Yet Implemented
        # menu_file.add_cascade(
        #     label="Open Recent", 
        #     state=ACTIVE,
        #     menu=menu_recent,
        # )
        menu_file.add_separator()        
        menu_file.add_command(
            label="Open Settings", 
            state=ACTIVE,
            command=self.event_file_open_settings
        )
        menu_file.add_command(
            label="Save Settings", 
            state=ACTIVE,
            command=self.event_file_save_settings
        )
        menu_file.add_separator()
        menu_file.add_command(
            label="Import Mask", 
            state=ACTIVE,
            command=self.event_file_import_mask
        )
        menu_file.add_command(
            label="Export Mask", 
            state=ACTIVE,
            command=self.event_file_export_mask
        )
        menu_file.add_command(
            label="Export Mask Applied to Image", 
            state=DISABLED,
            command=self.event_file_export_mask_applied
        )
        menu_file.add_separator()
        menu_file.add_command(
            label="Import Observ.", 
            state=DISABLED,
            command=None,
        )
        menu_file.add_command(
            label="Export Observ.", 
            state=DISABLED,
            command=None
        )
        menu_file.add_command(
            label="Export Observ. Applied to Image", 
            state=DISABLED,
            command=None
        )
        menu_file.add_separator()
        menu_file.add_command(
            label="Import Interp.", 
            state=DISABLED,
            command=None,
        )
        menu_file.add_command(
            label="Export Interp.", 
            state=DISABLED,
            command=None
        )
        menu_file.add_command(
            label="Export Interp. Applied to Image", 
            state=DISABLED,
            command=None
        )
        menu_file.add_separator()
        menu_file.add_command(label='Exit', command=self.event_close)

        # Copy And Merge
        menu_copy_merge.add_command(label="Show Copy and Merge Dialog", command=self.event_copy_merge)

        # About
        menu_about.add_command(label="More Information", command=self.event_about_more_information)

        # Attach to main window
        self.window['menu'] = root_menu

    def make_properties_start(self, Disabled=True):
        parent = self.frame_properties

        if Disabled:
            state = DISABLED
        else:
            state = ACTIVE

        # Horizontal Separator
        name = 'separator_properties_start'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

        # Label Name
        plugin_id = self.current_plugin_instance
        self.widgets['label_properties_name'] = ttk.Label(
            parent,
            text=self.plugins[plugin_id].text_name,
            state=state,
            bootstyle=(DEFAULT,) 
        )

        self.widgets['label_properties_name'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Horizontal Separator
        name = 'separator_properties_end'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=HORIZONTAL,
            bootstyle=(DEFAULT),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

        # Active Checkbox
        # Uses a active_change dedicated event handler, not generic handler
        self.widgets['checkbutton_properties_active'] = ttk.Checkbutton(
            parent,
            command=partial(self.event_properties_active_change, 'changed'),
            text='Active',
            bootstyle=(SECONDARY, TOGGLE, ROUND),
        )

        if self.plugins[plugin_id].params.get('Active', False):
            self.widgets['checkbutton_properties_active'].state(['selected'])
        else:
            self.widgets['checkbutton_properties_active'].state(['!selected'])

        self.widgets['checkbutton_properties_active'].pack(
            side=TOP,
            ipadx=4,
            ipady=4,
            padx=1,
            pady=1,
        )

        # Horizontal Separator
        name = 'separator_properties_end2'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=HORIZONTAL,
            bootstyle=(PRIMARY),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            #ipadx=4,
            ipady=4,
            #padx=1,
            pady=1,
        )

    def make_properties_end(self, Disabled=True, Show_Apply=True):

        # TODO
        # Can this method know which plugin is calling and thus if it needs apply button
        needs_apply = False
        if self.avaliable_plugins[self.current_plugin_type].type_needs_apply:
            needs_apply = True

        parent = self.frame_properties
        button_ipadx = 34

        if Disabled:
            state = DISABLED
        else:
            state = ACTIVE

        # Horizontal Separator
        name = 'separator_properties_end'
        self.widgets[name] = ttk.Separator(
            parent,
            orient=HORIZONTAL,
            bootstyle=(PRIMARY),
        )
        self.widgets[name].pack(
            side=TOP, 
            fill=X,
            ipadx=2,
            ipady=2,
            padx=2,
            pady=2,
        )

        # Button Apply
        if needs_apply:
            self.widgets['button_properties_apply'] = ttk.Button(
                parent,
                text="Apply", 
                command=partial(self.event_properties_button_apply, True), 
                image=None, 
                state=state,
                bootstyle=(SUCCESS,) 
            )

            self.widgets['button_properties_apply'].pack(
                side=LEFT,
                fill=X,
                expand=True,
                ipadx=button_ipadx,
                ipady=2,
                padx=2,
                pady=2,
            )

            ToolTip(self.widgets['button_properties_apply'], text="Apply")

        # In future use this to create an 'undo' system
        # At this time not needed
        # # Button Cancel
        # self.widgets['button_properties_cancel'] = ttk.Button(
        #     parent,
        #     text="Cancel", 
        #     command=partial(self.event_properties_button_cancel, True), 
        #     image=None, 
        #     state=state,
        #     bootstyle=(SECONDARY,) 
        # )

        # self.widgets['button_properties_cancel'].pack(
        #     side=LEFT,
        #     fill=X,
        #     ipadx=button_ipadx,
        #     ipady=2,
        #     padx=2,
        #     pady=2,
        # )

        # ToolTip(self.widgets['button_properties_cancel'], text="Cancel")

        # Button Delete
        self.widgets['button_properties_delete'] = ttk.Button(
            parent,
            text="Delete", 
            command=partial(self.event_properties_button_delete, True), 
            image=None, 
            state=state,
            bootstyle=(WARNING,) 
        )

        self.widgets['button_properties_delete'].pack(
            side=LEFT,
            fill=X,
            expand=True,
            ipadx=button_ipadx,
            ipady=2,
            padx=2,
            pady=2,
        )

        ToolTip(self.widgets['button_properties_delete'], text="Delete")
    #endregion

    #region event handlers
    def event_file_open_images(self, path=None):
        print('event_file_open_images')

        if path == None:
            from_dialog = []
            from_dialog.append(
                filedialog.askopenfilename(
                    title='Open RGB or Dip file', 
                    initialdir='', 
                    filetypes=self.config.image_filetypes
                )
            )
        else:
            from_dialog = path

        # Check in case user cancelled out of dialog, don't load anything if they cancelled
        if from_dialog != ['']:
            # hide the explorer - it is confusing if there is a single image set loaded
            # Do this first because of layout issues if done after update
            self.event_treeview_explorer_show_hide(force='hide')

            self.open_image_set(from_dialog)

            # Future: Check the image openned 
            self.update_recent_paths(from_dialog[0])

            # Update the Explorer with only one image set
            self.update_explorer_file(self.images.paths[self.config.rgb])

    def event_file_open_image_directory(self, path=None):
        print('event_file_open_image_directory')

        if path == None:
            from_dialog = []
            from_dialog.append(
                filedialog.askdirectory(
                    title='Open Directory to RGB and DIP files', 
                    initialdir='', 
                )
            )
        else:
            from_dialog = path

        # Get all the images from directory that have RGB or rgb in the name
        if from_dialog[0]:
            self.directory_path = from_dialog[0]

            # Get all the files in the directory
            files = [f for f in os.listdir(self.directory_path) if
                         os.path.isfile(os.path.join(self.directory_path, f))]

            # get only files with _RGB. in title
            search = '_RGB.'
            rgb_files = [i for i in files if search in i]

            # and then only files with match image extensions
            accepted_formats = self.config.accepted_formats
            rgb_imgs = []
            for file in rgb_files:
                if file.rsplit('.', 1)[-1] in accepted_formats:
                    rgb_imgs.append(file)

            #for image_path in glob.glob(self.config.resources_path + "*.png"):

            if len(rgb_imgs) == 0:
                messagebox.showerror(title='Error: Directory Not Loaded.',
                                        message=f'Directory does not contain images with" \
                                                "{search}", before filename extension.')
            else:
                # Order the files
                rgb_imgs.sort()

                # Future: Check the image openned 
                self.update_recent_paths(from_dialog[0])

                # save the files for later and then open the first file
                self.rgb_file_names = rgb_imgs
                self.current_rgb_file = self.rgb_file_names[0]
                
                # Update explorer to match found files
                self.update_explorer_directory(self.rgb_file_names)

                # Get the first images set by name and open it
                first_file_path = self.directory_path + '/' + self.current_rgb_file
                self.open_image_set([first_file_path])

                # Show the explorer
                self.event_treeview_explorer_show_hide(force='show')

    def event_open_recent(self, path):
        print(f'event_open_recent | {path}')

        # Decide if file (for image set) or directory (for directory of images) to open
        file = True
        # TODO how to tell if path is directory - if it doesnt have a file extension?


        if os.path.isfile(path):
            # Open files
            self.event_file_open_images([path])
        elif os.path.isdir(path):
            # Open Directory
            self.event_file_open_image_directory([path])
        else:
            # Error
            messagebox.showerror('File Error!', 'File Error! \n' + 'Error loading path.')
            self.widgets["label_status_images"].config(text=f'Status: Error loading path.')

    def event_file_open_settings(self):
        print('event_file_open_settings')

        # TODO
        # path exists needs dictionary

        dia_result = {'file':None}
        dia_result['file'] = filedialog.askopenfilename(
            title='Open Settings File', 
            initialdir='', 
            filetypes=[('RockBase Format files', '*.rbf'), ('All files', '*.*')]
        )

         # Check incase user cancelled out of dialog, don't load anything if they cancelled
        if not dia_result['file'] == '':
            self.meter_working_start()
            self.widgets["label_status_images"].config(text=f'Status: Loading Settings...')
            self.widgets["label_status_images"].update()

            # Load settings in reverse to how they were saved...
            # open a file, where you stored the pickled data

            # Check if the file exists before trying to open
            files_exist, message = self.images.paths_exist(dia_result, '.rbf')
            # If it doesn't show error and return
            if not files_exist:
                messagebox.showerror('File Error!', 'File Error! \n' + message)
                self.widgets["label_status_images"].config(text=f'Status: Error Loading Settings')
                self.meter_working_stop()
                return

            # Load/open information from that file
            settings = pickle.load(gzip.open(dia_result['file'], 'rb'))
            print('From Pickled. Load Settings:',settings)

            # In future could do further checking of the format
            # For now just look for the correct text return of not found...
            if settings['file_type'] != 'RockBase Format' and settings['format_version'] < 4:
                messagebox.showerror('File Error!', 'File Error! \n' + 'Wrong settings file format.')
                self.widgets["label_status_images"].config(text=f'Status: Error Loading Settings')
                self.meter_working_stop()
                return

            # INFUTURE
            # [ ] Also warn user if current settings are not saved as they will be overwritten
            #     Or always ask the user to save existing settings before opening new...if plugins exist
            # [ ] Re-apply all global plugins

            self.plugins.clear()
            self.plugin_next_id = 0
            for plugin in settings['plugins']:
                # TODO Do we need to figure out how to force the type?
                
                # Need to check if plugin type is avaliable 
                plugin_type = settings['plugins'][plugin]['type']
                plugin_params = settings['plugins'][plugin]['params']
                if plugin_type in self.avaliable_plugins:
                    plugin_id = self.create_new_plugin_from_file(
                        plugin_type=plugin_type, 
                        plugin_params=plugin_params,
                    )
                    self.plugins[plugin_id].prepare_load(settings['plugins'][plugin])

                    # Force the internal plugin id (out of date) to match external (current instance)
                    self.plugins[plugin_id].id = plugin_id

                    # Force the treeview to have correct text name
                    if not type(self.plugins[plugin_id]).__name__ == 'PanZoom':
                        self.widgets['treeview'].item(plugin_id, text=self.plugins[plugin_id].text_name)
                        print('Loading settings: ',self.plugins[plugin_id].text_name)
                else:
                    # Dispaly warning saying plugin type not supported in this version of 
                    messagebox.showerror('Plugin Error!', 'Plugin Error! \n' + f'{plugin_type} is not supported.')

            # If plugins were loaded, finish up by clearing all the intermediate masks and applying the new plugins 
            self.change_existing_plugin(plugin_type=self.plugin_default, plugin_id='PanZoom')
            if len(self.plugins) > 1:
                self.images.delete_layers_not_drawn()
                self.plugins_apply_all()
            self.update_view()
            self.widgets['label_status_images']['text'] = f'Loaded: {dia_result["file"].rsplit("/", 1)[1]}'
            self.meter_working_stop()

    def event_file_save_settings(self):
        print('event_file_save_settings')

        # We are likely to be busy working so warn user
        self.meter_working_start()

        # Guard Clause
        if len(self.plugins) == 0:
            # Show message no plugins to save
            messagebox.ok("There are no plugins currently avaliable to save.",
                                "No Plugins to Save.",
                                alert=True)
            self.meter_working_stop()
            return
        
        # Show the save dialog 
        filename_ = "settings.rbf"
        if not self.runnnig_on_mac():
            file_types = [('RockBase Format files', '*.rbf'), ('All files', '*.*')]
            dlg_result = filedialog.asksaveasfilename(initialfile=filename_, defaultextension=file_types)
        else:
            dlg_result = filedialog.asksaveasfilename(initialfile=filename_)

        if dlg_result == "":  # user cancelled out of the dialog
            self.widgets["label_status_images"].config(text=f'Status: User cancelled out of Save Settings Dialog.')
            self.meter_working_stop()
            return
        else:
            print('From Dialog', dlg_result)

        # Save the settings 
        # TODO: Make this a json file in the future
        self.widgets["label_status_images"].config(text=f'Status: Preparing Settings...')
        settings = {'file_type':'RockBaseFormat', 'format_version': 4}
        settings['plugins'] = {}

        # TODO Dump manual masks from inside the manualdraw plugin
        for plugin in self.plugins:
            settings['plugins'][plugin] = self.plugins[plugin].prepare_save()

        if dlg_result:
            with gzip.open(dlg_result, 'wb') as output_file:
                pickle.dump(settings, output_file)
        
        self.widgets["label_status_images"].config(text=f'Status: Settings Saved to {dlg_result.split("/")[-1]}')  
        self.meter_working_stop()  

    def event_file_import_mask(self):
        # TODO 
        # 25 Mar 2023: Start here. Get this finished...
        print('event_file_import_mask')

        self.meter_working_start()

        dia_result = None
        dia_result = filedialog.askopenfilename(
            title='Import Mask File', 
            initialdir='', 
            filetypes=self.config.image_filetypes,
        )

        path = {
            self.config.drwmsk : self.config.blank_image_path
        }

         # Check incase user cancelled out of dialog, don't load anything if they cancelled
        if dia_result == '':
            self.widgets["label_status_images"].config(text=f'Status: User cancelled out of dialog')
            self.meter_working_stop()
            return  
        else:
            self.widgets["label_status_images"].config(text=f'Status: Importing Mask...')
            self.widgets["label_status_images"].update()

            print('Load the image and put into drwmsk plugin')            
            # Check file includes the msk or MSK at the end of file name
            extension = dia_result.rsplit('_', 1)[-1][:3]
            if extension == 'MSK':
                path[self.config.drwmsk] = dia_result
            elif extension == 'msk':
                path[self.config.drwmsk] = dia_result
            else:
                messagebox.showerror('File Error!', 'File Error! \n' + 'A mask file name must include "_MSK" before the extension.')
                self.widgets["label_status_images"].config(text=f'Status: Error Loading Settings')
                self.meter_working_stop()
                return    
            
             # TODO Create a drwmsk layer to put the image into
            # Where to start with creating a drawn mask plugin...
            # [√] Try using the create plugin from file
            # [√] How to get the system to load into layer? 
            # Do we need to invert the image? 
            # If so why? 
            # Is it inverted when it is exported?

            # Create the plugin to put the loaded mask into...
            plugin_id = self.create_new_plugin_from_file(plugin_type="DrawMask")

            # load single image. Check path size, if file exists and image size during loading
            files_ok, message = self.images.load_single(path=path)
            if not files_ok:
                # Show error and return
                messagebox.showerror('File Error!', 'File Error! \n' + message)
                self.widgets["label_status_images"].config(text=f'Status: Error Loading Mask')
                self.meter_working_stop()

                # TODO: In future better to also delete the DrawMask plugin 

                return     
            
            # Force the loaded image into the newly create plugin 
            self.images._inter_msk[plugin_id] = self.images._in[self.config.drwmsk]


            self.update_view()
            self.widgets['label_status_images']['text'] = f'Loaded: {self.images.paths[self.config.rgb].rsplit("/", 1)[1]}'
            self.meter_working_stop()
        
    def event_file_export_mask(self):
        print('event_file_export_mask')

        self.meter_working_start()

        # Create name
        filename_root = self.images.paths[self.config.rgb].split("/")[-1]
        filename_ = filename_root.replace('RGB', 'MSK')

        if not self.runnnig_on_mac():
            file_types = [('Image files', '*.tif'), ('All files', '*.*')]
            dlg_result = filedialog.asksaveasfilename(initialfile=filename_, defaultextension=file_types)
        else:
            dlg_result = filedialog.asksaveasfilename(initialfile=filename_)

        if dlg_result == "":  # user cancelled out of the dialog
            self.widgets["label_status_images"].config(text=f'Status: User cancelled out of Save Dialog.')
            self.meter_working_stop()
            return
        else:
            print('From Dialog', dlg_result)

            # Get the blur and threshold settings if they exists
            blur = 1
            threshold = 0.5
            for plugin in self.plugins:
                if type(self.plugins[plugin]).__name__ == 'FinalSmooth' and \
                    self.plugins[plugin].params['Active']:
                    blur = self.plugins[plugin].params['Blur'] * 255
                    threshold = self.plugins[plugin].params['Threshold'] * 255
                    print("Blur value", blur)
            short_name = dlg_result.split("/")[-1]
            
            self.widgets["label_status_images"].config(text=f'Status: Starting to Export... {short_name}')
            self.widgets["label_status_images"].update()

            self.images.export_mask(
                path=dlg_result, 
                threshold=threshold, 
                blur=blur
            )
            
            self.widgets["label_status_images"].config(text=f'Status: Mask Exported {short_name}')
            self.meter_working_stop()

    def event_file_export_mask_applied(self):
        print('event_file_export_mask_applied')

    def event_copy_merge(self):
        CopyMergeDialog(images=self.images, config=self.config)

    def event_about_more_information(self):
        Splash(disappear_automatically=False)
    
    def event_treeview_select(self, selected):
        current_focus = self.widgets['treeview'].focus()
        print(f"Click treeview: {selected, current_focus}")
        print(self.plugins[current_focus])
        plugin_type = type(self.plugins[current_focus]).__name__
        self.change_existing_plugin(plugin_type, plugin_id=current_focus)

    def event_treeview_shift_select(self, selected):
        focus_plugin = self.widgets['treeview'].focus()
        print(f"Click treeview: {selected, focus_plugin}")
        print(self.plugins[focus_plugin])

        plugin_type = type(self.plugins[focus_plugin]).__name__
        self.change_existing_plugin(plugin_type, plugin_id=focus_plugin)

        self.plugins[focus_plugin].params['Active'] = not self.plugins[focus_plugin].params['Active']

        # Highlight the disabled state as red
        if not self.plugins[focus_plugin].params['Active']:
            self.widgets['treeview'].item(focus_plugin, tag='disabled_row')
        else:
            self.widgets['treeview'].item(focus_plugin, tag="")
    
        self.update_view()

    def event_invert_theme(self, property, value):
        print("event_theme_toggle_change", property, value)
        self.config.dark_theme = not self.config.dark_theme

        if self.config.dark_theme:
            self.style.load_user_themes('./resources/darkly-gray.json')
            self.style.theme_use('darkly-gray')
        else:
            self.style.theme_use('flatly')

    def event_invert_keep_outline(self):
        print(f"event_invert_keep_outline | new keep outline: {not self.keep_outline}")
        self.keep_outline = not self.keep_outline
        self.update_view()

    def event_button_tool(self, plugin_type):
        # Create and apply (create calls apply)
        self.create_new_plugin_from_tool(plugin_type=plugin_type)

    def event_change_view(self, view):
        print(f'change view: {view}')
        self.config.view = view

        if self.config.view == View.SINGLE:
            self.set_view_single()
        elif self.config.view == View.DOUBLE:
            self.set_view_dual()

        self.update_view()

    def event_three_d_view(self):
        # Show the 3D view of outcrop based on the .obj model...
        # TODO: Figure out all the loading...
        import subprocess
        #path_to_3d = "/Users/johnwood/VSCodeProjects/workspace_access_obj/AAA_open_obj_text_working.py"
        # path_to_3d = "/Users/johnwood/VSCodeProjects/workspace_access_obj/test_python"
        #               #/Users/johnwood/VSCodeProjects/workspace_access_obj/test_python.py
        # subprocess.call(['python', '-m', path_to_3d])
        #path = "/Users/johnwood/Documents/PhD/_Subproject 2 - RockAnything/VSCode/Rock3D/output/AAA_open_obj_text_working.app"
        command = ["open", "-n", "./AAA_open_obj_text_working.app"]
        subprocess.call(command)

    def event_treeview_explorer_show_hide(self, force=None):    
        if self.config.show_explorer or force=='hide':
            self.config.show_explorer = False
            self.make_frame_explorer_widgets()
        elif not self.config.show_explorer or force=='show':
            self.config.show_explorer = True
            self.make_frame_explorer_widgets()

        print(f"event_show_hide_explorer | Show: {self.config.show_explorer} ")

    def event_treeview_explorer_select(self, value):
        treeview_focus = self.widgets['treeview_explorer'].focus()

        # Strip rgb or dip from treeview focus end, if child node is selected
        text_end = treeview_focus[treeview_focus.rfind('.'):] 
        if len(text_end) > 5:
            treeview_focus = treeview_focus[:-3]


        print(f"event_treeview_explorer_select | Current Focus {treeview_focus} | Value {value}")

        if self.current_rgb_file == treeview_focus:
            return # ignore the users request as already in place
        else:
            print("Avalialbe Files", self.rgb_file_names)

            # Open the image set that corresponds with current focus
            self.current_rgb_file = treeview_focus
            first_file_path = self.directory_path + '/' + treeview_focus
            self.open_image_set([first_file_path])

    def event_scale_mask_transparency_change(self, event):
        print(f'event_scale_mask_transparency_change {event}')
        self.mask_transparency = float(event)
        self.update_view()

    def event_scale_interp_transparency_change(self, event):
        print(f'event_scale_interp_transparency_change {event}')
        self.interp_transparency = 1 - float(event)
        self.update_view()

    def event_properties_button_apply(self, value):
        self.plugin_apply_with_ui_updates(value)
        self.update_view()
    
    # def event_properties_button_cancel(self, value):
    #     # INFUTURE - Allow the users to undo the change params
    #     # What happens here?
    #     # The current plugins parameters are put back to what they were before the changes
    #     print('event_properties_button_cancel', value)

    def event_properties_button_delete(self, value=None):
        current_selection = self.widgets['treeview'].focus()
        if current_selection != '':
            result = Messagebox.okcancel(
                "Are you sure you want to delete the selected plugin?",                        
                "Are you sure?",
                alert=True,
            )
            print('Messagebox', result)
            if result == "OK":        
                self.plugins[current_selection].delete_mask_or_interp()
                self.widgets['treeview'].delete(current_selection)
                del self.plugins[current_selection]
                # Set state to pan zoom, which will also remove the old widgets from deleted plugin instance
                self.change_existing_plugin(plugin_type=self.plugin_default, plugin_id='PanZoom')
                self.update_view()
                print(f'event_properties_button_delete|delete_mask|treeview_plugin|{current_selection}')

    def event_properties_active_change(self, value):
        print('event_properties_active_change ACTIVE ONLY:', value)

        focus_plugin = self.widgets['treeview'].focus()
        print('Current focus_plugin:', focus_plugin)

        checkbox_state = self.widgets['checkbutton_properties_active'].instate(['selected'])
        self.plugins[focus_plugin].params['Active'] = checkbox_state

        # Highlight the disabled state as red
        if not checkbox_state:
            self.widgets['treeview'].item(focus_plugin, tag='disabled_row')
        else:
            self.widgets['treeview'].item(focus_plugin, tag="")
    
        self.update_view()

    def event_properties_scale_change(self, property, value):
        print("event_properties_slider_change", property, value)

        # print(self.plugins)
        # self.plugins[property]['plugin'].params['scale'] = float(value)

    def event_properties_checkbox_change(self, value):
        print('event_properties_checkbox_change', value)

    def event_plugin(self, value):
        print(f'value: {value}')
    
    def event_mouse_motion(self, event):
        # Always update mouse details
        self.mouse['screen_x'] = event.x
        self.mouse['screen_y'] = event.y

        print(f'event_mouse_motion:self.current_plugin_type {self.current_plugin_type}')
        self.frame_view.config(cursor=self.avaliable_plugins[self.current_plugin_type].get_cursor())
        self.avaliable_plugins[self.current_plugin_type].mouse_motion(
            event=event,
            widgets=self.widgets, 
            images=self.images
        )
        self.event_mouse(event, over_secondary=False)

    def event_mouse_motion_secondary(self, event):
        # Always update mouse details
        self.mouse['screen_x'] = event.x
        self.mouse['screen_y'] = event.y

        print(f"event_mouse_motion_secondary: self.current_plug_name = {self.current_plugin_type}")
        self.frame_view.config(cursor=self.avaliable_plugins[self.current_plugin_type].get_cursor())
        self.avaliable_plugins[self.current_plugin_type].mouse_motion(
            event=event,
            widgets=self.widgets, 
            images=self.images
        )
        self.event_mouse(event, over_secondary=True)
       
    def event_mouse(self, event, over_secondary=False):       
        print('event_mouse: ', event, 'over_secondary', over_secondary)

        plugin_type = self.avaliable_plugins[self.current_plugin_type]

        # Plugins that only update the view with mouse events
        if plugin_type.type_view:
            # INFUTURE
            # This should move to plugin.pan_zoom
            self.event_mouse_pan_zoom(event)
        # Plugins that can modify the manually draw on mask or interp with mouse events
        elif plugin_type.type_draw:
            plugin_id = self.current_plugin_instance
            self.plugins[plugin_id].mouse_drawing(event)
        # Plugins that don't draw but still modifiy interp...
        elif plugin_type.type_mouse_events:
            plugin_id = self.current_plugin_instance
            self.plugins[plugin_id].mouse_events(event)
        elif plugin_type.type_create_on_first_click:
            if event.type == EventType.ButtonRelease and event.num == 1:
                # Create and apply (create calls apply)
                self.create_new_plugin_from_click(
                    plugin_type=self.current_plugin_type, 
                    event=event, 
                    over_secondary=over_secondary
                )

        self.update_view()

    def event_mouse_button_2(self, event):
        print(f'event_mouse_button_2 | {event}')
        plugin = self.current_plugin_instance

        # Gaurd for PanZoom etc
        if self.plugins[plugin].type_view:
            return
        
        if self.plugins[plugin].type_has_popup:
            self.plugins[plugin].event_popup(event)

    def event_draw_size(self, draw_size, keypress=False):
        self.draw_size = draw_size
        if self.draw_size < 3:
            self.draw_size = 3
        elif self.draw_size > self.draw_size_max:
            self.draw_size = self.draw_size_max

        if keypress:
            self.view.menu_properties.scl_draw_size_var.set(self.draw_size)
            # pass
            # self.view.menu_properties.scl_draw_size.configure(variable=tk.DoubleVar().set(127))
            # self.view.menu_properties.scl_draw_size.update()

    def event_mouse_pan_zoom(self, event):
        if event.type == EventType.ButtonPress and event.num == 1:
            # keep the x and y
            self.mouse['old_screen_x'] = event.x
            self.mouse['old_screen_y'] = event.y
            self.mouse['active'] = True
        elif event.type == EventType.Motion and self.mouse['active'] is True:
            # calculate the difference
            delta_x = self.mouse['old_screen_x'] - event.x
            delta_y = self.mouse['old_screen_y'] - event.y
            print(f'mx {self.mouse["screen_x"]} x {event.x} delta_x {delta_x}')

            # pan
            self.images.pan('screen_x', delta_x)
            self.images.pan('screen_y', delta_y)

            # Keep for next time
            self.mouse['old_screen_x'] = event.x
            self.mouse['old_screen_y'] = event.y
        elif event.type == EventType.ButtonRelease and event.num == 1:
            self.mouse['active'] = False

        if event.type == EventType.MouseWheel:  # if the mouse wheel is changed: windows_platform
            # TODO- 
            # Test on windows and see if this is correct
            if not self.runnnig_on_mac():
                if event.delta < 0:  # +ve is out
                    self.images.zoom(1.1)
                else:
                    self.images.zoom(0.9)
            else:
                # 20240102 - EventType Mouse getting triggered without mouse change... 
                # I think this might be due to macOS upgrade?
                if event.delta > 1:  # +ve is in
                    self.images.zoom(1.1)
                elif event.delta < 1:
                    self.images.zoom(0.9)

    def event_keyboard(self, key):
        print(f"event_keyboard | key {key}")
        # TODO - Context aware keyboard shortcuts - The plan:
        # View based 
        #   • arrow keys and wasd and WASD, up down, left right
        #   • z,x,[,], bigger or smaller drawing size
        #   • q,e to zoom in and out
        
        # Common Drawing
        #   • 1,2,3.. 10 common drawing type
        #   • tab, mask or interp 0.3 or 0.0 transparency
        
        # Common Plugins
        #   • Space small task - like learn view
        #   • Return big task - like apply full plugin
        

        # Platform dependant Changes
        # if not self.runnnig_on_mac:
        #     arrow_key_up = 2490368
        #     arrow_key_down = 2621440
        #     arrow_key_right = 2555904
        #     arrow_key_left = 2424832
        # else:
        #     arrow_key_up = 0
        #     arrow_key_down = 1
        #     arrow_key_right = 2
        #     arrow_key_left = 3

        if key == 27:  # Escape key
            print('Escape Key Presss')
        elif key.char in ['w', 'W'] or key.keysym in ['Up']:
            self.images.pan('screen_y', -self.config.pan_step)
        elif key.char in ['s', 'S'] or key.keysym in ['Down']:
            self.images.pan('screen_y', self.config.pan_step)
        elif key.char in ['a', 'A',] or key.keysym in ['Left']:
            self.images.pan('screen_x', -self.config.pan_step)
        elif key.char in ['d', 'D'] or key.keysym in ['Right']:
            self.images.pan('screen_x', self.config.pan_step)
        elif key.char in ['-', '_', 'q', 'Q']:
            self.images.zoom(0.9)
        elif key.char in ['+', '=', 'e', 'E']:
            self.images.zoom(1.1)

        # INFUTURE 
        # • This needs to be inside the plugin
        # • Probably needs to be a callback
        # elif key.char in ['z', 'Z', '[', '{']:
        #     self.images.resize_draw_cirle(delta=0.9)
        # elif key.char in ['x', 'X', ']', '}']:
        #     self.images.resize_draw_cirle(delta=1.2)
        # elif key == 9:  # Tab key, tested: good. 
        #   self.event_change_user_mode()
        #   BUT REMOVED when in using tkinter.
        #     elif key in [ord('0'), ord('1'), ord('2'), ord('3'), ord('4'),
        #                  ord('5'), ord('6'), ord('7'), ord('8'), ord('9')]:
        #         self.set_interp_class(key)
        #         self.ui_debug += self.interp_class
        #     elif key in [ord('f'), ord('F')]:
        #         pass
        #         # This was purely example to test if things worked, ignore for now...
        #         # self.outstanding_proxels.append(self.proxel_blur)
        #         # self.outstanding_proxels.append(self.proxel_edge_detect)
        #         # print(f'F Pressed: Adding Proxel {self.outstanding_proxels[-1]}')
            
        self.update_view()
   
    def event_configure(self, event):
        print(f'View: Event Configure: {event}')
        self.update_view()

    def event_close(self):
        print('event_close | ')
        # If there are plugins ask to save settings
        # In future check if the plugins have changed, but this is quicker for now
        if len(self.plugins) > 0:
            # Show message no plugins to save
            result = Messagebox.yesno("Would you like to save settings?",
                                "Save Settings?",
                                alert=True)
            
            print(f'event_close | result: {result}')

            if (result == 'OK') or (result == 'Yes'):
                self.event_file_save_settings()
        
        self.window.quit()
    #endregion

    #region plugin methods
    def register_plugins(self, plugin_modules):
        for module in plugin_modules:
            # Get the plugins in the order specified in modules
            # and update the application "features"
            for plugin in module.plugin_order:
                self.avaliable_plugins[plugin] = getattr(module, plugin)

                if getattr(self.avaliable_plugins[plugin], "type_mask", False):
                    self.feature_mask = True
                
                if getattr(self.avaliable_plugins[plugin], "type_interp", False):
                    self.feature_interp = True
                
                if getattr(self.avaliable_plugins[plugin], "type_observ", False):
                    self.feature_observ = True

    def create_new_plugin_from_tool(self, plugin_type):
        print(f'create_new_plugin_from_tool | type: {plugin_type}')
        self.current_plugin_type = plugin_type

        # Clear existing widgets and update mouse overlays
        self.destroy_properties_widgets()
        self.forget_mouse_overlays()

        # Check is this plugin type already exist 
        name = self.plugin_type_exists_in_plugins(plugin_type=plugin_type)
        
        # Check if type and and there is an existing name (plugin found)
        if self.avaliable_plugins[plugin_type].type_solo and name:
            # Get the plugin rgb file name
            plugin_rgb_filename = self.plugins[name].params['RGBFile']
            
            if plugin_rgb_filename == self.current_rgb_file:
                # if file names match, change to that plug 
                self.change_existing_plugin(plugin_type=plugin_type, plugin_id=name)
            else: # else create that plugin
                print('Create the plugin, Plugin Type:', plugin_type)
                self.pre_create_plugin(plugin_type=plugin_type, event=None, over_secondary=False)
                self.plugin_apply_with_ui_updates(
                    value=None, 
                    changed_params=False, 
                    over_secondary=False
                )
                self.update_view()   
        elif self.avaliable_plugins[plugin_type].type_create_on_tool_button:
            print('Create the plugin, Plugin Type:', plugin_type)
            self.pre_create_plugin(plugin_type=plugin_type, event=None, over_secondary=False)
            self.plugin_apply_with_ui_updates(
                value=None, 
                changed_params=False, 
                over_secondary=False
            )
            self.update_view()
        elif self.avaliable_plugins[plugin_type].type_create_on_first_click:
            print(f'create_new_plugin_from_tool | type_create_on_first_click NOT CREATED')
            return
        elif self.avaliable_plugins[plugin_type].type_view:
            print(f'create_new_plugin_from_tool | type_view')
            self.pre_create_plugin(plugin_type=plugin_type, event=None, over_secondary=False)
            self.plugin_apply_with_ui_updates(
                value=None, 
                changed_params=False, 
                over_secondary=False
            )
            self.update_view()
        else:
            print(f"create_new_plugin | plugin_type error")  

    def create_new_plugin_from_click(self, plugin_type, event, over_secondary):
        print(f'create_new_plugin_from_click | type: {plugin_type}')
        self.current_plugin_type = plugin_type

        # Clear existing widgets and update mouse overlays
        self.destroy_properties_widgets()
        self.forget_mouse_overlays()

        # pre_create also calls the plugin.mouse_select_value
        self.pre_create_plugin(
            plugin_type=plugin_type, 
            event=event, 
            over_secondary=over_secondary
        )
        # The params have changed as they were updated by mouse_select_value
        self.plugin_apply_with_ui_updates(
            value=None, 
            changed_params=True, 
            over_secondary=over_secondary
        )  
        self.update_view()

    def create_new_plugin_from_file(self, plugin_type, plugin_params=None):
        print(f'create_new_plugin_from_file| type: {plugin_type}')

        self.current_plugin_type = plugin_type

        # Clear existing widgets and update mouse overlays
        self.destroy_properties_widgets()
        self.forget_mouse_overlays()

        if not plugin_params==None:
            rgb_filename = plugin_params.get('RGBFile', None)
        else:
            rgb_filename = None

        plugin_id = self.pre_create_plugin(
            plugin_type=plugin_type, 
            event=None, 
            over_secondary=False,
            from_saved=True,
            rgb_filename=rgb_filename,
        )

        return plugin_id
    
    def pre_create_plugin(self, plugin_type, event, over_secondary, from_saved=False, rgb_filename=None):
        """Create the plugin as the user has selected a value"""
        
        plugin = self.avaliable_plugins[plugin_type]

        if plugin.type_local:
            treeview_subtree = 'local_plugins'
            self.plugin_next_id += 1 # Create a new id for the name
            # plugin_id = f'{self.plugin_next_id:03d}' # original method
            # Generate id based on rgb file name
            if not from_saved:
                plugin_id = self.current_rgb_file 
            else:
                plugin_id = rgb_filename
        elif plugin.type_global:
            treeview_subtree = 'global_plugins'
            self.plugin_next_id += 1 # Create a new id for the name
            plugin_id = f'{self.plugin_next_id:03d}'
        elif plugin.type_view:
            plugin_id = plugin.generate_id(self.config)

        # Add new plugin instance to dictionary
        self.plugins[plugin_id] = plugin(
            config=self.config,
            id=plugin_id,
            text_name="",
            widgets=self.widgets,
            widget_parent=self.frame_properties,
            images=self.images,
            event_scale_change=self.event_properties_scale_change,
            event_checkbox_change=self.event_properties_checkbox_change,
        )

        # Add plugin to the treeview of plugins
        Disable_standard_controls = True
        if not plugin.type_view: # Ignore the 'view only' plugins
            self.widgets['treeview'].insert(
                treeview_subtree, 
                'end', 
                plugin_id, 
                text="awaiting information...", 
                open=True
            )
            self.widgets['treeview'].focus(plugin_id)  

            Disable_standard_controls = False
        
        # Create the widgets
        self.current_plugin_instance = plugin_id
        self.make_properties_start(Disabled=Disable_standard_controls)
        self.plugins[plugin_id].make_widgets()
        self.make_properties_end(Disabled=Disable_standard_controls)

        if not from_saved:
            self.plugins[plugin_id].mouse_select_value(event, over_secondary)
        self.post_create_plugin(plugin_id)

        return plugin_id

    def post_create_plugin(self, plugin_id):
        # Update text for plugin on treeview with colour selected by mouse
        print("post_create_plugin")

        if self.plugins[plugin_id].type_local:
            name_text = self.plugins[plugin_id].generate_name_text(self.images.paths)   
            self.plugins[plugin_id].params['RGBFile'] = f"{self.images.paths[self.config.rgb].split('/')[-1]}"
        else:
            name_text = self.plugins[plugin_id].generate_name_text()   
        
        # Update the text of the plugin text name now the plugin exists
        self.plugins[plugin_id].text_name = name_text    
        self.widgets['label_properties_name'].config(text=name_text)

        if not self.plugins[plugin_id].type_view:
            self.widgets['treeview'].item(plugin_id, text=name_text)

        # Finally we have an id so keep track of it
        self.current_plugin_instance = plugin_id

    def change_existing_plugin(self, plugin_type, plugin_id):
        '''This function only changes to existing plugins'''
        print(f'change_existing_plugin | type: {plugin_type}')

        # Keep track of type and name
        self.current_plugin_type = plugin_type
        self.current_plugin_instance = plugin_id

        # Update cursor to match plugin     
        new_cursor = self.avaliable_plugins[plugin_type].get_cursor()
        self.frame_view.config(cursor=new_cursor)
        
        # tidy old plugin items
        self.destroy_properties_widgets()
        self.forget_mouse_overlays()

        # Make properties and set focus on treeview, unless it is a view plugin
        if not self.avaliable_plugins[plugin_type].type_view:
            # The call came from  widget like treeview, so the plugin is in existance
            print('Plugin Instance ID:', plugin_id)
            self.make_properties_start(Disabled=False)
            self.plugins[plugin_id].make_widgets()
            self.make_properties_end(Disabled=False) 
            self.widgets['treeview'].focus(plugin_id)
        else:
            self.make_properties_end(Disabled=True) 

    def plugin_apply_with_ui_updates(self, value, changed_params=True, over_secondary=False):
        '''Does not call update_view, must be called seperately'''
        print(f"plugin_apply_with_ui_updates value: {value}")

        # TODO 
        # Before start of processing, mouse cursor, disable apply, 
        self.meter_working_start()
        self.widgets["label_status_plugins"].config(text="Applying Plugin Parameters") 
        self.widgets["label_status_plugins"].update()

        print('event_properties_button_apply', value)
        plugin_id = self.current_plugin_instance
        print('Current focus/ plugin_id |', plugin_id)

        if changed_params:
            # If params are being update then the plugin is not 'new'
            # if it is not new then it should ready know if it RGB or dip
            # IE over_secondary or not.
            over_secondary = not self.plugins[plugin_id].params['RGB']

        self.plugins[plugin_id].apply(
            changed_params=changed_params,
            over_secondary=over_secondary,
        )
        
        self.post_create_plugin(plugin_id)

        # TODO After end of processing mouse cursor disable apply update label
        self.widgets["label_status_plugins"].config(text="Finished Plugin Update") 
        self.meter_working_stop()
    
    def plugins_apply_all(self):
        print(f"plugins_apply_all")
        '''Apply all plugins in system to newly loaded image set. Does not call update_view, must be called seperately'''

        self.meter_working_start()
        self.widgets["label_status_plugins"].config(text="Applying All Plugins") 
        self.widgets["label_status_plugins"].update()

        for plugin in self.plugins:
            self.update()  # Allow time to tick and thus the meter to animate.

            if self.plugins[plugin].type_local and self.plugins[plugin].params['RGBFile'] == self.current_rgb_file:
                self.plugins[plugin].params['Active'] = True
                self.plugins[plugin].apply(changed_params=False, over_secondary=False)
            elif self.plugins[plugin].type_local and not self.plugins[plugin].params['RGBFile'] == self.current_rgb_file:
                self.plugins[plugin].params['Active'] = False
            elif self.plugins[plugin].params['Active']:
                over_secondary = not self.plugins[plugin].params['RGB']
                self.plugins[plugin].apply(changed_params=False, over_secondary=over_secondary)

        # TODO After end of processing mouse cursor disable apply update label
        self.widgets["label_status_plugins"].config(text="Finished All Plugins Update") 
        self.meter_working_stop()
    
    def plugin_type_exists_in_plugins(self, plugin_type):
        name = False
        for plugin in self.plugins:
            if type(self.plugins[plugin]).__name__ == plugin_type:
                name = plugin
        return name
    #endregion

    #region explorer and image set methods
    def open_image_set(self, from_dialog):
        self.meter_working_start()

        # Note self.config.msk not used at this point
        paths = {
            self.config.rgb : self.config.blank_image_path,
            self.config.dip : self.config.blank_image_path,
        }
  
        extension = from_dialog[0].rsplit('_', 1)[-1][:3]
        if extension == 'RGB':
            paths[self.config.rgb] = from_dialog[0]
            dip_path = from_dialog[0].replace('RGB', 'DIP')
            paths[self.config.dip] = dip_path
        elif extension == 'rgb':
            paths[self.config.rgb] = from_dialog[0]
            dip_path = from_dialog[0].replace('rgb', 'dip')
            paths[self.config.dip] = dip_path
        elif extension == 'DIP':
            paths[self.config.dip] = from_dialog[0]
            rgb_path = from_dialog[0].replace('DIP', 'RGB')
            from_dialog.append(rgb_path)
        elif extension == 'dip':
            paths[self.config.dip] = from_dialog[0]
            rgb_path = from_dialog[0].replace('dip', 'rgb')
            from_dialog.append(rgb_path)
        else:
            # None of the extensions match so display error and return
            message = "File must contain '_RGB' or '_Dip', at the end of the filename before the file extension." 
            messagebox.showerror('File Error!', 'File Error! \n' + message)
            self.widgets["label_status_images"].config(text=f'Status: Error Loading Images')
            return

        self.widgets["label_status_images"].config(text=f'Status: Loading Images...')
        self.widgets["label_status_images"].update()

        files_exist, message = self.images.load_rgb_dip(paths=paths)

        # Re-apply all global plugins
        if not files_exist:
            messagebox.showerror('File Error!', 'File Error! \n' + message)
            self.widgets["label_status_images"].config(text=f'Status: Error Loading Images')
        else:
            # Store the rgb file name for use in local plugins
            self.current_rgb_file = self.images.paths[self.config.rgb].rsplit("/", 1)[1]

            # Reset what is active
            self.current_plugin_type = self.plugin_default
            self.current_plugin_instance = 'PanZoom'
            self.images.draw_circle_size = None
            if len(self.plugins) > 0:
                self.images.delete_layers_not_drawn()
                self.plugins_apply_all()
            self.update_view()
            self.widgets['label_status_images']['text'] = f'Loaded: {self.images.paths[self.config.rgb].rsplit("/", 1)[1]}'
        
        # Always stop the meter animation at the point
        self.meter_working_stop()

    def update_explorer_file(self, path):
        """Update the Explorer for a Single Image Set"""

        # Get the root file name
        filename = path.rsplit("/", 1)[1]
        type = path.rsplit('_', 1)[-1][:3]

        print(f"filename {filename}, type {type}")

        # Clear existing files in explorer and insert new
        name = 'treeview_explorer'
        self.widgets[name].delete(*self.widgets[name].get_children())
        self.widgets[name].insert('',  'end', filename, text=filename, open=False)
        self.widgets[name].insert(filename,  'end', self.config.rgb, text=self.config.rgb, open=True)
        self.widgets[name].insert(filename,  'end', self.config.dip, text=self.config.dip, open=True)
        self.widgets[name].update()

    def update_explorer_directory(self, filenames):
        """Update the Explorer for a whole directory of Image Set(s)"""
       
        name = 'treeview_explorer'

        # Clear existing files in explorer and insert new
        self.widgets[name].delete(*self.widgets[name].get_children())

        for filename in filenames:
            type = filename.rsplit('_', 1)[-1][:3]

            print(f"filename {filename}, type {type}")
            self.widgets[name].insert('',  'end', filename, text=filename, open=False)
            self.widgets[name].insert(filename,  'end', filename + self.config.rgb, text=self.config.rgb, open=True)
            self.widgets[name].insert(filename,  'end', filename + self.config.dip, text=self.config.dip, open=True)
        
        self.widgets[name].update()       
    
    def update_recent_paths(self, path):
        # Push the latest path and update other recent paths...
        self.config.recent_path_2 = self.config.recent_path_1
        self.config.recent_path_1 = self.config.recent_path_0
        self.config.recent_path_0 = path
    #endregion
    
    #region other methods
    def destroy_properties_widgets(self):
            # Remove the old plugin properties widgets
        for widget in self.frame_properties.winfo_children():
            widget.destroy()

    def forget_mouse_overlays(self):
        # Clear up old mouse overlays if they exist
        if self.widgets.get('mouse_rect_upper', False):
            self.widgets['mouse_rect_upper'].place_forget()
        if self.widgets.get('mouse_rect_lower', False):
            self.widgets['mouse_rect_lower'].place_forget()
        if self.widgets.get('mouse_point_upper', False):
            self.widgets['mouse_point_upper'].place_forget()
        if self.widgets.get('mouse_point_lower', False):
            self.widgets['mouse_point_lower'].place_forget()
        self.images.draw_circle_size = None
    
    def update_view(self):
        # Update view - Draw the updated state
        w = self.widgets['label_view_upper'].winfo_width() -4
        h = self.widgets['label_view_upper'].winfo_height() -4

        if self.config.view == View.DOUBLE:
            img_out_main, img_out_secondary = self.images.update_double(w, 
                                                                        h, 
                                                                        keep_background=self.mask_transparency,
                                                                        show_interp=self.interp_transparency,
                                                                        keep_outline=self.keep_outline,
                                                                        mouse_x=self.mouse['screen_x'],
                                                                        mouse_y=self.mouse['screen_y'],
                                                                        )

            # Convert the secondary output to work with tkinter
            try:
                img_secondary = cv2.cvtColor(img_out_secondary, cv2.COLOR_BGRA2RGBA)
            except cv2.error:
                img_secondary = cv2.cvtColor(img_out_secondary, cv2.COLOR_GRAY2RGBA)

            self.image_lower = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img_secondary))
            self.widgets['label_view_lower'].configure(image=self.image_lower)

        elif self.config.view == View.SINGLE:
            img_out_main = self.images.update_single(w, 
                                                     h, 
                                                     keep_background=self.mask_transparency,
                                                     show_interp=self.interp_transparency,
                                                     keep_outline=self.keep_outline,
                                                     mouse_x=self.mouse['screen_x'],
                                                     mouse_y=self.mouse['screen_y'],
                                                    )

        #Convert the output to work with tkinter
        try:
            img_main = cv2.cvtColor(img_out_main, cv2.COLOR_BGRA2RGBA)
        except cv2.error:
            img_main = cv2.cvtColor(img_out_main[:,:,0], cv2.COLOR_GRAY2RGBA)

        print(f"update_view main shape: {img_main.shape}")
        self.image_upper = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img_main))
        self.widgets['label_view_upper'].configure(image=self.image_upper)

    def polled_update_check(self):
        '''Force Update if Images request it. Polls due to on timer.'''

        # Certain situation require a timed update
        # EG when the plugin needs to force the refresh
        if self.images.needs_update:
            self.update_view()
            print(f'polled_update_check | Update Performed')
            self.images.needs_update = False

        # if required make the "working" meter go round 
        if self.meter_working_animate:
            self.widgets['meter_working'].configure(amountused=self.meter_working_value)
            self.meter_working_value += 7
            if self.meter_working_value > 100:
                self.meter_working_value = 1

        # Update how much Virtual RAM is avaliable as %
        self.widgets['meter_ram'].get_ram_from_system()
        self.widgets['meter_ram'].update()

        # Changed to 5 seconds, 0.25 seconds is too waste full
        self.after(5000, self.polled_update_check)

    def set_view_dual(self):
        self.widgets['label_view_upper'].place_forget()
        self.widgets['label_view_lower'].place_forget()
        self.widgets['label_view_upper'].place(anchor='center', relheight=0.5, relwidth=1.0, relx=0.5, rely=0.25)
        self.widgets['label_view_lower'].place(anchor='center', relheight=0.5, relwidth=1.0, relx=0.5, rely=0.75)
        self.update_view()
        self.update()
    
    def set_view_single(self):
        self.widgets['label_view_upper'].place_forget()
        self.widgets['label_view_lower'].place_forget()
        self.widgets['label_view_upper'].place(anchor='center', relheight=1.0, relwidth=1.0, relx=0.5, rely=0.5)
        self.update_view()
        self.update()

    def meter_working_start(self):
        self.meter_working_animate = True
        self.widgets['meter_working'].configure(bootstyle=WARNING)
        self.widgets['meter_working'].update()

    def meter_working_stop(self):
        self.meter_working_animate = False
        self.widgets['meter_working'].configure(bootstyle=SECONDARY)
        self.widgets['meter_working'].update()

    def runnnig_on_mac(self):
        mac = False

        if sys.platform == "darwin":
            mac = True

        return mac
    
    def load_ui_images(self):
        # Get all the images in resources directory into system
        # must be .png and not have more than one full stop in name
        for image_path in glob.glob(self.config.resources_path + "*.png"):
            if self.runnnig_on_mac():
                name = image_path.split('/')[-1].split('.')[0]
            else:
                name = image_path.split('\\')[-1].split('.')[0]
            self.ui_images_raw[name] = PIL.Image.open(image_path)

    def load_starting_images(self):
        # TODO: make the system load in existing MSK files
        print('load_starting_images')

        paths = {
            self.config.rgb : self.config.starting_rgb_path,
            self.config.dip : self.config.starting_dip_path,
        }

        files_exist, message = self.images.load_rgb_dip(paths=paths)

        if not files_exist:
            messagebox.showerror('File Error!', 'File Error! \n' + message)
    
    def apply_config(self):
        print("Apply config has been run...")

        # now the widgets exist apply the configurations
        if self.config.dark_theme:
            self.style.load_user_themes('./resources/darkly-gray.json')
            self.style.theme_use('darkly-gray')

            self.widgets['toggle_light_dark'].configure(
                variable=ttk.IntVar(self.frame_top, 1), 
            )
        else:
            self.style.theme_use('flatly')
            self.widgets['toggle_light_dark'].configure(
                variable=ttk.IntVar(self.frame_top, 0), 
            )

    def tidyup(self):
        print(f"tidyup | save config to json")
        # After program has been closed, save the application config
        # need to check the output directory does not change after accessing other files
        with open("config.json", "w") as file_config:
            json_config = self.config.to_json(indent=4)
            file_config.write(json_config)
    #endregion


def event_closing(base_app: RockBase):
    print('Closing...', base_app)
    base_app.event_close()


if __name__ == '__main__':
    app = ttk.Window(
        title='RockBase App',
        iconphoto="./resources/logo_full_res.png",
        minsize=(1756, 977),
        maxsize=(3500, 1400),
    )
    app.place_window_center()
    base_app = RockBase(app, file_config="config.json")
    app.protocol("WM_DELETE_WINDOW", partial(event_closing, base_app))
    Splash(disappear_automatically=True)

    # In this order the splash screen appears before the 'slow'
    # process of loading outcrop images starts.
    base_app.load_starting_images()
    base_app.mainloop()
    base_app.tidyup()



