"""Explicita os intervalos já registrados do controle, sem recalcular resultados."""
from pathlib import Path
import argparse, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt = lambda v, n=2: f'{v:.{n}f}'.replace('.', ',')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-source', type=Path, required=True)
    a = p.parse_args()
    base = ROOT/'artigo/historico/ARTIGO_ANTES_INCERTEZA_2026-11-08.md'
    assert sha(base) == 'f80eaa85d5e22d97898d7d6b641833e77ebc05eedb6e1dd58889f6809b01d2be'
    audit_file = ROOT/'outputs/defesa_consolidada_final_2026-11-08/AUDITORIA_DEFESA.json'
    audit = json.loads(audit_file.read_text())
    assert audit['status'] == 'verified' and len(audit['conditions']) == 13
    assert audit['intervals_reused_without_recalculation'] and not audit['new_model_selection']
    ci = audit['conditions']['original_0']['interval95_cluster_person_percent']
    ranges = [f"{fmt(ci[k][0],n)}% a {fmt(ci[k][1],n)}%" for k,n in
              (('rank1',2),('tar',2),('fmr',3))]
    replacement = (f'Os intervalos descritivos de 95% do controle foram {ranges[0]} para Rank-1, '
        f'{ranges[1]} para TAR e {ranges[2]} para FMR. A aprovação pontual não constitui garantia populacional. '
        'As fronteiras históricas de 99,5% e 99% pertencem a outra grade; não se interpolaram níveis ausentes. '
        'Referências vazias permaneceram nos denominadores, com área indefinida.')
    text = base.read_text(encoding='utf-8')
    blocks = text.split('\n\n')
    indices = [i for i,b in enumerate(blocks) if b.startswith('O refinamento histórico encontrou 99,5%')]
    assert len(indices) == 1
    old = blocks[indices[0]]
    blocks[indices[0]] = replacement
    result = '\n\n'.join(blocks)
    assert result.count('<!-- pagina:') == text.count('<!-- pagina:') == 30
    a.output_source.parent.mkdir(parents=True, exist_ok=True)
    a.output_source.write_text(result, encoding='utf-8')
    metadata = {'base_sha256':sha(base), 'output_source_sha256':sha(a.output_source),
        'evidence_sha256':sha(audit_file), 'helper_sha256':sha(__file__),
        'word_delta':len(replacement.split())-len(old.split()),
        'recognition_and_clinical_counts_unchanged':True,
        'existing_intervals_made_explicit':True, 'new_threshold_or_model_selection':False}
    (a.output_source.parent/'PROVENIENCIA_INCERTEZA.json').write_text(
        json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
