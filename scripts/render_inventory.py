#!/usr/bin/env python3
"""Render a small Ansible inventory from Terraform JSON outputs."""

import json
import sys


def read_output(name, outputs, default=""):
    value = outputs.get(name, {}).get("value", default)
    return value if value is not None else default


def main():
    outputs = json.load(sys.stdin)
    public_ip = read_output("instance_public_ip", outputs)
    private_ip = read_output("instance_private_ip", outputs)
    ssh_user = read_output("ssh_user", outputs, "opc")

    if not public_ip:
        raise SystemExit("Terraform output instance_public_ip is empty.")

    print("[meridian]")
    print(
        "meridian-oci "
        f"ansible_host={public_ip} "
        f"ansible_user={ssh_user} "
        f"private_ip={private_ip}"
    )
    print("")
    print("[meridian:vars]")
    print("ansible_python_interpreter=/usr/bin/python3")


if __name__ == "__main__":
    main()

