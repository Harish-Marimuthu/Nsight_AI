# Dashboard to navigate PDFs and rename them.

### Docker Login
```sh
docker login <server_name> -u <user_name> -p <password>
```

```sh
docker login sapjson.azurecr.io -u sapjson -p <password>
```

### Build a docker image 
```sh
docker build -t <image_name> .
```

```sh
docker build -t sapjson.azurecr.io/sapjson:v1 .
```

### Run the docker image 
```sh
docker run --name <container_name> -p 80:80 <image_name>
```

```sh
docker run --name sapjson -p 80:80 sapjson.azurecr.io/sapjson:v1
```

### Push the docker image to Cloud

```sh
docker push <name>
```

```sh
docker push sapjson.azurecr.io/sapjson:v2
```