import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import psutil

class MeterRAM(ttk.Frame):
    def __init__(self, parent, size=50, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # First Status Label
        text = "RAM"
        self.label = ttk.Label(
            parent,     
            text=text,
            bootstyle=(SECONDARY),
            foreground='gray',
        )
        self.label.pack(
            side=LEFT, 
            # fill=ttk.BOTH, 
            # expand=ttk.YES,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

        self.meter = ttk.Meter(
            parent,
            metersize=size,
            padding=5,
            amountused=50,
            metertype="semi",
            subtext="",
            interactive=False,
            bootstyle=SECONDARY,
            #showtext=False,
            textfont=(None, 1),
            subtextfont=(None, 1)
        )
        self.meter.pack(
            side=LEFT, 
            # fill=ttk.BOTH, 
            # expand=ttk.YES,
            ipadx=1,
            ipady=1,
            padx=4,
            pady=2,
        )

    def get_ram_from_system(self):
        RAM_percentage = psutil.virtual_memory()[2]

        self.meter.configure(bootstyle=DEFAULT)
        if RAM_percentage > 65:
            self.meter.configure(bootstyle=WARNING)
        if RAM_percentage > 85:
            self.meter.configure(bootstyle=DANGER)
        
        self.meter.configure(amountused=RAM_percentage)
        print(f"Meter RAM | RAM_percentage: {self.meter.amountusedvar.get()}")

class App(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.frame = ttk.Frame(self).pack(
            fill=ttk.BOTH, 
            expand=ttk.YES
        )

        self.meter_ram = MeterRAM(self.frame, size=50)
        self.meter_ram.pack(
            side=ttk.LEFT, 
            ipadx=4,
            ipady=4,
            padx=4,
            pady=4,
        )
        #self.meter_ram.get_ram_from_system()

        # Start the system updating RAM used
        self.after(1000, self.polled_update_check)

    def polled_update_check(self):
        '''Force Update if Images request it. Polls due to on timer.'''

        self.meter_ram.get_ram_from_system()
        self.meter_ram.update()

        self.after(1000, self.polled_update_check)

if __name__ == "__main__":
    root = ttk.Window(
        title='RAM',
        iconphoto="./resources/logo_full_res.png",
        minsize=(10, 10),
        maxsize=(3500, 1400),
    )

    app = App(root)

    app.mainloop()