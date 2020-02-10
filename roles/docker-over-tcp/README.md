# docker-over-tcp

Exposes the docker socket via TCP on port 2376 (as describe [here](https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-socket-option)).

This can be useful for building docker images against a remote Docker daemon.

For security reasons the socket only binds to localhost such that you have to establish an SSH tunnel first before accessing the socket.
