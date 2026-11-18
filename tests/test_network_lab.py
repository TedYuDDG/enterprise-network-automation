import json
import pytest
from network_lab import analyse, demo_collect, load_inventory, run, COMMANDS

DEVICE = {'name':'R1','host':'192.0.2.1','expected_interfaces':['GigabitEthernet0/0'],'expected_ospf_neighbors':['2.2.2.2'],'expect_default_route':True}


def test_healthy():
    assert analyse(DEVICE, demo_collect(DEVICE)) == []


def test_fault():
    assert len(analyse(DEVICE, demo_collect(dict(DEVICE, name='R2')))) == 2


def test_missing_default():
    outputs = demo_collect(DEVICE)
    outputs[COMMANDS[1]] = 'Gateway of last resort is not set'
    assert 'Expected default route missing' in analyse(DEVICE, outputs)


def test_admin_down():
    outputs = demo_collect(DEVICE)
    outputs[COMMANDS[0]] = 'GigabitEthernet0/0 192.0.2.1 YES manual administratively down down'
    assert len(analyse(DEVICE, outputs)) == 1


def test_failure_isolation(tmp_path):
    def collect(d):
        if d['name'] == 'R1':
            raise TimeoutError('secret detail')
        return demo_collect(d)
    result = run([DEVICE, dict(DEVICE, name='R3')], collect, tmp_path, 'test')
    assert [d['status'] for d in result['devices']] == ['error', 'healthy']
    assert (tmp_path / 'R3.cfg').exists()
    assert 'secret detail' not in (tmp_path / 'report.json').read_text()


def test_unsafe_inventory(tmp_path):
    p = tmp_path / 'inventory.json'
    p.write_text(json.dumps([dict(DEVICE, name='../bad')]))
    with pytest.raises(ValueError):
        load_inventory(p)


def test_duplicate_inventory(tmp_path):
    p = tmp_path / 'inventory.json'
    p.write_text(json.dumps([DEVICE, DEVICE]))
    with pytest.raises(ValueError):
        load_inventory(p)
