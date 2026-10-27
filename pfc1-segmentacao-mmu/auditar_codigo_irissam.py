"""Inspecao AST do repositorio externo; nao importa nem executa seus scripts."""
from pathlib import Path
import argparse,ast,json
from preparar_encoder_espacial import file_hash
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=ROOT.parent.parent/'Segmentadores de Terceiros/Iris-SAM-main';files={}
    for name in ['dataset.py','sam_infer.py','sam_infer_auto.py','sam_test.py','sam_train_losses.py','utils/common.py']:
        tree=ast.parse((repo/name).read_text(encoding='utf-8'));calls=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ['draw_box_points','get_bounding_box','train']:
                calls.append(dict(line=node.lineno,function=node.func.id,arguments=[ast.unparse(v) for v in node.args]))
        cuda2=[node.lineno for node in ast.walk(tree) if isinstance(node,ast.Constant) and node.value=='cuda:2']
        top_training_loops=[node.lineno for node in tree.body if isinstance(node,ast.For) and any(isinstance(v,ast.Call) and isinstance(v.func,ast.Name) and v.func.id=='train' for v in ast.walk(node))]
        files[name]=dict(sha256=file_hash(repo/name),relevant_calls=calls,cuda2_lines=cuda2,module_level_training_loops=top_training_loops)
    placeholders=[]
    for file in (repo/'data').rglob('*'):
        if file.is_file() and file.suffix.lower() in ['.jpg','.png'] and file.stat().st_size<100:placeholders.append(dict(file=file.relative_to(repo).as_posix(),bytes=file.stat().st_size))
    findings=dict(external_scripts_executed=False,source=files,non_image_placeholders=placeholders,standard_LICENSE_files=[f.name for f in repo.iterdir() if f.is_file() and f.name.lower().startswith(('license','licence'))],interpretation=dict(automatic_script_still_calls_interactive_box=bool(files['sam_infer_auto.py']['relevant_calls']),test_dataset_box_comes_from_reference=any(c['function']=='get_bounding_box' and 'ground_truth_mask' in c['arguments'] for c in files['dataset.py']['relevant_calls']),train_module_has_unconditional_training_loop=bool(files['sam_train_losses.py']['module_level_training_loops'])))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(findings,indent=2),encoding='utf-8');print(json.dumps(dict(interpretation=findings['interpretation'],placeholder_files=len(placeholders),license_files=findings['standard_LICENSE_files']),indent=2))
if __name__=='__main__':main()
