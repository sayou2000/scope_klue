import streamlit as st
import pandas as pd
import io

# --- Page Config & Title ---
st.set_page_config(layout="wide")
st.title("Datenmigration: Interaktive Objektauswahl 🗂️")

# --- Helper function to get all descendant IDs ---
def get_all_children_ids(df, parent_id):
    """Findet rekursiv alle untergeordneten IDs für eine gegebene Parent-ID."""
    all_children = []
    direct_children = df[df['ParentId'] == parent_id]['Id'].tolist()
    if not direct_children:
        return []
    for child_id in direct_children:
        all_children.append(child_id)
        all_children.extend(get_all_children_ids(df, child_id))
    return all_children

# --- Core Logic Function (unverändert) ---
@st.cache_data
def build_hierarchical_df(_df):
    """Baut eine visuell klare Baumstruktur mit Emojis, sortiert auf jeder Ebene."""
    _df['DisplayName'] = _df['DisplayName'].astype(str)
    name_dict = _df.set_index('Id')['DisplayName'].to_dict()
    child_dict = _df.groupby('ParentId')['Id'].apply(list).to_dict()
    hierarchical_rows = []

    def find_children(parent_id, prefix=""):
        if parent_id not in child_dict: return
        children_to_sort = sorted([(name_dict.get(child_id, ""), child_id) for child_id in child_dict[parent_id]])
        num_children = len(children_to_sort)
        for i, (_, child_id) in enumerate(children_to_sort):
            is_last = (i == num_children - 1)
            connector = "┗━ " if is_last else "┣━ "
            display_name_indented = f"{prefix}{connector}{name_dict.get(child_id, 'N/A')}"
            hierarchical_rows.append({
                'Id': child_id, 'ParentId': parent_id,
                'DisplayName_Indented': display_name_indented,
                'Original_DisplayName': name_dict.get(child_id, 'N/A')
            })
            new_prefix = prefix + ("    " if is_last else "┃   ")
            find_children(child_id, prefix=new_prefix)

    root_ids = _df[~_df['ParentId'].isin(_df['Id'])]['Id'].tolist()
    if 0 in child_dict:
        root_ids.extend(child_id for child_id in child_dict[0] if child_id not in root_ids)
    sorted_roots = sorted([(name_dict.get(root_id, ""), root_id) for root_id in set(root_ids)])

    for _, root_id in sorted_roots:
        hierarchical_rows.append({
            'Id': root_id, 'ParentId': 0,
            'DisplayName_Indented': f"📁 {name_dict.get(root_id, 'N/A')}",
            'Original_DisplayName': name_dict.get(root_id, 'N/A')
        })
        find_children(root_id, prefix="")

    final_df = pd.DataFrame(hierarchical_rows)
    if not final_df.empty:
        final_df['In Scope'] = True
    return final_df

# --- Streamlit UI ---
uploaded_file = st.file_uploader("1. CSV-Exportdatei hochladen", type="csv")

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file, sep=';', quotechar='"', encoding="utf-8")
        required_columns = ['Id', 'ParentId', 'DisplayName']

        if not all(col in raw_df.columns for col in required_columns):
            st.error(f"Fehler: Die CSV-Datei muss die Spalten {required_columns} enthalten.")
        else:
            # Den vollständigen hierarchischen DataFrame einmalig erstellen und im Session State speichern
            if 'df_hierarchical' not in st.session_state:
                st.session_state.df_hierarchical = build_hierarchical_df(raw_df)

            # --- NEU: Auswahl des Startpunkts ---
            st.subheader("2. Startpunkt für die Analyse auswählen")
            
            # Finde alle Wurzel-Elemente (ParentId ist 0 oder nicht in der Id-Spalte vorhanden)
            root_df = raw_df[ (raw_df['ParentId'] == 0) | (~raw_df['ParentId'].isin(raw_df['Id'])) ].sort_values('DisplayName')
            root_options = {row['Id']: row['DisplayName'] for index, row in root_df.iterrows()}
            
            # Dropdown zur Auswahl des Startpunkts
            focus_selection = st.selectbox(
                "Bitte wählen Sie ein übergeordnetes Objekt aus, um dessen Hierarchie anzuzeigen:",
                options=list(root_options.keys()),
                format_func=lambda x: f"{root_options.get(x)} (ID: {x})"
            )

            st.divider()

            # --- Anzeige der gefilterten Hierarchie ---
            if focus_selection:
                st.subheader(f"3. Objekte für '{root_options.get(focus_selection)}' bearbeiten")
                st.write("Entfernen Sie den Haken bei 'In Scope', um ein Objekt von der Migration auszuschließen.")

                # Finde alle Kinder des ausgewählten Startpunkts
                ids_to_show = [focus_selection] + get_all_children_ids(raw_df, focus_selection)
                display_df = st.session_state.df_hierarchical[st.session_state.df_hierarchical['Id'].isin(ids_to_show)]

                edited_df = st.data_editor(
                    display_df,
                    column_config={"In Scope": st.column_config.CheckboxColumn("In Scope?", default=True)},
                    disabled=['Id', 'ParentId', 'Original_DisplayName', 'DisplayName_Indented'],
                    hide_index=True, key=f"data_editor_{focus_selection}" # Eindeutiger Key pro Auswahl
                )

                # --- Export-Logik ---
                st.divider()
                st.subheader("4. Export der Auswahl")
                
                # Aktualisiere den Haupt-DataFrame mit den Änderungen aus der gefilterten Ansicht
                st.session_state.df_hierarchical.update(edited_df)
                
                # Filtere den *gesamten* aktualisierten DataFrame für den Export
                in_scope_df = st.session_state.df_hierarchical[st.session_state.df_hierarchical['In Scope']]
                export_ids = in_scope_df[['Id']]

                st.write(f"**{len(export_ids)}** von **{len(raw_df)}** Objekten sind insgesamt als 'In Scope' ausgewählt.")
                st.download_button(
                    label="✅ Alle 'In-Scope' IDs als CSV herunterladen",
                    data=export_ids.to_csv(index=False).encode('utf-8'),
                    file_name="in_scope_ids.csv", mime="text/csv",
                )
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
