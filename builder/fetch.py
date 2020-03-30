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

from hashlib import sha256
import json
import os
import stat
import tempfile
import time
import tarfile
import zipfile
from urllib.parse import urlparse
from urllib.request import urlretrieve, urlopen

try:
    import fcntl
except:
    fcntl = None

try:
    import msvcrt
except:
    msvcrt = None

from util import run_command, chmod_exec

FETCH_URL = 'https://d19elf31gohf1l.cloudfront.net/_binaries'
PUBLISH_URL = 's3://aws-crt-builder/_binaries'
PACKAGE_URL_FORMAT = '{url}/{name}/{package}'

FETCH_MANIFEST_URL = '{}/MANIFEST'.format(FETCH_URL)
PUBLISH_MANIFEST_URL = '{}/MANIFEST'.format(PUBLISH_URL)
MANIFEST_PATH = os.path.expanduser('~/.builder/MANIFEST')
MANIFEST_LOCK = os.path.expanduser('~/.builder/manifest.lock')
MANIFEST_TIMEOUT = 30
CACHE_DIR = os.path.expanduser('~/.builder/pkg-cache')


class LockFile(object):
    def __init__(self, path=MANIFEST_LOCK, timeout=None):
        self.path = path
        self.timeout = timeout
        self.fd = None

    def _lock(self):
        try:
            fd = os.open(self.path, os.O_CREAT)
        except OSError:
            pass
        try:
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif msvcrt:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except (IOError, OSError) as ex:
            os.close(fd)
        else:
            self.fd = fd

    def _locked(self):
        return self.fd != None

    def _unlock(self):
        fd = self.fd
        self.fd = None

        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_UN)
        elif msvcrt:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

        os.close(fd)

    def __enter__(self):
        start_time = time.time()
        timeout_time = start_time + self.timeout if self.timeout else None

        def timed_out():
            if not timeout_time:
                return False
            return time.time() > timeout_time

        self._lock()
        while not timed_out() and not self._locked():
            self._lock()
            time.sleep(0.1)

    def __exit__(self, *args):
        self._unlock()


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
            with urlopen(FETCH_MANIFEST_URL) as manifest_doc:
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

    package = _url_to_package(url)

    remote_digest = manifest.remote.get(package)
    if remote_digest:
        local_digest = manifest.local.get(package)
        if local_digest == remote_digest:
            cache_path = os.path.join(CACHE_DIR, local_digest)
            if os.path.isfile(cache_path):
                return cache_path

    return url


def _url_to_package(url):
    return os.path.basename(urlparse(url).path)


def _is_cloudfront(url):
    return 'cloudfront.net' in url


def hash_file(file_path):
    hash = sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hash.update(chunk)
    return hash.hexdigest()


def _download(url, local_path):
    print('Downloading {} to {}'.format(url, local_path))
    slug = ''
    if _is_cloudfront(url):
        # add a unique param that will avoid the cache and pull from S3
        slug = '?time={}'.format(time.time())
    urlretrieve(url + slug, local_path)


def fetch(url, local_path, skip_cache=False):
    """ Download a file from a url and store it locally """
    # if it's already mapped to a local file, just let urlretrieve do the copy
    if not skip_cache:
        url = _map_from_cache(url)
        if os.path.isfile(url):
            print('Using cached package {}'.format(url))
            return urlretrieve('file://' + url, local_path)

    manifest = get_manifest()
    digest = manifest.remote.get(url)

    local_dir = os.path.dirname(local_path)
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)

    _download(url, local_path)

    if not digest:
        digest = hash_file(local_path)
    cache_path = os.path.join(CACHE_DIR, digest)

    # move to catch, record digest
    print('Caching {} to {}'.format(local_path, cache_path))
    urlretrieve('file://' + local_path, cache_path)
    package = _url_to_package(url)
    manifest.local[package] = digest


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
    chmod_exec(script_path)


def publish_package(name, package_path):
    manifest = get_manifest()
    package = os.path.basename(package_path)
    manifest.remote[package] = manifest.local[package]

    print('Publishing to S3')
    s3_url = PACKAGE_URL_FORMAT.format(
        url=PUBLISH_URL, name=name, package=package)
    run_command('aws', 's3', 'cp', package_path, s3_url)

    print('Updating remote manifest')
    # Update hash for this file in the manifest
    with tempfile.NamedTemporaryFile('w+', delete=False) as tmp_manifest:
        json.dump(manifest.remote, tmp_manifest)
        tmp_manifest.close()
        run_command('aws', 's3', 'cp', tmp_manifest.name, PUBLISH_MANIFEST_URL)


def mirror_package(name, source_url):
    url_path = urlparse(source_url).path
    filename = os.path.basename(url_path)
    local_path = os.path.join(tempfile.gettempdir(), filename)
    # This will also shove the file into the cache
    fetch(source_url, local_path, skip_cache=True)
    publish_package(name, local_path)
