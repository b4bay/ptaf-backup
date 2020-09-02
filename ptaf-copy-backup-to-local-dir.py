import argparse
import subprocess
import os
from pymongo import MongoClient
from gridfs import GridFS
import shutil

DEFAULT_SCHEDULE = 'All settings'
DEFAULT_PATH = '/backup/'


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

    def fetch_all(self, collection_name, filter={}, excluded_fields=[]):
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

    def fetch_one(self, collection_name, filter={}, excluded_fields=[]):
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
    parser = argparse.ArgumentParser(description='Copy backup from PT AF to local directory')
    parser.add_argument('-t', '--task-schedule',
                        action='store',
                        dest='SCHEDULE',
                        default=DEFAULT_SCHEDULE,
                        required=False,
                        help='Name of Task Schedule to check, e.g. "Main settings". Default is "All settings"')
    parser.add_argument('-f', '--folder',
                        action='store',
                        dest='FOLDER',
                        default=DEFAULT_PATH,
                        required=False,
                        help='Full path to store backup, e.g. /folder1/subfolder. Default is /backup')

    if test_data:
        args = parser.parse_args(test_data)
    else:
        args = parser.parse_args()

    if not args.FOLDER.endswith("/"):
        args.FOLDER += "/"

    return args


class Run:
    def __init__(self, args, mongo=MongoDB()):
        self.schedule = {}
        self.task = {}
        self.backup = {}
        self.outfilename = ""
        self.mongo = mongo
        self.schedule_name = args.SCHEDULE
        self.path = args.FOLDER

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

    def upload_file_to_local_dir(self):
        try:
            shutil.copy(self.outfilename, self.path)
        except IOError as io_err:
            os.makedirs(os.path.dirname(self.path))
            shutil.copy(self.outfilename, self.path)

    def remove_file(self):
        if os.path.isfile(self.outfilename):
            os.remove(self.outfilename)


if __name__ == "__main__":
    r = Run(parse_cli_args())
    r.bootstrap()

    # Get file
    r.save_file()

    # Upload file to share
    r.upload_file_to_local_dir()

    # Remove file
    r.remove_file()

    print("DONE! Backup stored to {}".format(os.path.join(r.path, r.outfilename)))