"""
Application Streamlit pour générer des devis de canapés sur mesure
Version avec design moderne et amélioré
"""

import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# Import des modules personnalisés
from pricing import calculer_prix_total
from pdf_generator import generer_pdf_devis

# Import des fonctions de génération de schémas depuis canapematplot
from canapematplot import (
    render_LNF, render_LF_variant, render_U2f_variant,
    render_U, render_U1F_v1, render_U1F_v2, render_U1F_v3, render_U1F_v4,
    render_Simple1
)

# Configuration de la page
st.set_page_config(
    page_title="Générateur de Devis Canapés",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CHARGEMENT DU CSS PERSONNALISÉ
# ============================================
def load_css():
    """Charge le CSS personnalisé pour un design moderne"""
    css = """
    <style>
    /* VARIABLES DE COULEURS */
    :root {
        --primary-color: #6366f1;
        --primary-hover: #4f46e5;
        --secondary-color: #ec4899;
        --background-gradient-start: #f8fafc;
        --background-gradient-end: #e0e7ff;
        --card-background: #ffffff;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --border-color: #e2e8f0;
        --shadow-color: rgba(99, 102, 241, 0.1);
        --success-color: #10b981;
    }

    /* FOND GÉNÉRAL */
    .stApp {
        background: linear-gradient(135deg, var(--background-gradient-start) 0%, var(--background-gradient-end) 100%);
    }

    /* EN-TÊTE */
    h1 {
        color: var(--primary-color) !important;
        font-weight: 800 !important;
        font-size: 3rem !important;
        text-align: center !important;
        margin-bottom: 2rem !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        animation: fadeInDown 0.8s ease-out;
    }

    /* SOUS-TITRES */
    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }

    /* INPUTS */
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input {
        background-color: var(--card-background) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 1px 3px var(--shadow-color) !important;
    }

    .stSelectbox > div > div:hover,
    .stNumberInput > div > div > input:hover,
    .stTextInput > div > div > input:hover {
        border-color: var(--primary-color) !important;
        box-shadow: 0 4px 12px var(--shadow-color) !important;
        transform: translateY(-2px);
    }

    /* CHECKBOXES */
    .stCheckbox > label {
        background-color: var(--card-background) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 10px !important;
        border: 2px solid var(--border-color) !important;
        transition: all 0.3s ease !important;
    }

    .stCheckbox > label:hover {
        border-color: var(--primary-color) !important;
        background-color: rgba(99, 102, 241, 0.05) !important;
        transform: translateX(5px);
    }

    /* BOUTONS */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
    }

    /* BOUTON DOWNLOAD */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--success-color) 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
    }

    /* METRICS */
    .stMetric {
        background: var(--card-background) !important;
        padding: 1.5rem !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 15px var(--shadow-color) !important;
        border: 2px solid var(--border-color) !important;
        transition: all 0.3s ease !important;
    }

    .stMetric:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 8px 25px var(--shadow-color) !important;
    }

    /* ALERTS */
    .stSuccess {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.2) 100%) !important;
        border-left: 4px solid var(--success-color) !important;
        border-radius: 12px !important;
    }

    /* SÉPARATEURS */
    hr {
        margin: 2rem 0 !important;
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent) !important;
        opacity: 0.3 !important;
    }

    /* ANIMATIONS */
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* SCROLLBAR */
    ::-webkit-scrollbar {
        width: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--background-gradient-start);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 5px;
    }

    /* CONTENEUR DE CARTE */
    .card {
        background: var(--card-background);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px var(--shadow-color);
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Charger le CSS
load_css()

def generer_schema_canape(type_canape, tx, ty, tz, profondeur, 
                          acc_left, acc_right, acc_bas,
                          dossier_left, dossier_bas, dossier_right,
                          meridienne_side, meridienne_len, coussins="auto"):
    """
    Génère le schéma du canapé en utilisant les fonctions de canapematplot.py
    et retourne une figure matplotlib
    """
    fig = plt.figure(figsize=(12, 8))
    
    try:
        if "Simple" in type_canape:
            render_Simple1(
                tx=tx, profondeur=profondeur, dossier=dossier_bas,
                acc_left=acc_left, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, window_title="Canapé Simple"
            )
            
        elif "L - Sans Angle" in type_canape:
            render_LNF(
                tx=tx, ty=ty, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas,
                acc_left=acc_left, acc_bas=acc_bas,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, variant="auto",
                window_title="Canapé L - Sans Angle"
            )
            
        elif "L - Avec Angle" in type_canape:
            render_LF_variant(
                tx=tx, ty=ty, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas,
                acc_left=acc_left, acc_bas=acc_bas,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, window_title="Canapé L - Avec Angle"
            )
            
        elif "U - Sans Angle" in type_canape:
            render_U(
                tx=tx, ty_left=ty, tz_right=tz, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas,
                dossier_right=dossier_right, acc_left=acc_left,
                acc_bas=acc_bas, acc_right=acc_right,
                coussins=coussins, variant="auto",
                window_title="Canapé U - Sans Angle"
            )
            
        elif "U - 1 Angle" in type_canape:
            render_U1F_v1(
                tx=tx, ty=ty, tz=tz, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas,
                dossier_right=dossier_right, acc_left=acc_left,
                acc_right=acc_right, meridienne_side=meridienne_side,
                meridienne_len=meridienne_len, coussins=coussins,
                window_title="Canapé U - 1 Angle"
            )
            
        elif "U - 2 Angles" in type_canape:
            render_U2f_variant(
                tx=tx, ty_left=ty, tz_right=tz, profondeur=profondeur,
                dossier_left=dossier_left, dossier_bas=dossier_bas,
                dossier_right=dossier_right, acc_left=acc_left,
                acc_bas=acc_bas, acc_right=acc_right,
                meridienne_side=meridienne_side, meridienne_len=meridienne_len,
                coussins=coussins, window_title="Canapé U - 2 Angles"
            )
        
        fig = plt.gcf()
        return fig
        
    except Exception as e:
        plt.close()
        raise Exception(f"Erreur lors de la génération du schéma : {str(e)}")

# ============================================
# HEADER AVEC DESIGN MODERNE
# ============================================
st.markdown("""
<div style='text-align: center; padding: 2rem 0;'>
    <h1>🛋️ Générateur de Devis Canapés Sur Mesure</h1>
    <p style='color: #64748b; font-size: 1.2rem;'>Créez votre canapé personnalisé en quelques clics</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# LAYOUT PRINCIPAL
# ============================================
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 📋 Configuration du Canapé")
    
    # TYPE DE CANAPÉ avec emoji
    st.markdown("#### 🛋️ 1. Type de Canapé")
    type_canape = st.selectbox(
        "Sélectionnez le type",
        ["Simple (S)", "L - Sans Angle", "L - Avec Angle (LF)", 
         "U - Sans Angle", "U - 1 Angle (U1F)", "U - 2 Angles (U2F)"],
        help="Choisissez la forme du canapé"
    )
    
    # DIMENSIONS
    st.markdown("#### 📏 2. Dimensions (en cm)")
    
    if "Simple" in type_canape:
        tx = st.number_input("Largeur (Tx)", min_value=100, max_value=600, value=280, step=10)
        ty = tz = None
    elif "L" in type_canape:
        tx = st.number_input("Largeur bas (Tx)", min_value=100, max_value=600, value=350, step=10)
        ty = st.number_input("Hauteur gauche (Ty)", min_value=100, max_value=600, value=250, step=10)
        tz = None
    else:  # U
        tx = st.number_input("Largeur bas (Tx)", min_value=100, max_value=600, value=450, step=10)
        ty = st.number_input("Hauteur gauche (Ty)", min_value=100, max_value=600, value=300, step=10)
        tz = st.number_input("Hauteur droite (Tz)", min_value=100, max_value=600, value=280, step=10)
    
    profondeur = st.number_input("Profondeur", min_value=50, max_value=120, value=70, step=5)
    
    # ACCOUDOIRS
    st.markdown("#### 💪 3. Accoudoirs")
    col_acc1, col_acc2 = st.columns(2)
    with col_acc1:
        acc_left = st.checkbox("👈 Gauche", value=True)
    with col_acc2:
        acc_right = st.checkbox("👉 Droit", value=True)
    
    if "L" not in type_canape and "Simple" not in type_canape:
        acc_bas = st.checkbox("⬇️ Bas", value=True)
    else:
        acc_bas = st.checkbox("⬇️ Bas", value=True) if "L" in type_canape else False
    
    # DOSSIERS
    st.markdown("#### 🪑 4. Dossiers")
    dossier_left = st.checkbox("Dossier Gauche", value=True) if "Simple" not in type_canape else False
    dossier_bas = st.checkbox("Dossier Bas", value=True)
    dossier_right = st.checkbox("Dossier Droit", value=True) if ("U" in type_canape) else False
    
    # MÉRIDIENNE
    st.markdown("#### 🌙 5. Méridienne (optionnel)")
    has_meridienne = st.checkbox("Ajouter une méridienne")
    if has_meridienne:
        meridienne_options = ["Gauche (g)", "Droite (d)"]
        if "L" in type_canape or "U" in type_canape:
            meridienne_options.append("Bas (b)")
        
        meridienne_side = st.selectbox("Côté", meridienne_options)
        meridienne_len = st.number_input("Longueur (cm)", min_value=30, max_value=200, value=100, step=10)
        meridienne_side = meridienne_side[0].lower()
    else:
        meridienne_side = None
        meridienne_len = 0
    
    # COUSSINS
    st.markdown("#### 🛏️ 6. Coussins")
    type_coussins = st.selectbox(
        "Type de coussins",
        ["auto", "65", "80", "90", "valise", "p", "g"],
        help="Auto = optimisation automatique"
    )
    
    # MOUSSE ET TISSU
    st.markdown("#### 🧺 7. Mousse & Tissu")
    col_mousse1, col_mousse2 = st.columns(2)
    with col_mousse1:
        type_mousse = st.selectbox("Type", ["D25", "D30", "HR35", "HR45"])
    with col_mousse2:
        epaisseur = st.number_input("Épaisseur", min_value=15, max_value=35, value=25, step=5)
    
    # OPTIONS
    st.markdown("#### ✨ 8. Options")
    nb_coussins_deco = st.number_input("Coussins déco", min_value=0, max_value=10, value=0)
    nb_traversins_supp = st.number_input("Traversins", min_value=0, max_value=5, value=0)
    has_surmatelas = st.checkbox("Surmatelas")
    
    # CLIENT
    st.markdown("#### 👤 9. Informations Client")
    nom_client = st.text_input("Nom du client")
    email_client = st.text_input("Email (optionnel)")
    
    st.markdown("</div>", unsafe_allow_html=True)

# COLONNE DROITE - APERÇU
with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 👁️ Aperçu du Canapé")
    
    # Bouton de génération avec icône
    if st.button("🎨 Générer l'Aperçu", type="primary", use_container_width=True):
        with st.spinner("✨ Génération du schéma en cours..."):
            try:
                # Générer le schéma
                fig = generer_schema_canape(
                    type_canape=type_canape, tx=tx, ty=ty, tz=tz,
                    profondeur=profondeur, acc_left=acc_left,
                    acc_right=acc_right, acc_bas=acc_bas,
                    dossier_left=dossier_left, dossier_bas=dossier_bas,
                    dossier_right=dossier_right, meridienne_side=meridienne_side,
                    meridienne_len=meridienne_len, coussins=type_coussins
                )
                
                st.pyplot(fig)
                plt.close()
                
                st.success("✅ Schéma généré avec succès !")
                
                # Calcul du prix
                prix_details = calculer_prix_total(
                    type_canape=type_canape, tx=tx, ty=ty, tz=tz,
                    profondeur=profondeur, type_coussins=type_coussins,
                    type_mousse=type_mousse, epaisseur=epaisseur,
                    acc_left=acc_left, acc_right=acc_right, acc_bas=acc_bas,
                    dossier_left=dossier_left, dossier_bas=dossier_bas,
                    dossier_right=dossier_right, nb_coussins_deco=nb_coussins_deco,
                    nb_traversins_supp=nb_traversins_supp,
                    has_surmatelas=has_surmatelas, has_meridienne=has_meridienne
                )
                
                # Affichage des prix avec design amélioré
                st.markdown("### 📊 Détails du Devis")
                
                col_prix1, col_prix2, col_prix3 = st.columns(3)
                
                with col_prix1:
                    st.metric("💰 Sous-total", f"{prix_details['sous_total']}€")
                
                with col_prix2:
                    st.metric("📈 TVA (20%)", f"{prix_details['tva']}€")
                
                with col_prix3:
                    st.metric("💵 TOTAL TTC", f"{prix_details['total_ttc']}€")
                
                st.markdown("---")
                
                # Détails des composants
                with st.expander("📦 Voir les détails des composants"):
                    for item, prix in prix_details['details'].items():
                        st.write(f"• {item}: **{prix}€**")
                
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération : {str(e)}")
    
    # Bouton PDF
    st.markdown("---")
    if st.button("📄 Générer le Devis PDF", use_container_width=True):
        if not nom_client:
            st.warning("⚠️ Veuillez renseigner le nom du client")
        else:
            with st.spinner("📝 Création du PDF en cours..."):
                try:
                    # Régénérer le schéma pour le PDF
                    fig = generer_schema_canape(
                        type_canape=type_canape, tx=tx, ty=ty, tz=tz,
                        profondeur=profondeur, acc_left=acc_left,
                        acc_right=acc_right, acc_bas=acc_bas,
                        dossier_left=dossier_left, dossier_bas=dossier_bas,
                        dossier_right=dossier_right, meridienne_side=meridienne_side,
                        meridienne_len=meridienne_len, coussins=type_coussins
                    )
                    
                    # Sauvegarder dans un buffer
                    img_buffer = BytesIO()
                    fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
                    img_buffer.seek(0)
                    plt.close(fig)
                    
                    # Configuration
                    config = {
                        'type_canape': type_canape,
                        'dimensions': {'tx': tx, 'ty': ty, 'tz': tz, 'profondeur': profondeur},
                        'options': {
                            'acc_left': acc_left, 'acc_right': acc_right, 'acc_bas': acc_bas,
                            'dossier_left': dossier_left, 'dossier_bas': dossier_bas,
                            'dossier_right': dossier_right, 'meridienne_side': meridienne_side,
                            'meridienne_len': meridienne_len, 'type_coussins': type_coussins,
                            'type_mousse': type_mousse, 'epaisseur': epaisseur
                        },
                        'client': {'nom': nom_client, 'email': email_client}
                    }
                    
                    # Calcul prix
                    prix_details = calculer_prix_total(
                        type_canape=type_canape, tx=tx, ty=ty, tz=tz,
                        profondeur=profondeur, type_coussins=type_coussins,
                        type_mousse=type_mousse, epaisseur=epaisseur,
                        acc_left=acc_left, acc_right=acc_right, acc_bas=acc_bas,
                        dossier_left=dossier_left, dossier_bas=dossier_bas,
                        dossier_right=dossier_right, nb_coussins_deco=nb_coussins_deco,
                        nb_traversins_supp=nb_traversins_supp,
                        has_surmatelas=has_surmatelas, has_meridienne=has_meridienne
                    )
                    
                    # Génération PDF
                    pdf_buffer = generer_pdf_devis(config, prix_details, schema_image=img_buffer)
                    
                    st.download_button(
                        label="⬇️ Télécharger le Devis PDF",
                        data=pdf_buffer,
                        file_name=f"devis_canape_{nom_client.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                    
                    st.success("✅ PDF généré avec succès !")
                    
                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# FOOTER
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem; color: #64748b;'>
    <p style='font-size: 1.1rem; font-weight: 600;'>🛋️ Générateur de Devis Canapés Sur Mesure</p>
    <p style='font-size: 0.9rem;'>Version 3.0 - Design Moderne | Développé avec ❤️</p>
</div>
""", unsafe_allow_html=True)
