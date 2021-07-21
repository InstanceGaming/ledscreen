from ledscreen import get_screen

screen = get_screen()
print(f'The screen dimensions are {screen.width}, {screen.height}')
screen.set_pixel(0, 0xFF)
screen.set_pixel(1, 0xFF)
print('Set pixels')
