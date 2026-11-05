"""Ponte para a inferencia congelada, preservando compatibilidade dos cadastros.

A implementacao e seus hashes continuam na pesquisa. UI/servidor podem mudar
sem alterar o identificador das caracteristicas ja cadastradas pelo usuario.
"""
import importlib.util
from pathlib import Path
import sys

RESEARCH_ROOT=Path(__file__).resolve().parents[2]/'pfc1-segmentacao-mmu'
sys.path.insert(0,str(RESEARCH_ROOT))
_source=RESEARCH_ROOT/'app_celular/motor.py'
_spec=importlib.util.spec_from_file_location('_pfc_frozen_mobile_engine',_source)
_engine=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_engine)
IrisEngine=_engine.IrisEngine
COMPONENTS=_engine.COMPONENTS
SCHEMA=_engine.SCHEMA
rank_candidates=_engine.rank_candidates
