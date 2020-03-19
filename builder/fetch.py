# Copyright 2010-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#  http://aws.amazon.com/apache2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import fcntl
from hashlib import sha256
import json
import os
import stat
import tempfile
import time
import tarfile
import zipfile
from urllib.request import urlretrieve, urlopen


MANIFEST_URL = 'https://d19elf31gohf1l.cloudfront.net/_binaries/MANIFEST'
MANIFEST_PATH = os.path.expanduser('~/.builder/MANIFEST')
MANIFEST_LOCK = os.path.expanduser('~/.builder/manifest.lock')
MANIFEST_TIMEOUT = 30
CACHE_DIR = os.path.expanduser('~/.builder/pkg-cache')


class LockFile(object):
    def __init__(self, path=MANIFEST_LOCK, timeout=None):
        self.path = path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.path, os.O_CREAT)
        start_time = time.time()
        timeout_time = start_time + self.timeout if self.timeout else None
        while not timeout_time or time.time() < timeout_time:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (OSError, IOError) as ex:
                # resource temporarily unavailable (locked)
                if ex.errno != errno.EAGAIN:
                    raise
            time.sleep(1)

    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        try:
            os.unlink(self.path)
        except:
            pass


class Manifest(object):
    """ map of urls -> hashes, fetched from our repo, used to index/validate the cache """

    def __init__(self):

        manifest = self

        class SynchronizedDict(dict):
            def __setitem__(self, item, value):
                super().__setitem__(item, value)
                manifest.save()

        self.remote = Manifest._fetch_remote()
        self.local = SynchronizedDict(Manifest._load_local())
        os.makedirs(CACHE_DIR, exist_ok=True)

    @staticmethod
    def _parse(doc):
        try:
            manifest = json.load(doc)
        except Exception as ex:
            print('Failed to parse manifest: {}'.format(ex))
            manifest = {}

        return manifest

    @staticmethod
    def _fetch_remote():
        try:
            with urlopen(MANIFEST_URL) as manifest_doc:
                return Manifest._parse(manifest_doc)
        except:
            print('Unable to fetch manifest, operating without cache')
            return {}

    @staticmethod
    def _load_local():
        try:
            with LockFile(timeout=5):
                with open(MANIFEST_PATH, 'r') as manifest_doc:
                    return Manifest._parse(manifest_doc)
        except:
            return {}

    def save(self):
        with LockFile(timeout=5):
            with open(MANIFEST_PATH, 'w+') as manifest_doc:
                json.dump(self.local, manifest_doc)


_manifest = None


def get_manifest():
    global _manifest
    if not _manifest:
        _manifest = Manifest()
    return _manifest


def _map_from_cache(url):
    """ Returns a path mapped from the cache if it is not expired, or the original url if download is required """
    manifest = get_manifest()

    remote_digest = manifest.remote.get(url, None)
    if remote_digest:
        local_digest = manifest.local.get(url, None)
        if local_digest == remote_digest:
            cache_path = os.path.join(CACHE_DIR, local_digest)
            if os.path.isfile(cache_path):
                return cache_path

    return url


def _is_cloudfront(url):
    return 'cloudfront.net' in url


def hash_file(file_path):
    hash = sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hash.update(chunk)
    return hash.hexdigest()


def fetch(url, local_path):
    """ Download a file from a url and store it locally """
    # if it's already mapped to a local file, just let urlretrieve do the copy
    url = _map_from_cache(url)
    if os.path.isfile(url):
        print('Using cached package {}'.format(url))
        return urlretrieve('file://' + url, local_path)

    manifest = get_manifest()
    digest = manifest.remote.get(url)

    local_dir = os.path.dirname(local_path)
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)

    print('Downloading {} to {}'.format(url, local_path))
    slug = ''
    if _is_cloudfront(url):
        # add a unique param that will avoid the cache and pull from S3
        slug = '?time={}'.format(time.time())
    urlretrieve(url + slug, local_path)

    if not digest:
        digest = hash_file(local_path)
    cache_path = os.path.join(CACHE_DIR, digest)

    # move to catch, record digest
    print('Caching {} to {}'.format(local_path, cache_path))
    urlretrieve('file://' + local_path, cache_path)
    manifest.local[url] = digest


def fetch_and_extract(url, archive_path, extract_path):
    """ Download a tarball or zip file and extract it """
    fetch(url, archive_path)

    if not os.path.isdir(extract_path):
        os.makedirs(extract_path)

    print('Extracting {} to {}'.format(archive_path, extract_path))
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as tar:
            tar.extractall(extract_path)

    elif zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zip:
            zip.extractall(extract_path)

    else:
        print('Unrecognized archive {}, cannot extract'.format(archive_path))


def fetch_script(url, script_path):
    """ Download a script, and give it executable permissions """
    fetch(url, script_path)

    print('Applying exec permissions to {}'.format(script_path))
    os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
