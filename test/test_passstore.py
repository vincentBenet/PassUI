import os
import tempfile
from PassUI import passstore


def test_init():
    passstore.PassStore()


def test_change_path_store():
    path_abs_tmp = tempfile.TemporaryDirectory().name
    os.makedirs(path_abs_tmp)
    passstore_obj = passstore.PassStore()
    assert passstore_obj.change_path_store(path_abs_tmp)
    assert passstore_obj.path_store == path_abs_tmp
    assert os.path.isfile(os.path.join(
        passstore_obj.path_store,
        ".gpg-id"
    ))


def test_wr():
    passstore_obj = passstore.PassStore()
    data_input = {
        "PASSWORD": "test",
        "test": "test",
    }
    passstore_obj.write_key("test", data_input)
    assert "test" in passstore_obj.rel_paths_gpg
    assert os.path.isfile(os.path.join(passstore_obj.path_store, "test" + ".gpg"))
    data_output = passstore_obj.read_key("test")
    assert data_input == data_output
    for key in data_input:
        assert data_input[key] == data_output[key]
    os.remove(os.path.join(passstore_obj.path_store, "test" + ".gpg"))
