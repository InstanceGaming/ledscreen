Starter Examples
----------------

The most basic screen script:

.. code-block:: python
    
   # import the get_screen() function from the ledscreen module.
   from ledscreen import get_screen 

   # get the current screen instance.
   screen = get_screen()
   # make all the pixels turn off (black). 0x000000 is just 0.
   screen.fill(0x000000)
   # 0xFFFFFF is the hexadecimal representation of 16777215, or white.
   screen.set_pixel(0, 0xFFFFFF)
   # draw the changed pixel to the screen.
   screen.render()
   # try and run it for yourself to see what happens!


Drawing text on the screen:

.. code-block:: python

   from ledscreen import get_screen

   # get the current screen instance.
   screen = get_screen()
   # make all the pixels turn off (black).
   screen.fill(0x000000)
   # draw text characters to the screen
   screen.draw_text(0, 'Hello, world!', 12, 0xFFFFFF, bold=True)
   # update the screen.
   screen.render()
