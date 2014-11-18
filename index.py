#!/usr/bin/python
import sys
import os
import os.path
import time
import hashlib
import binascii
import subprocess
import json
import argparse

ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.mobi', '.txt', '.rtf', '.ppt', '.py', '.zip', '.rar', '.chm')
CONTENT_INDEXABLE_EXTENSIONS = ('.pdf', '.doc', '.docx', '.epub', '.txt', '.rtf', '.ppt', '.chm')
CONTENT_INDEXABLE_MAX_SIZE = 60 * 1024 * 1024;
INDEX_NAME = "documents"
CONFIG = {
    'es.host': 'localhost:9200',
    'verbose': True,
}

def log(what):
    if CONFIG['verbose']:
        logAlways(what)

def logAlways(what):
    print what

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

def execute(command):
    try:
        output = subprocess.check_output(command, shell=True);
        return True
    except subprocess.CalledProcessError as e:
        log("Failed to execute command. Return code {0}".format(e.returncode))
        return False

def indexFile(absoluteFilename, dirname):
    if isIndexable(absoluteFilename):

        fileUniqueId = hashlib.sha224(absoluteFilename).hexdigest()
        fileTime = int(os.path.getmtime(absoluteFilename) * 1000) # ES wants millis as input for datetime

        log("- checking {0}".format(absoluteFilename))

        # check if we have a previous matching record
        output = subprocess.check_output("curl -s -XGET \"http://{0}/{1}/document/{2}\"".format(CONFIG['es.host'], INDEX_NAME, fileUniqueId), shell=True);
        data = json.loads(output);
        if (not data["found"] or (data["found"] and fileTime > int(data["_source"]["filetime"]))):

            fileChecksum = md5ForFile(absoluteFilename)
            fileSize = os.path.getsize(absoluteFilename)
            basename = os.path.basename(absoluteFilename)

            if (data["found"] and fileChecksum == data["_source"]["checksum"]):
                log("\t- file found with same checksum. skipping indexing")
                return

            logAlways("- indexing {0}{1}".format(dirname, basename))

            # construct indexing request body
            contentField = ""
            if isContentIndexable(basename) and fileSize < CONTENT_INDEXABLE_MAX_SIZE:
                contentField = """, \\\"content\\\": \\\"$(base64 \'{0}\')\\\"""".format(absoluteFilename.replace("'", r"'\''"))

            command = """echo "{{\\\"filename\\\": \\\"{0}\\\", \\\"dirname\\\": \\\"{1}\\\", \\\"checksum\\\": \\\"{2}\\\", \\\"filesize\\\": \\\"{3}\\\", \\\"filetime\\\": \\\"{4}\\\" {5} }}" > /tmp/docToIndex.txt""".format(basename, dirname, fileChecksum, fileSize, fileTime, contentField)
            execute(command)

            # fire away the request
            command = 'curl -s -i -XPUT http://{0}/{1}/document/{2} -d @/tmp/docToIndex.txt'.format(CONFIG['es.host'], INDEX_NAME, fileUniqueId)
            if not execute(command):
                logAlways("- failed to index {0}")

        else:
            log("\t- file timestamp not changed. skipping indexing")
            return


def dropIndex():
    log("- dropping elasticsearch index {0} on ES instance {1}".format(INDEX_NAME, CONFIG['es.host']))
    return execute('curl -s -X DELETE http://{0}/{1}'.format(CONFIG['es.host'], INDEX_NAME))


def createIndex():
    log("- creating elasticsearch index {0} on ES instance {1}".format(INDEX_NAME, CONFIG['es.host']))

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
                            "content"       : { "term_vector": "with_positions_offsets", "store":"yes", "index": "analyzed" },
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

    command = 'curl -s -XPOST http://{0}/{1} -d {2}'.format(CONFIG['es.host'], INDEX_NAME, mapping)
    return execute(command)


def recreateIndex():
    if not dropIndex():
        sys.exit(1);
    if not createIndex():
        sys.exit(2);
    logAlways("ES index recreated on host {0}".format(CONFIG['es.host']))


def indexFilesStartingAt(docroot):
    folder = os.path.abspath(docroot)
    if os.path.isdir(folder):
        log("Starting to index documents from docroot {0} to ES host {1}".format(docroot, CONFIG['es.host']))

        for root, dirs, files in os.walk(folder):
            resourcePath = os.path.abspath(root)[len(folder):] + "/"
            for file in files:
                indexFile(os.path.abspath(os.path.join(root, file)), resourcePath)
    else:
        logAlways("Invalid docroot path {0}".format(docroot))
        sys.exit(1)

# ---------------------------------

parser = argparse.ArgumentParser(description='Bensearch indexer script.')
parser.add_argument('action', choices=['install', 'index'], help='the type of action to perform. install recreates the ES schema while index recursively parses the specified directory and adds the data to ES')
parser.add_argument('-v', '--verbose', help='increase output verbosity', required=False, action="store_true")
parser.add_argument('-s', '--server', help='elasticsearch server locator. defaults to {0}'.format(CONFIG['es.host']), required=False)
parser.add_argument('-d', '--docroot', help="path to the root directory from which to start indexing recursively", required=False)
args = parser.parse_args()

CONFIG['verbose'] = args.verbose
CONFIG['es.host'] = args.server if args.server else CONFIG['es.host']

if args.action == 'install':
    recreateIndex()
elif args.action == 'index':
    if not args.docroot:
        print "Must specify document root when indexing!\n"
        parser.print_usage()
        sys.exit(3)
    else:
        indexFilesStartingAt(args.docroot);
