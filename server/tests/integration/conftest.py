import json
from pathlib import Path
import time
from typing import Any, Dict

from girder_client import GirderClient
import pytest

localDataRoot = Path('tests/integration/data')

"""
Alice and Bobby have different types of data (images and video)
Most tests run operations on a single dataset for each user, so keeping
each user constrained to a single data type will help ensure robustness
"""
users: Dict[str, Dict[str, Any]] = {
    'alice': {
        'login': 'alice',
        'email': 'alice@locahost.lan',
        'firstName': 'Alice',
        'lastName': 'User',
        'password': 'alicespassword',
        'data': [
            {
                'name': 'video1_train_mp4',
                'path': 'TestData/video1_train_mp4',
                'fps': 30,  # Should get reduced.
                'originalFps': 30_000 / 1001,
                'type': 'video',
            },
            {
                'name': 'video2_train_mp4',
                'path': 'TestData/video2_train_mp4',
                'fps': 5.8,
                'originalFps': 30_000 / 1001,
                'type': 'video',
            },
        ],
    },
    'bobby': {
        'login': 'bobby',
        'email': 'bobby@locahost.lan',
        'firstName': 'Bob',
        'lastName': 'User',
        'password': 'bobspass',
        'data': [
            {
                'name': 'testTrain1_imagelist',
                'path': 'TestData/testTrain1_imagelist',
                'fps': 1,
                'type': 'image-sequence',
            },
            {
                'name': 'testTrain2_imagelist',
                'path': 'TestData/testTrain2_imagelist',
                'fps': 6,
                'type': 'image-sequence',
            },
            {
                'name': 'multiConfidence_text',
                'path': 'TestData/multiConfidence_test',
                'fps': 22.1,
                'type': 'image-sequence',
            },
        ],
    },
}


def getClient(name: str) -> GirderClient:
    gc = GirderClient(apiUrl='http://localhost:8010/api/v1')
    gc.authenticate(username=name, password=users[name]['password'])
    return gc


def getTestFolder(client: GirderClient):
    me = client.get('user/me')
    privateFolder = client.loadOrCreateFolder("Integration", me['_id'], 'user')
    return privateFolder


@pytest.fixture(scope="module")
def admin_client() -> GirderClient:
    gc = GirderClient(apiUrl='http://localhost:8010/api/v1')
    gc.authenticate(username='admin', password='letmein')
    return gc


def wait_for_jobs(client: GirderClient, max_wait_timeout=30):
    """Wait for all worker jobs to complete"""
    start_time = time.time()
    incompleteJobs = []
    while True and (time.time() - start_time < max_wait_timeout):
        incompleteJobs = client.get(
            'job',
            parameters={
                # https://github.com/girder/girder/blob/master/plugins/jobs/girder_jobs/constants.py
                # https://github.com/girder/girder_worker/blob/master/girder_worker/girder_plugin/status.py
                'statuses': json.dumps([0, 1, 2, 820, 821, 822, 823, 824]),
            },
        )
        if len(incompleteJobs) == 0:
            break
        time.sleep(1)
    if len(incompleteJobs) > 0:
        raise Exception("Jobs were still running after timeout")
    # Verify that all jobs succeeded
    time.sleep(1)
    lastJob = client.get(
        'job',
        parameters={
            'limit': 1,
        },
    )
    if len(lastJob) > 0 and lastJob[0]['status'] != 3:
        raise Exception("Some jobs did not succeed")
