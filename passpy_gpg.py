"""
File from https://github.com/bfrascher/passpy
"""

import os

from gnupg import GPG


def _get_gpg_recipients(path):
    """Get the GPG recipients for the given path.

    :param str path: The directory to get the GPG recipients for.

    :raises FileNotFoundError: if there is not valid .gpg-id file for
        path.

    :rtype: list
    :returns: The list of IDs of the GPG recipients for the given
        path.

    """
    while True:
        gpg_id_path = os.path.join(path, '.gpg-id')
        if os.path.isfile(gpg_id_path):
            break
        path = os.path.dirname(path)

    if path is None or path == '':
        raise FileNotFoundError(
                'You must initialise the password store first!')

    with open(gpg_id_path) as gpg_id_file:
        gpg_recipients = [line.rstrip('\n') for line in gpg_id_file]
    return gpg_recipients


def read_key(path, gpg_bin, gpg_opts):
    """Read and decrypt a single key file.

    :param str path: The path to the key to decrypt.

    :param str gpg_bin: The path to the gpg binary.

    :param list gpg_opts: The options for gpg.

    :rtype: str
    :returns: The unencrypted content of the file at `path`.

    """
    gpg = GPG(gpgbinary=gpg_bin, options=gpg_opts)
    with open(path, 'rb') as key_file:
        return str(gpg.decrypt_file(key_file))


def write_key(path, key_data, gpg_bin, gpg_recipients, gpg_opts=None):
    """Encrypt and write a single key file.

    :param str key_data: The data to encrypt

    :param str path: The path to the key to decrypt.

    :param str gpg_bin: The path to the gpg binary.

    :param list gpg_opts: The options for gpg.

    """
    gpg = GPG(gpgbinary=gpg_bin, options=gpg_opts)
    if not key_data.endswith('\n'):
        key_data += '\n'
    key_data_enc = gpg.encrypt(key_data, _get_gpg_recipients(gpg_recipients)).data
    with open(path, 'wb') as key_file:
        key_file.write(key_data_enc)


def _reencrypt_key(path, gpg, gpg_recipients):
    """Reencrypt a single key.

    Gets called from :func:`passpy.gpg._reencrypt_path`.

    :param str path: The path to a gpg encrypted file.

    :param gpg: The gpg object.
    :type gpg: :class:`gnupg.GPG`

    :param list gpg_recipients: The list of GPG Ids to encrypt the key
        with.

    """
    with open(path, 'rb') as key_file:
        key_data = gpg.decrypt_file(key_file).data
    key_data_enc = gpg.encrypt(key_data, gpg_recipients).data
    with open(path, 'wb') as key_file:
        key_file.write(key_data_enc)


def reencrypt_path(path, gpg_bin, gpg_opts):
    """Reencrypt a single or multiple keys.

    If path is a directory all keys inside that directory and it's
    subdirectories will be reencrypted.

    :param str path: The key or directory to reencrypt.  If ``None``
        the function will silently fail.

    :param str gpg_bin: The path to the gpg binary.

    :param list gpg_opts: The gpg options.

    :raises FileNotFoundError: if path does not exist.

    """
    if path is None:
        return
    gpg = GPG(gpgbinary=gpg_bin, options=gpg_opts)
    if os.path.isfile(path):
        gpg_recipients = _get_gpg_recipients(path)
        _reencrypt_key(path, gpg, gpg_recipients)
    elif os.path.isdir(path):
        for root, dirs, keys in os.walk(path):
            gpg_recipients = _get_gpg_recipients(root)
            for key in keys:
                if not key.endswith('.gpg'):
                    continue
                key_path = os.path.join(root, key)
                _reencrypt_key(key_path, gpg, gpg_recipients)
    else:
        raise FileNotFoundError('{0} does not exist.'.format(path))