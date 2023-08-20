import re
import subprocess


def run(command):
    # print("run")
    # print(f"\t{command_list = }")
    output = subprocess.check_output(command, shell=True).decode("utf-8", "ignore")
    # print(f"\t{output = }")
    return output


def extract_wifi_pass(wifi_name, regex_pass_before, regex_pass_after, command_pass):
    output = run(command_pass % wifi_name)
    regex = f"(?<={regex_pass_before})(.*)(?={regex_pass_after})"
    res = re.findall(regex, output)
    if not res:
        print(f"Error extracting wifi password for '{wifi_name}': \n\tOUTPUT = {repr(output)}\n\tREGEX = {repr(regex)}\n")
        return ""
    return res[0]


def get_wifis_ssid(regex_ssid_before, regex_ssid_after, command_ssid):
    output = run(command_ssid)
    print(f"get_wifis_ssid : \n-----\n{repr(output)}")
    regex = f"(?<={regex_ssid_before})(.*)(?={regex_ssid_after})"
    wifi_names = re.findall(regex, output)
    if not wifi_names:
        print(f"Error extracting wifis ssid: \n\tOUTPUT = {repr(output)}\n\tREGEX = {repr(regex)}")
    return wifi_names


def main(
    regex_ssid_before,
    regex_ssid_after,
    regex_pass_before,
    regex_pass_after,
    command_ssid,
    command_pass,
):
    res = {}
    wifi_names = get_wifis_ssid(regex_ssid_before, regex_ssid_after, command_ssid)
    for wifi_name in wifi_names:
        wifi_pass = extract_wifi_pass(wifi_name, regex_pass_before, regex_pass_after, command_pass)
        if len(wifi_pass):
            res[wifi_name] = wifi_pass
    print(res)
    return res


if __name__ == "__main__":
    print(main(
        "Profil Tous les utilisateurs    : ",
        "\r\n",
        "Contenu de la cl            : ",
        "\r\n",
        "netsh wlan show profiles",
        'netsh wlan show profile "%s" key=clear',
    ))
