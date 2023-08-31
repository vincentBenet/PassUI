import os
import tempfile
from PassUI import gpg


def test_init():
    gpg_obj = gpg.GPG()
    gpg_obj.remove_key()
    assert len(gpg_obj.list_keys()) == 0
    gpg_obj.create_key(
        name="test",
        mail="test.test@test.test",
        passphrase="test",
    )
    assert len(gpg_obj.list_keys()) == 1
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path_tmp_1 = tmp.name
    gpg_obj.write(path_tmp_1, "test", passphrase="test")
    assert gpg_obj.read(path_tmp_1, passphrase="test") == "test"
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path_tmp_2 = tmp.name
    keys = gpg_obj.list_keys()
    key = keys[0]['key']
    gpg_obj.export_key(path_tmp_2, key=key, passphrase="test")
    gpg_obj.remove_key()
    assert key not in gpg_obj.list_keys()
    gpg_obj.import_key(path_tmp_2, passphrase="test")
    assert gpg_obj.read(path_tmp_1, passphrase="test") == "test"
    gpg_obj.write(path_tmp_1, "test", passphrase="test")
    assert gpg_obj.read(path_tmp_1, passphrase="test") == "test"
    os.remove(path_tmp_1)
    os.remove(path_tmp_2)
