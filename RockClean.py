import RockBase 

def event_closing(base_app: RockBase):
    print('Closing...', base_app)
    base_app.event_close()


if __name__ == '__main__':
    app = RockBase.ttk.Window(
        title='RockClean',
        iconphoto="./resources/logo_full_res.png",
        minsize=(1756, 977),
        maxsize=(3500, 1400),
    )
    app.place_window_center()
    base_app = RockBase.RockBase(app, file_config="RockCleanConfig.json")
    app.protocol("WM_DELETE_WINDOW", RockBase.partial(event_closing, base_app))
    RockBase.Splash(disappear_automatically=True)

    # In this order the splash screen appears before the 'slow'
    # process of loading outcrop images starts.
    base_app.load_starting_images()
    base_app.mainloop()
    base_app.tidyup()