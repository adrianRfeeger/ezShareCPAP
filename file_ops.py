import datetime
import re
import requests
import bs4
import urllib.parse
import logging
from tempfile import NamedTemporaryFile
import pathlib
import os

logger = logging.getLogger(__name__)

def recursive_traversal(ezshare_instance, url, dir_path, total_files, processed_files, is_running):
    """
    Recursively traverse directories to list and download files.

    :param ezshare_instance: Instance of the main application containing settings and states.
    :param url: URL of the directory to traverse.
    :param dir_path: Local directory path to store the files.
    :param total_files: Total number of files expected to be processed.
    :param processed_files: Count of files already processed.
    :param is_running: Function to check if the process should continue running.
    :return: Updated count of processed files.
    """
    files, dirs = list_dir(ezshare_instance, url)
    processed_files = check_files(ezshare_instance, files, url, dir_path, total_files, processed_files, is_running)
    processed_files = check_dirs(ezshare_instance, dirs, url, dir_path, total_files, processed_files, is_running)
    return processed_files

def list_dir(ezshare, url):
    """
    Fetch and parse directory listing from the given URL.

    :param ezshare: Instance of the main application containing settings and states.
    :param url: URL of the directory to list.
    :return: Tuple of (files, directories).
    """
    try:
        response = ezshare.session.get(url, timeout=5)
        response.raise_for_status()
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        files, dirs = parse_directory_listing(ezshare, soup)
        return files, dirs
    except requests.RequestException as e:
        logger.error(f"Error fetching directory listing from {url}: {e}")
        return [], []

import bs4

import re
import bs4
import datetime
import urllib.parse

import re
import bs4
import datetime
import urllib.parse
import logging

def parse_directory_listing(ezshare, soup):
    """
    Parse the HTML directory listing to separate files and directories.

    :param ezshare: Instance of the main application containing settings and states.
    :param soup: BeautifulSoup object containing the parsed HTML.
    :return: Tuple of (files, directories).
    """
    files = []
    dirs = []
    
    # Find the <pre> tag
    pre_tag = soup.find('pre')
    
    # Check if <pre> tag exists
    if pre_tag is None:
        logging.error("No <pre> tag found in the HTML response.")
        return files, dirs  # Return empty lists if <pre> tag is not found
    
    pre_text = pre_tag.decode_contents()  # Extract content from <pre> tag
    lines = pre_text.split('\n')  # Split the content by lines

    for line in lines:
        if line.strip():  # Check if the line is not empty
            parts = line.rsplit(maxsplit=2)  # Split the line into parts
            modifypart = parts[0].replace('- ', '-0').replace(': ', ':0')  # Fix timestamp formatting
            regex_pattern = r'\d*-\d*-\d*\s*\d*:\d*:\d*'  # Regex pattern to match the timestamp
            match = re.search(regex_pattern, modifypart)  # Search for the timestamp
            file_ts = datetime.datetime.strptime(match.group(), '%Y-%m-%d %H:%M:%S').timestamp() if match else 0  # Convert to timestamp
            
            # Parse the line as HTML to extract the link
            soupline = bs4.BeautifulSoup(line, 'html.parser')
            link = soupline.a
            if link:
                link_text = link.get_text(strip=True)  # Get the link text
                link_href = link['href']  # Get the href attribute of the link
                
                # Ignore files that should be ignored or hidden
                if link_text in ezshare.ignore or link_text.startswith('.'):
                    continue
                
                # Parse the URL
                parsed_url = urllib.parse.urlparse(link_href)
                
                # Check if the link is for a file or directory
                if parsed_url.path.endswith('download'):
                    files.append((link_text, parsed_url.query, file_ts))  # Add file to the list
                elif parsed_url.path.endswith('dir'):
                    dirs.append((link_text, link_href))  # Add directory to the list
    
    return files, dirs





