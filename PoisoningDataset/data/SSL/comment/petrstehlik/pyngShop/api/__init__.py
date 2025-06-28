"""
Liberouter GUI
File: __init__.py
Author: Petr Stehlik <stehlik@cesnet.cz>

The basic initialization of the REST API happens within this file.
The basic steps:
	* app init and its configuration
	* configuration init
	* SSL init (if enabled)
	* base database connection to MongoDB (for users mainly)
	* Session manager
	* Authorization manager
	* Check if there are any users, if not set up a new admin
	* Enable CORS if requested
	* import all modules and its Blueprints
"""
