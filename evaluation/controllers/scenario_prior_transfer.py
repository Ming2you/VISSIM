"""Explicit experimental reuse of historical priors on a changed network.

Training artifacts remain byte-identical and retain their original network.
This declaration never certifies their predictive accuracy on the new scenario.
All callers must still perform their physical path/head/clock validations.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def read(pin):
    path=ROOT/pin['path']
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=pin['sha256']:
        raise ValueError('Historical prior transfer source changed: '+str(path))
    return data


def training_network(document,prior_pin):
    transfer=document.get('historical_prior_transfer')
    if transfer is None:return document['network']
    record=json.loads(read(transfer))
    if (record.get('schema')!='experimental-network-prior-transfer/v1'
            or record.get('predictive_accuracy_validated') is not False
            or document['network']!=record['target_network']
            or {k:prior_pin[k] for k in ('path','sha256')} not in record['unchanged_prior_files']):
        raise ValueError('Historical prior lacks explicit scenario/source declaration')
    read(record['source_network']);read(record['target_network']);read(prior_pin)
    return record['source_network']
