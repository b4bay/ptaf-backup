import argparse
import subprocess
import socket
import os
from pymongo import MongoClient
from gridfs import GridFS
from smb.SMBConnection import SMBConnection

DEFAULT_SCHEDULE = 'All settings'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PATH = 'backup'
DEFAULT_DOMAIN = ''
DEFAULT_LOGIN = 'test'
DEFAULT_PASSWORD = 'test'

class MongoDB:
    def __init__(self):
        process = subprocess.Popen(
            ["sudo /usr/local/bin/wsc -c 'cluster list mongo' | /bin/grep 'mongodb://' | /usr/bin/awk '{print $2}'"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        mongo_uri = process.stdout.readline().strip()
        self.client = MongoClient(mongo_uri)
        self.db = self.client['waf']
        self.fs = GridFS(self.db)

    def fetch_all(self, collection_name, filter = {}, excluded_fields = []):
        res = []
        collections = self.db.collection_names()
        if collection_name in collections:
            storage = self.db[collection_name]
            excluded = {}
            for field in excluded_fields:
                    excluded[field] = False
            if excluded:
                    db_iterator = storage.find(filter, excluded)
            else:
                    db_iterator = storage.find(filter)
            for doc in db_iterator:
                    res.append(doc)
        return res

    def fetch_one(self, collection_name, filter = {}, excluded_fields = []):
        res = {}
        collections = self.db.collection_names()
        if collection_name in collections:
            storage = self.db[collection_name]
            excluded = {}
            for field in excluded_fields:
                excluded[field] = False
            if excluded:
                res = storage.find_one(filter, excluded)
            else:
                res = storage.find_one(filter)
        return res

    def get_file(self, oid):
        return self.fs.get(oid)

def parse_cli_args(test_data=""):
    parser = argparse.ArgumentParser(description='Export backup from PT AF')
    parser.add_argument('-t', '--task-schedule',
                        action='store',
                        dest='SCHEDULE',
                        default=DEFAULT_SCHEDULE,
                        required=False,
                        help='Name of Task Schedule to check, e.g. "Main settings"')
    parser.add_argument('-s', '--server',
                        action='store',
                        dest='HOST',
                        default=DEFAULT_HOST,
                        required=False,
                        help='Server name or IP to store backup, e.g. MYSERVER or 192.16.0.1')
    parser.add_argument('-f', '--folder',
                        action='store',
                        dest='FOLDER',
                        default=DEFAULT_PATH,
                        required=False,
                        help='Path to share excluding root, e.g. folder1\\subfolder')
    parser.add_argument('-d', '--domain',
                        dest='DOMAIN',
                        required=False,
                        default=DEFAULT_DOMAIN,
                        action='store',
                        help='Domain for login, e.g. MYDOMAIN')
    parser.add_argument('-l', '--login',
                        dest='LOGIN',
                        required=False,
                        default=DEFAULT_LOGIN,
                        action='store',
                        help='Username for share, e.g. Administrator')
    parser.add_argument('-p', '--password',
                        dest='PASSWORD',
                        required=False,
                        default=DEFAULT_PASSWORD,
                        action='store',
                        help='Password for share, e.g. P@ssw0rd')

    if test_data:
        args = parser.parse_args(test_data)
    else:
        args = parser.parse_args()

    return args

class Run:
    def __init__(self, args, mongo=MongoDB()):
        self.schedule = {}
        self.task = {}
        self.backup = {}
        self.outfilename = ""
        self.mongo = mongo
        self.schedule_name = args.SCHEDULE
        self.host = args.HOST
        self.path = args.FOLDER
        self.domain = args.DOMAIN
        self.login = args.LOGIN
        self.password = args.PASSWORD

    def bootstrap(self):
        # Populate Task Schedule Object
        task_schedule = self.mongo.fetch_one('task_schedules', {"name": self.schedule_name, "task_type": "backup"})
        if task_schedule != {}:
            self.schedule = task_schedule
        else:
            raise LookupError("Cannot find Task Schedule {}".format(self.schedule_name))

        # Populate Task Object
        task = self.mongo.fetch_one('tasks', {"_id": self.schedule['last_task']})
        if task != {}:
            if task["status"] == "pending":
                raise ReferenceError("Task {} is still pending, cannot proceed".format(self.schedule['last_task']))
            elif task["status"] == "failed":
                raise ReferenceError("Task {} failed, cannot proceed".format(self.schedule['last_task']))
            else:
                self.task = task
        else:
            raise LookupError("Cannot find Task {}".format(self.schedule['last_task']))

        # Populate Backup Object
        backup = self.mongo.fetch_one('backups', {"_id": self.task['backup']})
        if task != {}:
            self.backup = backup
        else:
            raise LookupError("Cannot find Backup {}".format(self.schedule['last_task']))

        # Populate out file name
        self.outfilename = self.backup['name'].replace(":", "_") + ".tgz"

    def save_file(self):
        gridfs_file = self.mongo.fs.get(self.backup['file'])
        with open(r.outfilename, 'wb') as outfile:
            outfile.write(gridfs_file.read())

    def upload_file(self):
        conn = SMBConnection(self.login, self.password, socket.gethostname(), self.domain, is_direct_tcp=True)
        conn.connect(self.host, port=445)
        with open(self.outfilename, 'rb') as outfile:
            conn.storeFile(self.path, self.outfilename, outfile, timeout=300)
        conn.close()

    def remove_file(self):
        if os.path.isfile(self.outfilename):
            os.remove(self.outfilename)


if __name__ == "__main__":
    r = Run(parse_cli_args())
    r.bootstrap()

    # Get file
    r.save_file()

    # Upload file to share
    r.upload_file()

    # Remove file
    r.remove_file()

    print("DONE!")