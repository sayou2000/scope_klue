import streamlit as st
import pandas as pd
import io

# Set page layout to wide for better table display
st.set_page_config(layout="wide")

st.title("Datenmigration: Interaktive Objektauswahl 🗂️")
st.info(
    "Laden Sie Ihre CSV-Datei hoch, um die Objekthierarchie interaktiv zu bearbeiten. "
    "Die Datei muss die Spalten 'Id', 'ParentId' und 'DisplayName' enthalten."
)

# --- Core Logic Function ---
# This function recursively builds the hierarchical structure.
# Using @st.cache_data makes it run only once if the input data doesn't change,
# which speeds up the app significantly.
@st.cache_data
def build_hierarchical_df(df):
    """
    Transforms a flat dataframe with Id/ParentId into a hierarchical one
    with indentation for display.
    """
    # Create a dictionary for quick lookups of display names
    name_dict = df.set_index('Id')['DisplayName'].to_dict()
    # Create a dictionary to hold parent-child relationships
    child_dict = df.groupby('ParentId')['Id'].apply(list).to_dict()

    # This list will hold the final, ordered data
    hierarchical_rows = []

    def find_children(parent_id, level):
        """Recursive inner function to traverse the tree."""
        if parent_id not in child_dict:
            return # No children, end of branch

        for child_id in child_dict[parent_id]:
            # Indent the display name based on its level in the hierarchy
            indentation = "· · " * level
            display_name_indented = f"{indentation}{name_dict.get(child_id, 'N/A')}"

            hierarchical_rows.append({
                'Id': child_id,
                'ParentId': parent_id,
                'DisplayName_Indented': display_name_indented,
                'Original_DisplayName': name_dict.get(child_id, 'N/A')
            })
            # --- RECURSION ---
            # Call the function for the next level
            find_children(child_id, level + 1)

    # Start the process from the root nodes (those with ParentId = 0 or a ParentId not present in the Id column)
    root_ids = df[~df['ParentId'].isin(df['Id'])]['Id'].tolist()
    # It's common to use 0 as the root identifier, so we add it if it exists.
    if 0 in child_dict and 0 not in root_ids:
       root_ids.extend(child_dict[0])

    for root_id in sorted(list(set(root_ids))):
         hierarchical_rows.append({
            'Id': root_id,
            'ParentId': 0, # Assuming root
            'DisplayName_Indented': name_dict.get(root_id, 'N/A'),
            'Original_DisplayName': name_dict.get(root_id, 'N/A')
         })
         find_children(root_id, level=1)
    
    # Create the final DataFrame to be displayed
    final_df = pd.DataFrame(hierarchical_rows)
    final_df['In Scope'] = True # Add the interactive checkbox column, default to True
    return final_df


# --- Streamlit UI ---
uploaded_file = st.file_uploader("Wählen Sie Ihre CSV-Exportdatei", type="csv")

if uploaded_file is not None:
    try:
        # Load the raw data
        raw_df = pd.read_csv(uploaded_file, sep=";", quotechar='"', encoding="utf-8")
       
        # Check for required columns
        required_columns = ['Id', 'ParentId', 'DisplayName']
        if not all(col in raw_df.columns for col in required_columns):
            st.error(f"Fehler: Die CSV-Datei muss die Spalten {required_columns} enthalten.")
        else:
            # --- Session State Initialization ---
            # We use session state to keep track of the data across reruns
            if 'df_hierarchical' not in st.session_state:
                st.session_state.df_hierarchical = build_hierarchical_df(raw_df)

            st.subheader("Hierarchische Ansicht der Objekte")
            st.write("Entfernen Sie den Haken bei 'In Scope', um ein Objekt von der Migration auszuschließen.")
            
            # --- Interactive Data Editor ---
            # This is the core interactive element where the user makes selections.
            edited_df = st.data_editor(
                st.session_state.df_hierarchical,
                column_config={
                    "In Scope": st.column_config.CheckboxColumn(
                        "In Scope?",
                        default=True,
                    ),
                    "DisplayName_Indented": st.column_config.TextColumn(
                        "Objekt-Hierarchie",
                        disabled=True
                    )
                },
                # Disable editing for data columns
                disabled=['Id', 'ParentId', 'Original_DisplayName'],
                hide_index=True,
                key='data_editor' # Add a key to preserve state
            )

            # --- Export Functionality ---
            st.subheader("Export")
            
            # Filter the dataframe based on the user's selections in the data_editor
            in_scope_df = edited_df[edited_df['In Scope']]
            
            # Prepare data for download
            export_ids = in_scope_df[['Id']]
            
            # Use an in-memory buffer to create the CSV file
            csv_buffer = io.StringIO()
            export_ids.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            st.write(f"**{len(export_ids)}** von **{len(raw_df)}** Objekten sind als 'In Scope' ausgewählt.")
            
            st.download_button(
                label="✅ In-Scope IDs als CSV herunterladen",
                data=csv_buffer.getvalue(),
                file_name="in_scope_ids.csv",
                mime="text/csv",
            )
    
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")

else:
    st.warning("Bitte laden Sie eine CSV-Datei hoch, um zu beginnen.")
