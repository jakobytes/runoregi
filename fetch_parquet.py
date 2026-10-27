#!/usr/bin/env python3
"""Download the parquet files of runoregi and filter-visualizations into a directory.

Usage: fetch_parquet.py [target_dir]   (default: ./parquet next to this script)

Source: $PARQUET_SOURCE, either a public URL (e.g. https://a3s.fi/filter-data)
or an S3 bucket (s3://livonia-parquet). For S3, requests are signed with
$AWS_ACCESS_KEY_ID and $AWS_SECRET_ACCESS_KEY against $S3_ENDPOINT
(default https://a3s.fi, i.e. Allas). Tables missing from the source are skipped.
"""
import datetime
import hashlib
import hmac
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE = os.getenv('PARQUET_SOURCE', 'https://a3s.fi/filter-data').rstrip('/')
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'https://a3s.fi').rstrip('/')
S3_REGION = os.getenv('S3_REGION', 'regionOne')
TABLES = [
    # runoregi
    'collectors', 'dbmeta', 'p_clust', 'p_clust_freq', 'p_col', 'p_dupl',
    'p_pl', 'p_sim', 'p_typ', 'p_year', 'place_stats', 'places', 'poems',
    'raw_meta', 'refs', 'runoregi_pages', 'types', 'v_clust', 'v_clust_freq',
    'v_clusterings', 'v_sim', 'verse_poem', 'verses', 'verses_cl',
    'verses_translated', 'word_analysis',
    # filter-visualizations
    'map_pol', 'maps', 'pol_pl', 'polygons', 'word_freq', 'word_occ', 'words',
]


def _sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def s3_request(bucket, key):
    'A GET request for s3://bucket/key, signed with AWS Signature Version 4.'
    access_key = os.environ['AWS_ACCESS_KEY_ID']
    secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
    host = urllib.parse.urlparse(S3_ENDPOINT).netloc
    path = '/{}/{}'.format(bucket, urllib.parse.quote(key))
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date, date = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
    payload_hash = hashlib.sha256(b'').hexdigest()
    headers = {'host': host, 'x-amz-content-sha256': payload_hash, 'x-amz-date': amz_date}
    signed_headers = ';'.join(sorted(headers))
    canonical_request = '\n'.join([
        'GET', path, '',
        ''.join('{}:{}\n'.format(k, headers[k]) for k in sorted(headers)),
        signed_headers, payload_hash])
    scope = '{}/{}/s3/aws4_request'.format(date, S3_REGION)
    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256', amz_date, scope,
        hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()])
    signing_key = _sign(_sign(_sign(_sign(
        ('AWS4' + secret_key).encode('utf-8'), date), S3_REGION), 's3'), 'aws4_request')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    headers['Authorization'] = (
        'AWS4-HMAC-SHA256 Credential={}/{}, SignedHeaders={}, Signature={}'
        .format(access_key, scope, signed_headers, signature))
    return urllib.request.Request(S3_ENDPOINT + path, headers=headers)


def make_request(tbl):
    if SOURCE.startswith('s3://'):
        bucket = SOURCE[len('s3://'):].strip('/')
        return s3_request(bucket, tbl + '.parquet')
    return urllib.request.Request('{}/{}.parquet'.format(SOURCE, tbl))


def fetch(tbl, path, retries=3):
    'Download a table to path. Returns False if it does not exist in the source.'
    for attempt in range(1, retries + 1):
        try:
            # build the request on every attempt: S3 signatures are time-limited
            with urllib.request.urlopen(make_request(tbl), timeout=120) as r, \
                    open(path + '.part', 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            os.replace(path + '.part', path)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if e.code == 403:
                raise SystemExit('Access denied to {} (credentials?)'.format(tbl))
            if attempt == retries:
                raise
            print('  retry {} after: {}'.format(attempt, e), flush=True)
            time.sleep(5 * attempt)
        except OSError as e:
            if attempt == retries:
                raise
            print('  retry {} after: {}'.format(attempt, e), flush=True)
            time.sleep(5 * attempt)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parquet')
    os.makedirs(target, exist_ok=True)
    t0 = time.time()
    for tbl in TABLES:
        path = os.path.join(target, tbl + '.parquet')
        if os.path.exists(path):
            print('have  ', tbl, flush=True)
            continue
        print('fetch ', tbl, flush=True)
        if not fetch(tbl, path):
            print('  not in source, skipped', flush=True)
    size = sum(os.path.getsize(os.path.join(target, t + '.parquet'))
               for t in TABLES if os.path.exists(os.path.join(target, t + '.parquet')))
    print('{:.0f} MB in {} ({:.0f}s)'.format(size / 1e6, target, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
