# synthesize.py (最終版)

import os
import json
import glob
from collections import defaultdict

def synthesize_data(pages_dir: str, output_path: str):
    print("ページデータの統合処理を開始します...")
    page_data_map = {}
    for file_path in sorted(glob.glob(os.path.join(pages_dir, "page_*_data.json"))):
        page_num = int(os.path.basename(file_path).split('_')[1])
        with open(file_path, 'r', encoding='utf-8') as f:
            page_data_map[page_num] = json.load(f)

    all_persons_by_name = {}
    for page_num in sorted(page_data_map.keys()):
        for person_data in page_data_map[page_num].get("persons", []):
            name = person_data.get("name")
            if not name or len(name) < 2: continue
            
            # 名前の正規化（スペース除去）
            name = name.replace(" ", "").replace("　", "")
            person_data["name"] = name
            
            if name not in all_persons_by_name:
                all_persons_by_name[name] = person_data
            else:
                for key, value in person_data.items():
                    if value and (key not in all_persons_by_name[name] or not all_persons_by_name[name][key]):
                        all_persons_by_name[name][key] = value

    all_relationships = []
    for page_num in sorted(page_data_map.keys()):
        for rel_data in page_data_map[page_num].get("relationships", []):
            source = rel_data.get("source", "").replace(" ", "").replace("　", "")
            target = rel_data.get("target", "").replace(" ", "").replace("　", "")
            if source and target:
                all_relationships.append({"source": source, "target": target, "type": rel_data["type"]})

    final_persons = []
    person_name_to_id = {}
    current_id = 1
    for name, person_data in sorted(all_persons_by_name.items()):
        person_name_to_id[name] = current_id
        person_data['id'] = current_id
        final_persons.append(person_data)
        current_id += 1

    final_relationships, rel_set = [], set()
    for rel_data in all_relationships:
        source_name, target_name = rel_data.get("source"), rel_data.get("target")
        if source_name in person_name_to_id and target_name in person_name_to_id:
            source_id, target_id = person_name_to_id[source_name], person_name_to_id[target_name]
            rel_type = rel_data.get("type")
            
            rel_tuple = (rel_type, tuple(sorted((source_id, target_id)))) if rel_type == "spouse" else (rel_type, source_id, target_id)
            if rel_tuple not in rel_set:
                final_relationships.append({"source": source_id, "target": target_id, "type": rel_type})
                rel_set.add(rel_tuple)

    final_data = {"persons": final_persons, "relationships": final_relationships}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 統合完了！最終的なデータを '{output_path}' に保存しました。")

if __name__ == "__main__":
    synthesize_data("output/pages", "output/family_tree_merged.json")