"""Readable JSON export; tuple-keyed evidence remains explicitly represented."""
import numpy as np


def json_records(value):
    from src.models.state import ControlAction
    if isinstance(value,np.ndarray):return json_records(value.tolist())
    if isinstance(value,np.generic):return json_records(value.item())
    if isinstance(value,ControlAction):return json_records(vars(value))
    if isinstance(value,dict):
        if all(isinstance(k,(str,int,float,bool,type(None))) for k in value):
            return {k:json_records(v) for k,v in value.items()}
        return {'__tuple_keyed_mapping__':[[json_records(k),json_records(v)] for k,v in value.items()]}
    if isinstance(value,(list,tuple)):return [json_records(v) for v in value]
    if isinstance(value,(str,int,float,bool,type(None))):return value
    raise TypeError('Unsupported evidence type: '+type(value).__name__)
