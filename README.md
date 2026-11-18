# Enterprise Network Automation & Monitoring Lab

A personal learning lab for Python-based Cisco IOS operations: inventory, read-only SSH configuration backups, interface and OSPF checks, and JSON health reports. Initial implementation assisted by AI; live-device integration is not yet verified.

## Quick start (macOS/Linux)

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python network_lab.py
python -m pytest -q
```

The demo uses synthetic Cisco command outputs and documentation-only IP addresses. R1 is healthy; R2 intentionally has an interface and OSPF fault. Exit code 1 indicates a warning or failure, not necessarily a program crash. Reports and backups are saved in timestamped folders under `output/` (ignored by Git).

## Live lab (next milestone)

Use only devices you own or have explicit permission to manage, such as an authorized Cisco lab. Packet Tracer does not generally expose real SSH to external Netmiko clients. Use a suitable lab with reachable IOS devices instead. Create `inventory.local.json` from the example, set actual addresses and expected interface names/OSPF router IDs, and independently verify SSH host keys before adding them to your local known_hosts. Run:

```sh
python network_lab.py --inventory inventory.local.json --live
```

The program prompts for credentials and uses strict SSH host-key verification. Use an account authorized to run the four read-only show commands. Never upload real running configurations or credentials; configuration backups may contain sensitive data. Report statuses represent configured checks only, not comprehensive network health. The OSPF check expects FULL adjacency only for explicitly configured neighbors; DROTHER relationships need different expectations. The default-route check expects common IOS IPv4 route output. No configuration changes are performed.

## Architecture

Inventory JSON → per-device collector (synthetic or Netmiko SSH) → interface/route/OSPF checks → local configuration backup + JSON report. A failed device does not stop collection from others.

## Learning roadmap

1. Run demo and understand every function; add a custom simulated fault.
2. Build or access an authorized IOS lab; configure management addressing and SSH.
3. Run live backup and compare with manually collected show output.
4. Validate interface and OSPF failures, recovery, authentication failure, and default-route checks; record actual results.
5. Add configuration comparison and richer troubleshooting reports after baseline validation.

## Evidence status

Synthetic fixtures and unit tests are not proof of live network operation. Record actual devices, commands, results, and personal contributions after completing lab work. Do not describe this as production experience.
