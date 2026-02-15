# Server Requirements
These are pretty lighweight, not intensive.

It requires Redis running so that you can store the data. It could run on an external system, I did try that by running a guest on Proxmox. But it seems better to just have it locally gathered and stored together.

The first gathers the UDP broadcast from Tempest and stores it in Redis, the second serves up the data from Redis.

The HTTP server does seem to have to some trouble new connections. I am not certain if it can handle all the clients I am throwing at it. I may need to figure out how to use NGINX and run it as CGI or something instead. Suggestions welcome.
