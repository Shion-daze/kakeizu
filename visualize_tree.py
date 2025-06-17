# visualize_tree.py (最終版)

import json
import networkx as nx
import matplotlib.pyplot as plt

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

class Relationship:
    def __init__(self, person1_id, person2_id, rel_type):
        self.person1_id = person1_id
        self.person2_id = person2_id
        self.rel_type = rel_type

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
            G.add_node(id, label=label, gender=person.gender)
        
        for rel in self.family_tree.relationships:
            if rel.person1_id in G and rel.person2_id in G:
                G.add_edge(rel.person1_id, rel.person2_id, type=rel.rel_type)
        return G

    def visualize_basic(self, figsize=(32, 24)):
        plt.figure(figsize=figsize)
        pos = self._hierarchical_layout()
        
        node_colors = ['lightblue' if self.graph.nodes[n].get('gender') == 'M' else 'lightpink' for n in self.graph.nodes()]
        
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
        
        children_ids = {rel.person2_id for rel in self.family_tree.relationships if rel.rel_type in ['parent_child', 'adopted']}
        all_person_ids = set(self.family_tree.persons.keys())
        roots = list(all_person_ids - children_ids)
        if not roots: roots = [list(all_person_ids)[0]] if all_person_ids else []

        generations = {}
        visited = set()
        for root_id in roots:
            if root_id in visited: continue
            generations[root_id] = 0
            queue = [(root_id, 0)]
            visited.add(root_id)
            while queue:
                person_id, gen = queue.pop(0)
                spouses = [p for rel in self.family_tree.relationships if rel.rel_type == 'spouse' for p in (rel.person1_id, rel.person2_id) if p != person_id and (rel.person1_id == person_id or rel.person2_id == person_id)]
                for spouse_id in spouses:
                    if spouse_id not in generations: generations[spouse_id] = gen
                    if spouse_id not in visited: visited.add(spouse_id); queue.append((spouse_id, gen))
                children = [rel.person2_id for rel in self.family_tree.relationships if rel.person1_id == person_id and rel.rel_type in ['parent_child', 'adopted']]
                for child_id in children:
                    if child_id not in generations: generations[child_id] = gen + 1
                    if child_id not in visited: visited.add(child_id); queue.append((child_id, gen + 1))
        
        pos = {}
        nodes_by_gen = {}
        for node, gen in generations.items():
            nodes_by_gen.setdefault(gen, []).append(node)
        
        y_coord = 0
        for gen in sorted(nodes_by_gen.keys()):
            nodes = nodes_by_gen[gen]
            x_coords = [i - (len(nodes) - 1) / 2.0 for i in range(len(nodes))]
            for node_id, x in zip(nodes, x_coords):
                pos[node_id] = (x * 2.0, -y_coord)
            y_coord += 1
        return pos

def build_tree_from_json(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{json_path}' が見つかりません。先に main.py を実行してください。")
        return None

    tree = FamilyTree()
    for person_data in data.get("persons", []):
        tree.add_person(Person(**person_data))
    for rel_data in data.get("relationships", []):
        if rel_data.get("source") and rel_data.get("target"):
            tree.add_relationship(Relationship(rel_data.get("source"), rel_data.get("target"), rel_data.get("type")))
    return tree

if __name__ == "__main__":
    json_file = "output/family_tree_merged.json"
    output_image = "output/family_tree.png"
    
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