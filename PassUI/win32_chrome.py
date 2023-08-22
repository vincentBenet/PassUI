import keyring

if __name__ == "__main__":
    print(keyring.get_keyring().get_password("system", "username"))