import os

from PassUI import passpy_api, utils


def read_write_gpg(store_dir, gpg_id, gpg_bin, path_rel, key_data):
    path_gpg = os.path.join(store_dir, path_rel + ".gpg")
    utils.write_gpg(path_gpg, key_data, gpg_bin, [gpg_id])
    output = utils.read_gpg(path_gpg, gpg_bin)
    assert output == key_data


def read_write_gpg_obj(store_dir, path_rel, key_data):
    path_gpg = os.path.join(store_dir, path_rel + ".gpg")
    passpy_obj = passpy_api.PassPy()
    passpy_obj.write_gpg(path_gpg, key_data)
    output = passpy_obj.read_gpg(path_gpg)
    print(f"{key_data = }")
    print(f"{output = }")
    assert output == key_data


def read_write_gpg_key(path_rel, data_dict):
    passpy_obj = passpy_api.PassPy()
    passpy_obj.write_key(path_rel, data_dict)
    output = passpy_obj.read_key(path_rel)
    assert output == data_dict


if __name__ == "__main__":
    store_dir = r"C:\Users\vince\Documents\GDriveGadz\PASS"
    gpg_key_str = "09EB7E77B807ECE7F91942E273C8C7C8A0775A19"
    path_bin_gpg = r"C:\Program Files (x86)\GnuPG\bin\gpg.exe"
    path_rel = "bla_key"
    data_str = "bla\nuser: bli"
    data_dict = {"PASSWORD": "bla", "user": "bli"}
    path_abs_gpg = r"C:\Users\vince\Documents\GDriveGadz\PASS\sante\aggema.gpg"

    # read_write_gpg(store_dir, gpg_key_str, path_bin_gpg, path_rel, data_str)
    # read_write_gpg_obj(store_dir, path_rel, data_str)
    # read_write_gpg_key(path_rel, data_dict)
    print(utils.read_gpg(path_abs_gpg, path_bin_gpg))