def check_files(ezshare_instance, files, url, dir_path, total_files, processed_files, is_running):
    """
    Process each file in the list, downloading if necessary.

    :param ezshare_instance: Instance of the main application containing settings and states.
    :param files: List of files to process.
    :param url: URL of the directory containing the files.
    :param dir_path: Local directory path to store the files.
    :param total_files: Total number of files expected to be processed.
    :param processed_files: Count of files already processed.
    :param is_running: Function to check if the process should continue running.
    :return: Updated count of processed files.
    """
    for filename, file_url, file_ts in files:
        if not is_running():
            ezshare_instance.update_status('Process cancelled.', 'info')
            break

        local_path = dir_path / filename
        absolute_file_url = urllib.parse.urljoin(url, 'download?' + file_url)
        
        if should_download(ezshare_instance, local_path, file_ts):
            progress_msg = f'Downloading file "{filename}" {processed_files + 1}/{total_files}'
            ezshare_instance.update_status(progress_msg + (f" ({int((processed_files + 1) / total_files * 100)}%)" if total_files else " (0%)"))
            if download_file(ezshare_instance, absolute_file_url, local_path, file_ts):
                processed_files += 1
                progress_value = (processed_files / total_files) * 100
                ezshare_instance.update_progress(min(max(0, progress_value), 100))
    return processed_files

def should_download(ezshare_instance, local_path, file_ts):
    """
    Determine if a file should be downloaded based on its timestamp and existence.

    :param ezshare_instance: Instance of the main application containing settings and states.
    :param local_path: Local file path.
    :param file_ts: Timestamp of the remote file.
    :return: True if the file should be downloaded, False otherwise.
    """
    return not (local_path.is_file() and not (ezshare_instance.overwrite or local_path.stat().st_mtime < file_ts) and not ezshare_instance.keep_old)

def download_file(ezshare_instance, url, file_path, file_ts=None):
    """
    Download a file from the given URL and save it locally.

    :param ezshare_instance: Instance of the main application containing settings and states.
    :param url: URL of the file to download.
    :param file_path: Local path where the file should be saved.
    :param file_ts: Optional timestamp to set on the downloaded file.
    :return: True if the file was downloaded successfully, False otherwise.
    """
    try:
        response = ezshare_instance.session.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        if total_size == 0:
            logger.warning('File %s has zero total size, skipping progress update.', str(file_path))
            with file_path.open('wb') as f:
                pass
            return True

        with NamedTemporaryFile(delete=False, dir=file_path.parent) as tmp_file:
            for data in response.iter_content(1024):
                if not ezshare_instance._is_running:
                    logger.info('Cancelling download of %s', str(file_path))
                    tmp_file.close()
                    pathlib.Path(tmp_file.name).unlink()
                    return False
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

def check_dirs(ezshare_instance, dirs, url, dir_path, total_files, processed_files, is_running):
    """
    Recursively process each directory in the list.

    :param ezshare_instance: Instance of the main application containing settings and states.
    :param dirs: List of directories to process.
    :param url: URL of the current directory being processed.
    :param dir_path: Local directory path to store files.
    :param total_files: Total number of files expected to be processed.
    :param processed_files: Count of files already processed.
    :param is_running: Function to check if the process should continue running.
    :return: Updated count of processed files.
    """
    for dirname, dir_url in dirs:
        if not is_running():
            ezshare_instance.update_status('Process cancelled.', 'info')
            break

        new_dir_path = dir_path / dirname
        new_dir_path.mkdir(exist_ok=True)
        absolute_dir_url = urllib.parse.urljoin(url, dir_url)
        processed_files = recursive_traversal(ezshare_instance, absolute_dir_url, new_dir_path, total_files, processed_files, is_running)
    return processed_files

def cleanup_temp_files(ezshare_instance):
    """
    Cleanup any temporary files or directories that were created during the process.
    This ensures no leftover files are hanging around after a cancellation.

    :param ezshare_instance: Instance of the main application containing settings and states.
    """
    temp_dir = pathlib.Path(ezshare_instance.path).parent / "temp"
    if temp_dir.exists():
        logger.info(f"Cleaning up temporary directory: {temp_dir}")
        for temp_file in temp_dir.glob("*"):
            try:
                temp_file.unlink()
            except Exception as e:
                logger.error(f"Error deleting temporary file {temp_file}: {e}")
        try:
            temp_dir.rmdir()
        except Exception as e:
            logger.error(f"Error removing temporary directory {temp_dir}: {e}")
    else:
        logger.debug("No temporary directory found for cleanup.")
