_Updated 12/15/21_

# ledscreen
This Python project is designed to control a 1944-pixel WS2813 LED screen in a classroom environment.

### This is NOT finished software!

**For the time being, only the built-in program start, stop and option edit functionality is implemented, others will come in due time.**

## Known issues
- Running the Flask app with uWSGI makes tinyrpc hang upon first RPC call but dev server does not. I'm out of ideas on how to dignose this issue.
- It seems like dhcpcd takes at least 10sec to setup even just a static address, so a 10 second delay must happen before screend starts or else the startup splash will not be able to show the devices address. Linux only.
- Oversimplified user authentication for a single user account (for my particular use case).
- Pluggram option modals do not show descriptive error for invalid input.
- As it turns out, trying to drive all 1944 pixels from one DMA channel has its quirks. If you are building a WS28XX screen, please heed my advice: use multiple GPIO outputs to drive segments of your screen (it's a bit late in the design process for me). Even though it's only 800kHz, use copious amounts of shielding on data lines, RS485 if you have to. Order at least one spare roll of LED strip, there WILL be dead pixels! Try to order all the LED rolls from the same vendor **at the same time**. There is no guarantee that they will make more of the same specification or quality.

## To run
- Install Python >3.6 and `virtualenv` or equivalent.
- Make virtual environments for each of the above modules.
- Run `pip install -r requirements.txt` for each module in their respective virtual environments.
- Configure each modules `.toml` config files to suite your environment and liking.
- Start `screend/main.py <config file path> <bind URL>`. For example, `screend/main.py screen.toml tcp://localhost:5555`. If you would like to have drawn frames saved into files, add `-f <directory>`.
- Start `pluggramd/main.py <programs directory> <screen RPC URL> <bind URL>`.
- Start `webapp/app.py` for a sample server or use a uWSGI compatible server to launch the web application. Be sure to update the `app.toml` configuration file to reflect the RPC URL's you used above.

For all three entry scripts, use the argument `-h` or `--help` by itself to read the complete list of available command line arguments.

## Client-side
A well-documented, easy-to-use Python pseudo-module that students can write code around. Under the hood, the API just makes IPC calls over zeroMQ to the running screen daemon.

## screend
- Driving the LED screen via the `rpi_ws2812` libary.
- Wrapping PIL for easier image and font manipulation.
- Showing splash image upon startup of the devices current IP address (interface set in `screend.toml`).

## pluggramd
- Loading, configuring, running "built-in programs".
- Interfaces with both screend and webapp over IPC.

"Built-in program" is just a friendlier name for a plugin framework, like JAR plugins.
These plugin scripts can be found or added under `pluggramd/programs/`.

## webapp
The Flask frontend web service and REST API to make IPC calls to pluggramd.

## Concept
This system is meant to run headless on a Raspberry Pi or other linux device to provide a useful computer science teaching tool in the classroom by driving a 1944 (54x36) pseudo-"screen" display.

The class instructor can run built-in graphical programs or (eventually) allow students to write Python to run on the screen from over the network by uploading their code to the screen for sandboxed execution.
