# """ This module contains the Copy and Merge for the RockBase application."""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip


from pathlib import Path

PATH = Path(__file__).parent / 'resources'


class CopyMergeDialog:
    def __init__(self, images, config):
        self.copy_merge = ttk.Window(
            title='Copy And Merge Dialog',
            iconphoto="./resources/logo_full_res.png",
            minsize=(300, 500),
            maxsize=(300, 500),
            #bootstyle=DEFAULT,
        )
        self.copy_merge.place_window_center()
        
        self.images = images
        self.config = config

        # After getting config(?)
        self.style = ttk.Style()
        #self.apply_config()

        # self.frame = ttk.Frame(copy_merge, style=(DEFAULT))
        # self.frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Option to copy to another layer or to Merge layers with priority
        # [ ] Need a widget to allow this
        # [ ] Create a drop down list for the first layer
        # [ ] Create a drop down list for the second layer
        # [ ] Create a result layer with option for NEW

        # label Rock Type
        self.label_copy_merge_priority = ttk.Label(
            self.copy_merge,
            text='Priority Layer (Copy From)',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.label_copy_merge_priority.pack(
            self.config.standard_label
        )
       
        if len(self.images._inter_int) > 0:
            # Get the actual names from the plugins so they are 'more' human readable
            names = []
            self.plugin_text_name_to_id = {} # clear
            for plugin in self.images.plugins:
                names.append(self.images.plugins[plugin].text_name)
                self.plugin_text_name_to_id[names[-1]] = plugin

            # Create the combobox    
            self.combobox_source = ttk.Combobox(
                self.copy_merge,
                values=names,
                state='readonly',
            )
            # self.combobox_source.bind(
            #     '<<ComboboxSelected>>', 
            #     partial(self.event_combobox_change)
            # )
            self.combobox_source.current(0)
            self.combobox_source.pack(
                self.config.standard_scale
            )
        else:
            names = ['No Interps. Avaliable']
            self.combobox_source = ttk.Combobox(
                self.copy_merge,
                values=names,
                state=DISABLED,
            )
            self.combobox_source.current(0)
            self.combobox_source.pack(
                self.config.standard_scale
            )

        # label Rock Type
        self.label_copy_merge_secondary = ttk.Label(
            self.copy_merge,
            text='Secondary Layer (Copy To...)',
            state=ACTIVE,
            bootstyle=(DEFAULT,) 
        )

        self.label_copy_merge_secondary.pack(
            self.config.standard_label
        )
       
        if len(self.images._inter_int) > 0:
            # Get the actual names from the plugins so they are 'more' human readable
            names = []
            self.plugin_text_name_to_id = {} # clear
            for plugin in self.images.plugins:
                names.append(self.images.plugins[plugin].text_name)
                self.plugin_text_name_to_id[names[-1]] = plugin

            # Create the combobox    
            self.combobox_destination = ttk.Combobox(
                self.copy_merge,
                values=names,
                state='readonly',
            )
            # self.combobox_source.bind(
            #     '<<ComboboxSelected>>', 
            #     partial(self.event_combobox_change)
            # )
            self.combobox_destination.current(0)
            self.combobox_destination.pack(
                self.config.standard_scale
            )
        else:
            names = ['No Interps. Avaliable']
            self.combobox_destination = ttk.Combobox(
                self.copy_merge,
                values=names,
                state=DISABLED,
            )
            self.combobox_destination.current(0)
            self.combobox_destination.pack(
                self.config.standard_scale
            )

        # Horizontal Separator
        self.separator_properties_end = ttk.Separator(
            self.copy_merge,
            orient=HORIZONTAL,
            bootstyle=(PRIMARY),
        )
        self.separator_properties_end.pack(
            side=TOP, 
            fill=X,
            ipadx=2,
            ipady=2,
            padx=2,
            pady=2,
        )

        # Button Apply
        if True:
            self.button_properties_apply = ttk.Button(
                self.copy_merge,
                text="Apply", 
                #command=partial(self.event_properties_button_apply, True), 
                image=None, 
                #state=state,
                bootstyle=(SUCCESS,) 
            )

            self.button_properties_apply.pack(
                side=LEFT,
                fill=X,
                expand=True,
                ipadx=2,
                ipady=2,
                padx=2,
                pady=2,
            )

            ToolTip(self.button_properties_apply, text="Apply the Copy to the Layers")

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
        self.button_properties_cancel = ttk.Button(
            self.copy_merge,
            text="Cancel", 
            #command=partial(self.event_properties_button_delete, True), 
            image=None, 
            #state=state,
            bootstyle=(WARNING,) 
        )

        self.button_properties_cancel.pack(
            side=LEFT,
            fill=X,
            expand=True,
            ipadx=2,
            ipady=2,
            padx=2,
            pady=2,
        )

        ToolTip(self.button_properties_cancel, text="Cancel Out of Dialog")



        self.copy_merge.update()

    def apply_config(self):
        print("Apply config has been run...")
        # now the widgets exist apply the configurations
        if self.config.dark_theme:
            self.style.load_user_themes('./resources/darkly-gray.json')
            self.style.theme_use('darkly-gray')
        else:
            self.style.theme_use('flatly')

