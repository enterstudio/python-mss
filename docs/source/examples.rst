========
Examples
========

Using PIL
---------

Use you use the Python Image Library (aka Pillow) to do whatever you want with raw pixels.
This is an example using `frombytes() <http://pillow.readthedocs.io/en/latest/reference/Image.html#PIL.Image.frombytes>`_::

    #!/usr/bin/env python
    # coding: utf-8

    from mss import mss
    from PIL import Image


    with mss() as screenshotter:
        # We retrieve monitors informations:
        monitors = screenshotter.enum_display_monitors()

        # Get rid of the first, as it represents the "All in One" monitor:
        for num, monitor in enumerate(monitors[1:], 1):
            # Get raw pixels from the screen.
            # This method will store screen size into `width` and `height`
            # and raw pixels into `image`.
            screenshotter.get_pixels(monitor)

            # Create an Image:
            img = Image.frombytes('RGB',
                                  (screenshotter.width, screenshotter.height),
                                  screenshotter.image)

            # And save it!
            img.save('monitor-{0}.png'.format(num))
