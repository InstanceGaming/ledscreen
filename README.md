# ledscreen

This Python project is designed to control a 1944-pixel WS2813 LED screen in a classroom environment.

## To run

- Install Python >3.6 and `virtualenv` or equivalent.
- Make virtual environments for each of the above modules.
- Run `pip install -r requirements.txt` for each module in their respective virtual environments.
- Configure each modules `.toml` config files to suite your environment and liking.
- Start `screend/main.py <config file path> <bind URL>`. For example, `screend/main.py screen.toml tcp://localhost:5555`. If you would like to have drawn frames saved into files, add `-f <directory>`.
- Start `pluggramd/main.py <programs directory> <screen RPC URL> <bind URL>`.
- Start `webapp/app.py` for a sample server or use a uWSGI compatible server to launch the web application. Be sure to update the `app.toml` configuration file to reflect the RPC URL's you used above.

For all three entry scripts, use the argument `-h` or `--help` by itself to read the complete list of available command line arguments.

**For the time being, only the built-in program start, stop and option edit functionality is implemented, others will come in due time. The information below is what the final version will encompass.**

## Client

A well-documented, easy-to-use psudo-libary that students will interface with. Under the hood, the API just makes IPC calls over zeroMQ to the running daemon.

## Daemon

The main control system for the screen will have many responsibilities:

- Running student code from a browser
- Serving web requests
- Seemless IPC
- Database connections and setup
- Plugin-like Python scripts ("built-in programs")
- All-in-one-place management portal for teachers
- Driving the LED screen via the `rpi_ws2812` libary.

## Concept

This system is meant to run headless on a Raspberry Pi or other linux device to provide a useful computer science teaching tool in the classroom.

The idea is a instructor can login to the management portal, create a roster of student "codes" (an 8-digit random alphanumeric value), and have their students use this system to explore graphics programming in Python in a simplified and ideal environment while promoting critical thinking and lightning-fast prototyping. Each student can login to the system using their assigned code to continue to iterate over their program as they learn the language and concepts of programming itself.

When the student has written and syntax-checked their code, within two clicks, they're code will run live on the big screen to produce immediate, definitive feedback for what they just wrote (which, in my opinion, is critical for learning developers). Teachers have the ability to monitor and selectively allow students to run code either on the physical screen or with a dummy library.
