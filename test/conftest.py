import os
from google.cloud import storage

TEST_DATA_DIR = "test/test-data/assignment"


def download_assignment_test_data():
    """Downloads assignment test data from a cloud storage bucket
    The same test data is used by all Eppo SDKs.
    """
    storage_client = storage.Client.create_anonymous_client()
    bucket = storage_client.bucket("sdk-test-data")
    blobs = bucket.list_blobs(prefix="assignment/test-case")
    for blob in blobs:
        blob.download_to_filename(
            "{}/{}".format(TEST_DATA_DIR, blob.name.split("/")[1])
        )


def pytest_configure(config):
    if not os.path.exists(TEST_DATA_DIR):
        os.makedirs(TEST_DATA_DIR)
        download_assignment_test_data()
