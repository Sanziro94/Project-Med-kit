# Project-Med-Kit V1
A high school project primarily intended to explore data storage and server/client communication. The concept: an intelligent locker designed to manage medicines remotely, providing personalized healthcare for a group or individual patient. The project didn't fully reach its potential due to time constraints and team inefficiencies.
# What It Does
Concretely? Not that much yet — but it has potential for a bigger impact down the line.
For now, it's a Python server built with the Flask library and the Flask-CORS extension, exposing multiple routes. Users can navigate several web pages stored on the system — designed primarily for Raspberry Pi but adaptable to other environments. The frontend is written in HTML/CSS, with client-side logic handled by JavaScript, communicating over HTTP using POST requests.
Features include: login, register, reset password, a patient state page, and a medic page. The state page currently does nothing, but the medic page allows saving a medication name and intake schedule for a registered patient.
Medicines are placed manually in the locker — the operator knows (or will know) which drawer to use. All data is stored in a JSON file that the server reads and writes continuously.
# Roles
Server — Routes instructions, exchanges data with the JS client via POST requests, updates the JSON file, and coordinates other components like the RFID manager or temperature/fan control (coming soon).
Client — Everything the user sees: HTML/CSS pages and a script.js file that handles HTTP communication using the Fetch API.
RFID — A Python script that reads RFID tags and sends them to the server during registration procedures.
Admin Panel — A Python script for sending instructions such as banning an IP address. Currently the least polished and least secure feature — use at your own risk.
# About
I'm a high school student getting my footing in software engineering and a bunch of other things. As you might have noticed, my English isn't perfect either — but you have to start somewhere, right? For V2, I promise I'll clean up the repo properly.
