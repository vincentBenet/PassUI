import os
import tempfile
from PassUI import gpg


def test_init_driver():
    gpg.GPG()


def test_remove_keys():
    gpg_obj = gpg.GPG()
    gpg_obj.remove_key()
    assert len(gpg_obj.list_keys()) == 0


def test_list_keys():
    gpg_obj = gpg.GPG()
    assert isinstance(gpg_obj.list_keys(), list)


def test_create_key():
    gpg_obj = gpg.GPG()
    gpg_obj.remove_key()
    gpg_obj.create_key(
        name="test",
        mail="test.test@test.test",
        passphrase="test",
    )
    keys = gpg_obj.list_keys()
    assert len(keys) == 1
    assert isinstance(keys, list)
    dico = keys[0]
    assert isinstance(dico, dict)
    for k, v in dico.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
    assert dico["mail"] == "test.test@test.test"
    assert dico["user"] == "test"


def test_rw_created():
    gpg_obj = gpg.GPG()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path_tmp = tmp.name
    gpg_obj.write(path_tmp, "test", passphrase="test")
    assert gpg_obj.read(path_tmp, passphrase="test") == "test"
    os.remove(path_tmp)


def test_rw_import():
    gpg_obj = gpg.GPG()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path_tmp_key = tmp.name
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path_tmp_password = tmp.name
    keys = gpg_obj.list_keys()
    key = keys[0]['key']
    gpg_obj.export_key(path_tmp_key, key=key, passphrase="test")
    gpg_obj.remove_key()
    assert key not in gpg_obj.list_keys()
    assert len(gpg_obj.list_keys()) == 0
    gpg_obj.import_key(path_tmp_key, passphrase="test")
    assert len(gpg_obj.list_keys()) == 1
    os.remove(path_tmp_key)
    gpg_obj.write(path_tmp_password, "test", passphrase="test")
    assert gpg_obj.read(path_tmp_password, passphrase="test") == "test"
    os.remove(path_tmp_password)
