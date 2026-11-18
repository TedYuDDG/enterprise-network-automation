"""Read-only Cisco IOS inventory, configuration backup and health checks."""
import argparse
import getpass
import ipaddress
import json
import re
from pathlib import Path
from datetime import datetime, timezone

COMMANDS = ('show ip interface brief', 'show ip route', 'show ip ospf neighbor')


def load_inventory(path):
    devices = json.loads(Path(path).read_text())
    names = set()
    if not isinstance(devices, list) or not devices:
        raise ValueError('Inventory must be a nonempty list')
    for d in devices:
        name = d['name']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in names:
            raise ValueError('Device names must be unique and filesystem-safe')
        names.add(name)
        ipaddress.ip_address(d['host'])
        if not isinstance(d.get('expected_interfaces', []), list):
            raise ValueError('expected_interfaces must be a list')
    return devices


def analyse(device, outputs):
    issues = []
    lines = outputs[COMMANDS[0]].splitlines()
    interfaces = {}
    for line in lines:
        fields = line.split()
        if len(fields) >= 6 and fields[0] != 'Interface':
            interfaces[fields[0]] = (' '.join(fields[4:-1]), fields[-1])
    for name in device.get('expected_interfaces', []):
        if interfaces.get(name) != ('up', 'up'):
            issues.append(f'Expected interface {name} is not up/up or missing')
    full = set()
    for line in outputs[COMMANDS[2]].splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[2].startswith('FULL'):
            full.add(fields[0])
    for neighbor in device.get('expected_ospf_neighbors', []):
        if neighbor not in full:
            issues.append(f'Expected OSPF neighbor {neighbor} is not FULL or missing')
    if device.get('expect_default_route') and not re.search(r'(?m)^\s*[A-Z][A-Z0-9* ]*\s+0\.0\.0\.0/0\b', outputs[COMMANDS[1]]):
        issues.append('Expected default route missing')
    return issues


def demo_collect(device):
    name = device['name']
    fault = name == 'R2'
    return {COMMANDS[0]: 'Interface IP-Address OK? Method Status Protocol\nGigabitEthernet0/0 192.0.2.1 YES manual ' + ('down down' if fault else 'up up'), COMMANDS[1]: 'O*E2 0.0.0.0/0 [110/1] via 192.0.2.254', COMMANDS[2]: 'Neighbor ID Pri State Dead Time Address Interface\n' + ('' if fault else '2.2.2.2 1 FULL/DR 00:00:30 192.0.2.2 GigabitEthernet0/0'), 'show running-config': f'! SYNTHETIC DEMO CONFIG\nhostname {name}\n!'}


def live_collect(device, username, password):
    from netmiko import ConnectHandler
    with ConnectHandler(device_type='cisco_ios', host=device['host'], username=username, password=password, conn_timeout=10, auth_timeout=10, banner_timeout=10, ssh_strict=True, system_host_keys=True) as connection:
        result = {}
        for command in (*COMMANDS, 'show running-config'):
            output = connection.send_command(command, read_timeout=30)
            if not output.strip() or re.search(r'(?im)^\s*%\s*(invalid|incomplete|ambiguous|authorization|error)', output):
                raise RuntimeError(f'Command failed: {command}')
            result[command] = output
        return result


def run(devices, collector, output_dir, mode):
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    rows = []
    for device in devices:
        name = device['name']
        try:
            outputs = collector(device)
            issues = analyse(device, outputs)
            # Running configs may contain secrets; keep local and restrict file permissions.
            backup = folder / f'{name}.cfg'
            with backup.open('x') as f:
                backup.chmod(0o600)
                f.write(outputs['show running-config'])
            rows.append({'device': name, 'status': 'warning' if issues else 'healthy', 'issues': issues})
        except Exception as exc:
            rows.append({'device': name, 'status': 'error', 'issues': [type(exc).__name__]})
    report = {'mode': mode, 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'devices': rows}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', default='inventory.example.json')
    p.add_argument('--output', default='output')
    p.add_argument('--live', action='store_true', help='Use authorized Cisco devices instead of synthetic fixtures')
    args = p.parse_args()
    devices = load_inventory(args.inventory)
    if args.live:
        username = input('SSH username: ')
        password = getpass.getpass('SSH password: ')
        collector = lambda d: live_collect(d, username, password)
    else:
        collector = demo_collect
    folder = Path(args.output) / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = run(devices, collector, folder, 'live' if args.live else 'synthetic-demo')
    print(json.dumps(report, indent=2))
    print(f'Report saved to {folder}')
    return int(any(d['status'] != 'healthy' for d in report['devices']))


if __name__ == '__main__':
    raise SystemExit(main())
