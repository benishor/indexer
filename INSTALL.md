# Installing BenSearch

BenSearch is composed of three components:

- an **indexer script** is used to recursively walk your document directory and *obtain metadata* which it then *feeds to*
- **elasticsearch** which *stores the metadata* provided by the indexer about the documents to be indexed and *is queried by*
- a **web based UI** which *presents the search results* to the end user

## elasticsearch

First we need to download elasticsearch. We will use version `1.4.0` for our experiments. Obtain the needed version by downloading it from [here](https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.0.tar.gz) and unpack the obtained archive:

```
wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.0.tar.gz
tar -xvzf elasticsearch-1.4.0.tar.gz
```

It is time now to configure our elasticsearch deploy to support our needs.

### Configuring elasticsearch

Open `elasticsearch-1.4.0/config/elasticsearch.yml` and set following values:

```
http.max_content_length: 100mb
```

In order to allow AJAX calls directly to our elasticsearch server, we need to enable [CORS](http://en.wikipedia.org/wiki/Cross-origin_resource_sharing). Do this by adding the following settings in the very same `elasticsearch-1.4.0/config/elasticsearch.yml` file:

```
http.cors.enabled: true
http.cors.allow-origin: "*"
```

### Adding attachment plugin

In order to index documents content, elasticsearch makes use of the fine [elasticsearch-mapper-attachments plugin](https://github.com/elasticsearch/elasticsearch-mapper-attachments).

We'll install the mapper attachments plugin by running:

```
cd elasticsearch-1.4.0/bin/
./plugin -install elasticsearch/elasticsearch-mapper-attachments/2.4.1
```

As you can notice, I have installed the 2.4.1 version of the plugin which is compatible with the 1.4.0 version of elasticsearch that we use. If you want to use a different elasticsearch, make sure to install the proper plugin version by consulting the [list of compatible versions](https://github.com/elasticsearch/elasticsearch-mapper-attachments).

### Starting elasticsearch

For testing purposes, you may want top start elasticsearch in the foreground, by simply running:

```
elasticsearch-1.4.0/bin/elasticsearch
```


Once you are satfisied with the set-up, you may want to run it in the background as a daemon process. You can do that by adding the **-d** argument:

```
elasticsearch-1.4.0/bin/elasticsearch -d
```

This is the command you want to be ran at system start-up if you want the storage to be started when the computer starts.

## indexer
BenSearch makes use of a Python enabled indexer whose task is to make sure the information stored in elasticsearch is accurate.

### Creating the elasticsearch schema

```
index.py install
```

### Indexing the actual files

```
index.py index -d /home/benny/Dropbox/books
```
