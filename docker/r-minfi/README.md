
# Idat preprocessor function for use with Web applications.

This utility has also been dockerized and can be found in dockerhub [here](https://hub.docker.com/repository/docker/konlaz/r-minfi/general).


## 1. How to make

```bash
# to create the image
docker build -t konlaz/r-minfi:latest .
docker build -t konlaz/r-minfi:<version>

# To upload the image to Docker Hub

docker push konlaz/r-minfi:latest
docker push konlaz/r-minfi:<version>
```

## 2. How to use:

```bash

docker pull konlaz/r-minfi

docker run --rm -it -v ./[youridatfolder]:/workspace/idat -v ./out:/workspace/results konlaz/r-minfi
```
