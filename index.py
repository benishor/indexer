#!/usr/bin/python

import sys
import os
import os.path
import time
import hashlib
import binascii

ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.mobi', '.txt', '.rtf', '.ppt', '.py', '.zip', '.rar', '.chm')
CONTENT_INDEXABLE_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.txt', '.rtf', '.ppt', '.chm')
INDEX_NAME = "documents"

def isIndexable(f):
	return f.lower().endswith(ALLOWED_EXTENSIONS)

def isContentIndexable(f):
	return f.lower().endswith(CONTENT_INDEXABLE_EXTENSIONS)

def md5ForFile(filename, blockSize=8192):
	md5 = hashlib.md5()
	with open(filename,'rb') as f: 
		for chunk in iter(lambda: f.read(blockSize), b''): 
			md5.update(chunk)
	return binascii.hexlify(md5.digest())

def indexFile(absoluteFilename, dirname):
	if isIndexable(absoluteFilename):

		print "- indexing {0}".format(absoluteFilename)

		fileUniqueId = hashlib.sha224(absoluteFilename).hexdigest()
		fileChecksum = md5ForFile(absoluteFilename)
		fileSize = os.path.getsize(absoluteFilename)
		fileTime = int(os.path.getmtime(absoluteFilename) * 1000) # ES wants millis as input for datetime

		basename = os.path.basename(absoluteFilename)

		# construct indexing request body
		contentField = ""
		if isContentIndexable(basename):
			contentField = """, \\\"content\\\": \\\"$(base64 \'{0}\')\\\"""".format(absoluteFilename)

		command = """echo "{{\\\"filename\\\": \\\"{0}\\\", \\\"dirname\\\": \\\"{1}\\\", \\\"checksum\\\": \\\"{2}\\\", \\\"filesize\\\": \\\"{3}\\\", \\\"filetime\\\": \\\"{4}\\\" {5} }}" > /tmp/docToIndex.txt""".format(basename, dirname, fileChecksum, fileSize, fileTime, contentField)
		os.system(command)

		# print command

		# fire away the request
		command = 'curl -i -XPUT http://localhost:9200/{0}/document/{1} -d @/tmp/docToIndex.txt'.format(INDEX_NAME, fileUniqueId)
		os.system(command)

def dropIndex():
	command = 'curl -X DELETE http://localhost:9200/{0}'.format(INDEX_NAME)
	os.system(command)

def createIndex():
				      # "_source" : {"excludes" : ["content"]},
				            # "content"  : { "store" : "no" },
	mapping = """'{
				  "mappings" : {
				  	"indexer" : {
				  		"properties" : {
				  			"run_date" : {"type" : "date"}
				  		}
				  	},
				    "document" : {
				      "_source" : {"excludes" : ["content"]},
				      "properties" : {
				      	"filename" : {"type": "string"},
				      	"dirname" : {"type": "string"},
				      	"checksum" : {"type": "string"},
				      	"filesize" : {"type": "long"},
				      	"filetime" : {"type": "date"},
				      	"indexer_run_id" : {"type" : "string"},
				        "content" : {
				          "type" : "attachment",
				          "fields" : {
				            "content"    	: { "term_vector": "with_positions_offsets", "store":"yes", "index": "analyzed" },
				            "author"        : { "store" : "yes" },
				            "keywords"      : { "store" : "yes", "analyzer" : "keyword" },
				            "content_type"  : { "store" : "yes" },
				            "title"         : { "store" : "yes", "analyzer" : "english"}
				          }
				        }
				      }
				    }
				  }
				}'"""

	command = 'curl -XPOST http://localhost:9200/{0} -d {1}'.format(INDEX_NAME, mapping)
	os.system(command)

# ---------------------------------

dropIndex()
createIndex()

folder = os.path.abspath("/home/benny/Dropbox/books")

for root, dirs, files in os.walk(folder):
    resourcePath = os.path.abspath(root)[len(folder):] + "/"
    for file in files:
		indexFile(os.path.abspath(os.path.join(root, file)), resourcePath)

# folder = "."
# for filename in os.listdir(folder):
# 	absoluteFilename = os.path.abspath(os.path.join(folder, filename))
# 	if isIndexable(absoluteFilename):
# 		indexFile(absoluteFilename, folder)


