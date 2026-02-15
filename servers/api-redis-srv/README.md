# The API Server
I may need to figure out a better method of serving HTTP than the Python HTTP Server. I have clients throwing no-connection errors.

The configuration is pretty simple and straight forward -- where is Redis to get the data, and how does it serve it up?

```
[DEFAULT]
debug = 3
Redis_Server = localhost
Redis_Port = 6379
Redis_Instance = 0
Historical_Minutes = 90
Web_ServerName=10.10.10.8
Web_Port=8080
```

I forgot where I was going with Historical_Minutes! I think it might have been for the HTML interface, but I have pretty much abandoned that in favor of more ePaper displays everywhere.

Use the .service file for systemd registration.
