# ledscreen (simplified)

Stripped-down version of `websocket` branch with only admin account and pluggram features.

<b>This project is currently under active development.</b>

## Client

A well-documented, easy-to-use psudo-libary that students will interface with. Under the hood, the API just makes IPC calls over zeroMQ to the running daemon.

## Daemon

The main control system for the screen. It has a few responsabilities:

- Serving web requests
- Seemless IPC
- Database connections and setup
- Plugin-like Python scripts ("built-in programs")
- All-in-one-place management portal for teachers
- Driving the LED screen via the `rpi_ws2812` libary.

## Usage

This system is meant to run headless on a Raspberry Pi or other linux device to provide a useful computer science teaching tool in the classroom.

The idea is a instructor can login to the management portal, create a roster of student "codes" (an 8-digit random alphanumeric value), and have their students use this system to explore graphics programming in Python in a simplified and ideal environment while promoting critical thinking and lightning-fast prototyping. Each student can login to the system using their assigned code to continue to iterate over their program as they learn the language and concepts of programming itself.

When the student has written and syntax-checked their code, within two clicks, they're code will run live on the big screen to produce immediate, definitive feedback for what they just wrote (which, in my opinion, is critical for learning developers). Teachers have the ability to monitor and selectively allow students to run code either on the physical screen or with a dummy library.

<b>To test drive the daemon:</b>

- Make a virtual environment and activate it
- Run `pip install -r requirements.txt`
- Setup a MySQL or MariaDB instance and a dedicated database user
- Create `config.toml` (see `utils.py:load_config()`)
- Set the `LS_CONFIG` environment variable with a path to the `config.toml` file
- Run `python cli.py setup-db` to initialize database
- Run `python app.py`