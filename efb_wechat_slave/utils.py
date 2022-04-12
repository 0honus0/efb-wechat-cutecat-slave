import logging
import tempfile
import threading
import requests as requests

def download_file(url: str, retry: int = 3) -> tempfile:
    """
    A function that downloads files from given URL
    Remember to close the file once you are done with the file!
    :param retry: The max retries before giving up
    :param url: The URL that points to the file
    """
    count = 1
    while True:
        try:
            file = tempfile.NamedTemporaryFile()
            r = requests.get(url, stream=True, timeout=10)
            r.raise_for_status()  # Replace this with better error handling.

            for chunk in r.iter_content(1024):
                file.write(chunk)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error occurred when downloading {url}. {e}")
            if count >= retry:
                logging.getLogger(__name__).warning(f"Maximum retry reached. Giving up.")
                raise e
            count += 1
        else:
            break
    return file