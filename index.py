#!/usr/bin/python

import sys
import os
import os.path
import time
import hashlib
import binascii
import subprocess
import json

ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.mobi', '.txt', '.rtf', '.ppt', '.py', '.zip', '.rar', '.chm')
CONTENT_INDEXABLE_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.txt', '.rtf', '.ppt', '.chm')
CONTENT_INDEXABLE_MAX_SIZE = 60 * 1024 * 1024;
INDEX_NAME = "documents"
CONFIG = {
	'verbose': False
}

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

		fileUniqueId = hashlib.sha224(absoluteFilename).hexdigest()
		fileTime = int(os.path.getmtime(absoluteFilename) * 1000) # ES wants millis as input for datetime

		if CONFIG['verbose']:
			print "- checking {0}".format(absoluteFilename)

		# check if we have a previous matching record
		output = subprocess.check_output("curl -s -XGET \"http://localhost:9200/{0}/document/{1}\"".format(INDEX_NAME, fileUniqueId), shell=True);
		data = json.loads(output);
		if (not data["found"] or (data["found"] and fileTime > int(data["_source"]["filetime"]))):

			fileChecksum = md5ForFile(absoluteFilename)
			fileSize = os.path.getsize(absoluteFilename)
			basename = os.path.basename(absoluteFilename)

			if (data["found"] and fileChecksum == data["_source"]["checksum"]):
				if CONFIG['verbose']:
					print "\t- file found with same checksum. skipping indexing"
				return

			print "- indexing {0}".format(absoluteFilename)

			# construct indexing request body
			contentField = ""
			if isContentIndexable(basename) and fileSize < CONTENT_INDEXABLE_MAX_SIZE:
				contentField = """, \\\"content\\\": \\\"$(base64 \'{0}\')\\\"""".format(absoluteFilename.replace("'", r"'\''"))

			command = """echo "{{\\\"filename\\\": \\\"{0}\\\", \\\"dirname\\\": \\\"{1}\\\", \\\"checksum\\\": \\\"{2}\\\", \\\"filesize\\\": \\\"{3}\\\", \\\"filetime\\\": \\\"{4}\\\" {5} }}" > /tmp/docToIndex.txt""".format(basename, dirname, fileChecksum, fileSize, fileTime, contentField)
			output = subprocess.check_output(command, shell=True);

			# fire away the request
			command = 'curl -i -XPUT http://localhost:9200/{0}/document/{1} -d @/tmp/docToIndex.txt'.format(INDEX_NAME, fileUniqueId)
			try:
				output = subprocess.check_output(command, shell=True);
			except subprocess.CalledProcessError as e:
				print "- failed to index {0}. Reason {1}".format(absoluteFilename, e.output);

		else:
			if CONFIG['verbose']:
				print "\t- file timestamp not changed. skipping indexing"
			return


def dropIndex():
	command = 'curl -s -X DELETE http://localhost:9200/{0}'.format(INDEX_NAME)
	output = subprocess.check_output(command, shell=True);

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

	command = 'curl -s -XPOST http://localhost:9200/{0} -d {1}'.format(INDEX_NAME, mapping)
	output = subprocess.check_output(command, shell=True);

# ---------------------------------

# dropIndex()
createIndex()

folder = os.path.abspath("/home/benny/Dropbox/books")

for root, dirs, files in os.walk(folder):
    resourcePath = os.path.abspath(root)[len(folder):] + "/"
    for file in files:
		indexFile(os.path.abspath(os.path.join(root, file)), resourcePath)
