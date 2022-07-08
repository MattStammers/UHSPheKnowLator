#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import needed libraries
import fnmatch
import os

from google.api_core.exceptions import GoogleAPICallError  # type: ignore
from google.cloud import storage  # type: ignore


def uploads_data_to_gcs_bucket(bucket, original_data, temp_directory, filename):
    """Takes a file name and pushes the data referenced by the filename object and stored locally in that object to
    a Google Cloud Storage bucket.

    Args:
        bucket: A storage Bucket object specifying a Google Cloud Storage bucket.
        original_data: A string specifying the location of the original_data directory for a specific build.
        temp_directory: A local directory where preprocessed data is stored.
        filename: A string containing a filename.

    Returns:
        None.
    """

    if isinstance(bucket, storage.bucket.Bucket):
        print('Uploading {} to GCS bucket: {}'.format(filename, original_data))
        blob = bucket.blob(original_data + filename)
        blob.upload_from_filename(temp_directory + '/' + filename)

    return None


def downloads_data_from_gcs_bucket(bucket, original_data, processed_data, filename, temp_directory):
    """Takes a filename and and downloads the corresponding data to a local temporary directory, if it has not
    already been downloaded.

    Args:
        bucket: A storage Bucket object specifying a Google Cloud Storage bucket.
        original_data: A string containing a path to the original data directory in a Google Cloud Storage bucket.
        processed_data: A string containing a path to the processed data directory in a Google Cloud Storage bucket.
        filename: A string containing the name of file to write to a Google Cloud Storage bucket.
        temp_directory: A local directory where preprocessed data is stored.

    Returns:
        data_file: A string containing the local filepath for a file downloaded from a GSC bucket.

    Raises:
        ValueError: when trying to download a non-existent file from the GCS original_data dir of the current build.
    """

    if isinstance(bucket, storage.bucket.Bucket):
        try:  # search processed bucket first
            if processed_data is not None:
                _files = [_.name for _ in bucket.list_blobs(prefix=processed_data)]
                proc_file = fnmatch.filter(_files, '*/' + filename)[0]
                data_file = temp_directory + '/' + proc_file.split('/')[-1]
                if not os.path.exists(data_file):  # only download if file has not yet been downloaded
                    bucket.blob(proc_file).download_to_filename(temp_directory + '/' + proc_file.split('/')[-1])
            else: raise IndexError('processed_data is None, Exception Trigger in Order to Search original_data')
        except IndexError:
            try:  # then search the original bucket
                _files = [_.name for _ in bucket.list_blobs(prefix=original_data)]
                org_file = fnmatch.filter(_files, '*/' + filename)[0]
                data_file = temp_directory + '/' + org_file.split('/')[-1]
                if not os.path.exists(data_file):  # only download if file has not yet been downloaded
                    bucket.blob(org_file).download_to_filename(temp_directory + '/' + org_file.split('/')[-1])
            except IndexError:
                raise ValueError('Cannot find {} in the GCS directories of the current build'.format(filename))
        return data_file
    else: return None


def deletes_single_file(bucket, file_path):
    """Method deletes a single file form a Google Cloud Storage Bucket.

    Args:
        bucket: A storage Bucket object specifying a Google Cloud Storage bucket.
        file_path: A string containing a Google Cloud Storage Bucket path to a specific file.

    Returns:
        None.
    """

    blob = bucket.blob(file_path)
    blob.delete()

    return None


def deletes_bucket_files(bucket, gcs_directory):
    """Deletes all files within a specific directory in a Google Cloud Storage Bucket.

    Args:
        bucket: A storage bucket object specifying a Google Cloud Storage bucket.
        gcs_directory: A string containing the location for directory within a Google Cloud Storage bucket.

    Returns:
        None.
    """

    # get all files currently in the directory
    gcs_directory_files = [file.name for file in bucket.list_blobs(prefix=gcs_directory)]

    # delete directory files
    for _ in gcs_directory_files:
        blob = bucket.blob(_)
        blob.delete()

    return None


def copies_data_between_gcs_bucket_directories(bucket, src_directory, dest_directory, src_data_files):
    """Method copies files between Google Cloud Storage bucket directories. Method initially tries to copy data using
    copy.blob, but if the timeout threshold is reached it switches to using the blob.rewrite method, the recommended
    method to use when copying large files.

    SOURCE: https://stackoverflow.com/questions/60658799/gcp-python-copy-large-files-between-buckets

    Args:
        bucket: A storage bucket object specifying a Google Cloud Storage bucket.
        src_directory: A Google CLoud Storage Bucket directory to copy from.
        dest_directory: A Google Cloud Storage Bucket directory to copy to.
        src_data_files: A list of Google Cloud Storage Bucket paths, including filenames that need to be copied.

    Returns:
        None.
    """

    for data_file in src_data_files:
        try:
            src_blob = bucket.blob(src_directory + data_file); dest_blob = dest_directory + data_file
            _ = bucket.copy_blob(src_blob, bucket, dest_blob)
        except GoogleAPICallError:
            src_blob = bucket.get_blob(src_directory + data_file); dest_blob = bucket.blob(dest_directory + data_file)
            dest_blob.rewrite(src_blob); rewrite_token = False
            while True:
                rewrite_token, bytes_rewritten, bytes_to_rewrite = dest_blob.rewrite(src_blob, token=rewrite_token)
                logs = 'Progress {}: {}/{} bytes.'.format(data_file, bytes_rewritten, bytes_to_rewrite); print(logs)
                if not rewrite_token: break

    return None
