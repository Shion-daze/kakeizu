# visualize_tree.py (属性名修正版)

import json
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

# Macで日本語表示するためのフォント設定
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False 

class Person:
    def __init__(self, id, name, gender=None, birth_date=None, death_date=None, **kwargs):
        self.id = id
        self.name = name
        self.gender = gender
        self.birth_date = birth_date
        self.death_date = death_date

# ▼▼▼▼▼ 属性名を source, target, type に統一 ▼▼▼▼▼
class Relationship:
    def __init__(self, source, target, type):
        self.source = source
        self.target = target
        self.type = type
# ▲▲▲▲▲ ここまでを修正 ▲▲▲▲▲

class FamilyTree:
    def __init__(self):
        self.persons = {}
        self.relationships = []
    
    def add_person(self, person):
        self.persons[person.id] = person
        
    def add_relationship(self, relationship):
        self.relationships.append(relationship)

class FamilyTreeVisualizer:
    def __init__(self, family_tree):
        self.family_tree = family_tree
        self.graph = self._to_networkx_graph()

    def _to_networkx_graph(self):
        G = nx.DiGraph()
        for id, person in self.family_tree.persons.items():
            label = f"{person.name}\n{person.birth_date or ''}"
            if person.death_date:
                label += f"\n- {person.death_date}"
            G.add_node(person.id, label=label, gender=person.gender)
        
        for rel in self.family_tree.relationships:
            # ▼▼▼▼▼ 属性名を source, target に統一 ▼▼▼▼▼
            if rel.source in G and rel.target in G:
                G.add_edge(rel.source, rel.target, type=rel.type)
            # ▲▲▲▲▲ ここまでを修正 ▲▲▲▲▲
        return G

    def visualize_basic(self, figsize=(32, 24)):
        plt.figure(figsize=figsize)
        pos = self._hierarchical_layout()
        
        node_colors = []
        for n in self.graph.nodes():
            gender = self.graph.nodes[n].get('gender')
            if gender == 'M':
                node_colors.append('lightblue')
            elif gender == 'F':
                node_colors.append('lightpink')
            else:
                node_colors.append('lightgray')
        
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=4000, alpha=0.9)
        
        parent_child_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get('type') in ['parent_child', 'adopted']]
        spouse_edges = [(u, v) for u, v, d in self.graph.edges(data=True) if d.get('type') == 'spouse']
        
        nx.draw_networkx_edges(self.graph, pos, edgelist=parent_child_edges, arrows=True, edge_color='gray', width=1.5, node_size=4000)
        nx.draw_networkx_edges(self.graph, pos, edgelist=spouse_edges, style='dashed', arrows=False, edge_color='red')
        
        labels = nx.get_node_attributes(self.graph, 'label')
        nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=9, font_family='AppleGothic')
        
        plt.title("Generated Family Tree", fontsize=20)
        plt.axis('off')
        return plt.gcf()

    def _hierarchical_layout(self):
        if not self.family_tree.persons: return {}
        # ▼▼▼▼▼ 属性名を target, type に統一 ▼▼▼▼▼
        children_ids = {rel.target for rel in self.family_tree.relationships if rel.type in ['parent_child', 'adopted']}
        # ▲▲▲▲▲ ここまでを修正 ▲▲▲▲▲
        all_person_ids = set(self.family_tree.persons.keys())
        roots = list(all_person_ids - children_ids)
        if not roots: roots = [list(all_person_ids)[0]] if all_person_ids else []
        
        levels = defaultdict(list)
        visited = set()

        def assign_level(p_id, level):
            if p_id in visited: return
            visited.add(p_id)
            levels[level].append(p_id)
            
            # ▼▼▼▼▼ 属性名を source, target, type に統一 ▼▼▼▼▼
            spouses = [rel.target for rel in self.family_tree.relationships if rel.source == p_id and rel.type == 'spouse'] + \
                      [rel.source for rel in self.family_tree.relationships if rel.target == p_id and rel.type == 'spouse']
            for sp_id in spouses:
                if sp_id not in visited:
                    assign_level(sp_id, level)

            children = [rel.target for rel in self.family_tree.relationships if rel.source == p_id and rel.type in ['parent_child', 'adopted']]
            for ch_id in children:
                assign_level(ch_id, level + 1)
            # ▲▲▲▲▲ ここまでを修正 ▲▲▲▲▲
        
        for root_id in roots:
            assign_level(root_id, 0)
            
        pos = {}
        for level, nodes in levels.items():
            y = -level
            width = len(nodes)
            for i, node_id in enumerate(nodes):
                x = i - (width - 1) / 2.0
                pos[node_id] = (x, y)
                
        return pos

def build_tree_from_json(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{json_path}' が見つかりません。先に run_analysis.py と run_synthesis.py を実行してください。")
        return None

    tree = FamilyTree()
    for person_data in data.get("persons", []):
        tree.add_person(Person(**person_data))
    for rel_data in data.get("relationships", []):
        # ▼▼▼▼▼ 属性名を source, target, type に統一 ▼▼▼▼▼
        if rel_data.get("source") and rel_data.get("target"):
            tree.add_relationship(Relationship(rel_data.get("source"), rel_data.get("target"), rel_data.get("type")))
    return tree
    # ▲▲▲▲▲ ここまでを修正 ▲▲▲▲▲

if __name__ == "__main__":
    json_file = "output/family_tree_merged.json"
    output_image = "output/family_tree_network.png"
    
    print(f"'{json_file}' から家系図データを読み込んでいます...")
    family_tree = build_tree_from_json(json_file)
    
    if family_tree and family_tree.persons:
        print("家系図データの構築が完了しました。描画を開始します...")
        visualizer = FamilyTreeVisualizer(family_tree)
        figure = visualizer.visualize_basic()
        figure.savefig(output_image, bbox_inches='tight', dpi=200)
        print(f"✅ 成功！ 家系図を '{output_image}' に保存しました。")
    elif family_tree:
        print("家系図に人物データがありません。")
    else:
        print("家系図の構築に失敗しました。")