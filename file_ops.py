import pathlib
import requests
import datetime
import bs4
import urllib.parse
import re
import os
import logging
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)

def recursive_traversal(ezshare, url, dir_path, total_files, processed_files):
    files, dirs = list_dir(ezshare, url)
    processed_files = check_files(ezshare, files, url, dir_path, total_files, processed_files)
    processed_files = check_dirs(ezshare, dirs, url, dir_path, total_files, processed_files)
    return processed_files

def list_dir(ezshare, url):
    try:
        html_content = requests.get(url, timeout=5)
        soup = bs4.BeautifulSoup(html_content.text, 'html.parser')
    except requests.RequestException as e:
        logger.error(f"Error fetching directory listing from {url}: {e}")
        return [], []

    files = []
    dirs = []

    pre_text = soup.find('pre').decode_contents()
    lines = pre_text.split('\n')

    for line in lines:
        if line.strip():
            parts = line.rsplit(maxsplit=2)
            modifypart = parts[0].replace('- ', '-0').replace(': ', ':0')
            regex_pattern = r'\d*-\d*-\d*\s*\d*:\d*:\d*'

            match = re.search(regex_pattern, modifypart)
            file_ts = datetime.datetime.strptime(match.group(), '%Y-%m-%d   %H:%M:%S').timestamp() if match else 0

            soupline = bs4.BeautifulSoup(line, 'html.parser')
            link = soupline.a
            if link:
                link_text = link.get_text(strip=True)
                if link_text == 'STR.EDF':
                    link_text = 'STR.edf'

                link_href = link['href']
                if link_text in ezshare.ignore or link_text.startswith('.'):
                    continue

                parsed_url = urllib.parse.urlparse(link_href)
                if parsed_url.path.endswith('download'):
                    files.append((link_text, parsed_url.query, file_ts))
                elif parsed_url.path.endswith('dir'):
                    dirs.append((link_text, link_href))
    return files, dirs

def check_files(ezshare, files, url, dir_path: pathlib.Path, total_files, processed_files):
    for filename, file_url, file_ts in files:
        local_path = dir_path / filename
        absolute_file_url = urllib.parse.urljoin(url, f'download?{file_url}')
        
        if should_download(ezshare, local_path, file_ts):
            progress_msg = f'Downloading file "{filename}" {processed_files + 1}/{total_files}'
            ezshare.update_status(progress_msg + (f" ({int((processed_files + 1) / total_files * 100)}%)" if total_files else " (0%)"))
            if download_file(ezshare, absolute_file_url, local_path, file_ts):
                processed_files += 1
                progress_value = (processed_files / total_files) * 100
                ezshare.update_progress(progress_value)
    return processed_files

def should_download(ezshare, local_path: pathlib.Path, file_ts):
    return not (local_path.is_file() and not (ezshare.overwrite or local_path.stat().st_mtime < file_ts) and not ezshare.keep_old)


def download_file(ezshare, url, file_path: pathlib.Path, file_ts=None):
    if file_path.is_file() and not (ezshare.overwrite or file_path.stat().st_mtime < file_ts) and not ezshare.keep_old:
        logger.info('File %s already exists and has not been updated. Skipping because overwrite is off.', str(file_path))
        return False

    logger.debug('Downloading %s from %s', str(file_path), url)
    try:
        response = ezshare.session.get(url, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Error downloading file {file_path}: {e}')
        return False

    total_size = int(response.headers.get('content-length', 0))
    if total_size == 0:
        logger.warning('File %s has zero total size, skipping progress update.', str(file_path))
        with file_path.open('wb'):
            pass
        return True

    try:
        with NamedTemporaryFile(delete=False, dir=file_path.parent) as tmp_file:
            for data in response.iter_content(1024):
                tmp_file.write(data)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_file_path = pathlib.Path(tmp_file.name)
            tmp_file_path.replace(file_path)
            logger.info('%s written', str(file_path))
            if file_ts:
                os.utime(file_path, (file_ts, file_ts))
    except Exception as e:
        logger.error(f'Error downloading file {file_path}: {e}')
        return False

    return True

def check_dirs(ezshare, dirs, url, dir_path: pathlib.Path, total_files, processed_files):
    for dirname, dir_url in dirs:
        new_dir_path = dir_path / dirname
        new_dir_path.mkdir(exist_ok=True)
        absolute_dir_url = urllib.parse.urljoin(url, dir_url)
        processed_files = recursive_traversal(ezshare, absolute_dir_url, new_dir_path, total_files, processed_files)
    return processed_files
