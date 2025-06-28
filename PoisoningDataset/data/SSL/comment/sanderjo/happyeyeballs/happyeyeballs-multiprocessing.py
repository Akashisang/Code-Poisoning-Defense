# Multiprocessing module for Happy Eyeballs
# Method on high level: start a Process for each IP address (adding a delay for IPv4 addresses), connect & 
# find the quickest response, report that and terminate() all other processes that might still be running.
