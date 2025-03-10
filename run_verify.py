#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Running verification workchain
"""
import os
import click

import aiida
from aiida import orm
from aiida.plugins import DataFactory

from aiida_sssp_workflow.workflows.verifications import DEFAULT_PROPERTIES_LIST, DEFAULT_CONVERGENCE_PROPERTIES_LIST

from sssp_verify_scripts import run_verification

UpfData = DataFactory('pseudo.upf')

SSSP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_sssp')

def inputs_from_mode(mode, computer_label, properties_list):
    if computer_label == 'imx':
        computer = 'imxgesrv1'
        mpiprocs = 32
        npool = 4
        walltime = 3600
    elif computer_label == 'daint-mc':
        computer = f'daint-mc'
        mpiprocs = 36
        npool = 4
        walltime = 1800

    else:
        computer = f'eiger-mc-{computer_label}'
        mpiprocs = 128
        npool = 16
        walltime = 1800
        
    inputs = {}
    if mode == 'TEST':
        inputs['pw_code'] = orm.load_code('pw-6.7@localhost')
        inputs['ph_code'] = orm.load_code('ph-6.7@localhost')
        inputs['protocol'] = orm.Str('test')
        inputs['cutoff_control'] = orm.Str('test')
        inputs['criteria'] = orm.Str('efficiency')
        inputs['options'] = orm.Dict(
            dict={
                "resources": {
                    "num_machines": 1,
                    "num_mpiprocs_per_machine": 1
                },
                "max_wallclock_seconds": 1800,
                "withmpi": False,
            }
        )
        inputs['parallization'] = orm.Dict(dict={})
        inputs['properties_list'] = orm.List(list=properties_list)
        
    if mode == 'PRECHECK':
        inputs['pw_code'] = orm.load_code(f'pw-7.0@{computer}')
        inputs['ph_code'] = orm.load_code(f'ph-7.0@{computer}')
        inputs['protocol'] = orm.Str('acwf')
        inputs['cutoff_control'] = orm.Str('precheck')
        inputs['criteria'] = orm.Str('precision')
        inputs['options'] = orm.Dict(
            dict={
                "resources": {
                    "num_machines": 1,
                    "num_mpiprocs_per_machine": mpiprocs,
                    "num_cores_per_mpiproc": 1
                },
                "max_wallclock_seconds": walltime,
                "withmpi": True,
            }
        )
        inputs['parallization'] = orm.Dict(dict={'npool': npool})
        inputs['properties_list'] = orm.List(list=properties_list)
        
    if mode == 'STANDARD':
        inputs['pw_code'] = orm.load_code(f'pw-7.0@{computer}')
        inputs['ph_code'] = orm.load_code(f'ph-7.0@{computer}')
        inputs['protocol'] = orm.Str('acwf')
        inputs['cutoff_control'] = orm.Str('standard')
        inputs['criteria'] = orm.Str('efficiency')
        inputs['options'] = orm.Dict(
            dict={
                "resources": {
                    "num_machines": 1,
                    "num_mpiprocs_per_machine": mpiprocs,
                    "num_cores_per_mpiproc": 1
                },
                "max_wallclock_seconds": walltime,
                "withmpi": True,
            }
        )
        inputs['parallization'] = orm.Dict(dict={'npool': npool})
        inputs['properties_list'] = orm.List(list=properties_list)
        
    return inputs

@click.command()
@click.option('profile', '-p', help='profile')
@click.option('--mode', type=click.Choice(['TEST', 'PRECHECK', 'STANDARD'], case_sensitive=False), 
              help='mode of verification.')
@click.option('--computer', type=click.Choice(['mr0', 'mr32', 'imx', 'daint-mc'], case_sensitive=True),
              help='computer to run non-test verification.')
@click.option('--test-mode', is_flag=True, default=False, # TODO: rename to `--no-cleanup`
              help='in test mode the remote folder will not being cleaned.')
@click.option('--property', multiple=True, default=[])
@click.argument('filename', type=click.Path(exists=True))
def run(profile, mode, filename, computer, property, test_mode):
    if not property:
        extra_desc = 'all_prop'
        if mode == "PRECHECK":
            properties_list = DEFAULT_CONVERGENCE_PROPERTIES_LIST
        else:
            properties_list = DEFAULT_PROPERTIES_LIST
    else:
        properties_list = list(property)
        extra_desc = f'{properties_list}'
        
    _profile = aiida.load_profile(profile)
    click.echo(f'Profile: {_profile.name}')
    
    inputs = inputs_from_mode(mode=mode, computer_label=computer, properties_list=properties_list)
    if test_mode:
        inputs['clean_workchain'] = False
    else:
        inputs['clean_workchain'] = True
    
    basename = os.path.basename(filename)
    label, _ = os.path.splitext(basename)
    label = orm.Str(f'({mode}-{computer}) {label}')

    with open(filename, "rb") as stream:
        pseudo = UpfData(stream)
        
    node = run_verification(
        **inputs, 
        **{
            'pseudo': pseudo,
            'label': label,
            'extra_desc': extra_desc,
        }, 
    )

    click.echo(node)
    click.echo(f"calculated on property: {'/'.join(properties_list)}")


if __name__ == '__main__':
    run()