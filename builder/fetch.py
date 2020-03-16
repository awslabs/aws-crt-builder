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
import os
import stat
import tempfile
import time
import tarfile
import zipfile
from urllib.request import urlretrieve, urlopen


MANIFEST_URL = 'https://d19elf31gohf1l.cloudfront.net/_binaries/MANIFEST'
MANIFEST_PATH = os.path.expanduser('~/.builder/MANIFEST')
CACHE_DIR = os.path.expanduser('~/.builder/pkg-cache')

# map of urls -> hashes, fetched from our repo, used to index/validate the cache


class Manifest(object):
    def __init__(self):
        self.remote = Manifest._fetch_remote()
        self.local = Manifest._load_local()
        os.makedirs(CACHE_DIR)

    @staticmethod
    def _parse(manifest_blob):
        manifest = {}
        line = manifest_blob.readline()
        while line:
            if line.startswith('#'):
                continue
            if '|' in line:
                url, digest = line.split('|', 1)
                manifest[url] = digest
            line = manifest_blob.readline()
        return manifest

    @staticmethod
    def _fetch_remote():
        try:
            with urlopen(MANIFEST_URL) as manifest_blob:
                return Manifest._parse(manifest_blob)
        except:
            print('Unable to fetch manifest, operating without cache')
            return {}

    @staticmethod
    def _load_local():
        try:
            with open(MANIFEST_PATH, 'r') as manifest_blob:
                return Manifest._parse(manifest_blob)
        except:
            return {}


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
        for chunk in iter(lambda: f.read(1024 * 1024)):
            hash.update(chunk)
    return hash.hexdigest()


def fetch(url, local_path):
    """ Download a file from a url and store it locally """
    # if it's already mapped to a local file, just let urlretrieve do the copy
    url = _map_from_cache(url)
    if os.path.isfile(url):
        return urlretrieve(url, local_path)

    manifest = get_manifest()
    digest = manifest.remote.get(url)

    local_dir = os.path.dirname(local_path)
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)

    if _is_cloudfront(url):
        # add a unique param that will avoid the cache and pull from S3
        url = url + '?time={}'.format(time.time())
    urlretrieve(url, local_path)

    if not digest:
        digest = hash_file(local_path)
    cache_path = os.path.join(CACHE_DIR, digest)

    # move to catch, record digest
    urlretrieve(local_path, cache_path)
    manifest.local[url] = digest


def fetch_and_extract(url, archive_path, extract_path):
    """ Download a tarball or zip file and extract it """
    fetch(url, archive_path)

    if not os.path.isdir(extract_path):
        os.makedirs(extract_path)

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

    os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
