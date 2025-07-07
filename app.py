import streamlit as st
import pandas as pd
from anytree import Node, RenderTree, PreOrderIter

st.title("Migration Scope Entscheidung")

# CSV Upload
uploaded_file = st.file_uploader("Lade die CSV-Datei hoch", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Strukturaufbau
    st.subheader("Hierarchie")
    nodes = {}
    for _, row in df.iterrows():
        tid = row["TenantId"]
        pid = row["ParentId"]
        label = f"{row['DisplayName']} ({tid})"
        if pd.isna(pid):
            nodes[tid] = Node(label)
        else:
            parent_node = nodes.get(pid)
            if parent_node:
                nodes[tid] = Node(label, parent=parent_node)
            else:
                nodes[tid] = Node(label)  # später verwaiste behandeln

    # Visualisierung
    for node in PreOrderIter(list(nodes.values())[0]):
        indent = " " * node.depth
        st.write(f"{indent}🔹 {node.name}")

    # Entscheidung
    st.subheader("Scope-Festlegung")
    scope_results = []
    for node in PreOrderIter(list(nodes.values())[0]):
        indent = " " * node.depth
        scope = st.radio(f"{indent}{node.name}", ["In Scope", "Out of Scope"], horizontal=True, key=node.name)
        scope_results.append({
            "TenantId": node.name.split("(")[-1].rstrip(")"),
            "DisplayName": node.name.split("(")[0].strip(),
            "Scope": scope
        })

    # Download
    if st.button("CSV mit Scope-Entscheidung exportieren"):
        result_df = pd.DataFrame(scope_results)
        st.download_button("Herunterladen", result_df.to_csv(index=False), file_name="scope_entscheidung.csv")
