"""
VERSION DARK MODE - À intégrer dans load_css()
Remplacez le contenu de la fonction load_css() dans app.py par ce code
pour obtenir un thème sombre moderne
"""

def load_css_dark():
    """Charge le CSS personnalisé pour un design moderne en mode sombre"""
    css = """
    <style>
    /* VARIABLES DE COULEURS - Mode Sombre */
    :root {
        --primary-color: #818cf8;
        --primary-hover: #6366f1;
        --secondary-color: #f472b6;
        --background-gradient-start: #0f172a;
        --background-gradient-end: #1e293b;
        --card-background: #1e293b;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --border-color: #334155;
        --shadow-color: rgba(129, 140, 248, 0.2);
        --success-color: #34d399;
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
        text-shadow: 0 0 20px rgba(129, 140, 248, 0.5);
        animation: fadeInDown 0.8s ease-out, glow 2s ease-in-out infinite;
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
        color: var(--text-primary) !important;
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
        box-shadow: 0 4px 12px var(--shadow-color), 0 0 20px rgba(129, 140, 248, 0.3) !important;
        transform: translateY(-2px);
    }

    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2) !important;
    }

    /* LABELS */
    label {
        color: var(--text-secondary) !important;
    }

    /* CHECKBOXES */
    .stCheckbox > label {
        background-color: var(--card-background) !important;
        color: var(--text-primary) !important;
        padding: 0.75rem 1rem !important;
        border-radius: 10px !important;
        border: 2px solid var(--border-color) !important;
        transition: all 0.3s ease !important;
    }

    .stCheckbox > label:hover {
        border-color: var(--primary-color) !important;
        background-color: rgba(129, 140, 248, 0.1) !important;
        box-shadow: 0 0 15px rgba(129, 140, 248, 0.3) !important;
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
        box-shadow: 0 4px 15px rgba(129, 140, 248, 0.4), 0 0 30px rgba(129, 140, 248, 0.2) !important;
    }

    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(129, 140, 248, 0.5), 0 0 40px rgba(129, 140, 248, 0.3) !important;
    }

    /* BOUTON DOWNLOAD */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--success-color) 0%, #10b981 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(52, 211, 153, 0.4) !important;
    }

    .stDownloadButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(52, 211, 153, 0.5), 0 0 30px rgba(52, 211, 153, 0.3) !important;
    }

    /* METRICS */
    .stMetric {
        background: var(--card-background) !important;
        padding: 1.5rem !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 15px var(--shadow-color), 0 0 20px rgba(129, 140, 248, 0.1) !important;
        border: 2px solid var(--border-color) !important;
        transition: all 0.3s ease !important;
    }

    .stMetric:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 8px 25px var(--shadow-color), 0 0 30px rgba(129, 140, 248, 0.2) !important;
        border-color: var(--primary-color) !important;
    }

    .stMetric label {
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
    }

    .stMetric [data-testid="stMetricValue"] {
        color: var(--primary-color) !important;
        font-weight: 800 !important;
        font-size: 2rem !important;
        text-shadow: 0 0 10px rgba(129, 140, 248, 0.5);
    }

    /* ALERTS */
    .stSuccess {
        background: linear-gradient(135deg, rgba(52, 211, 153, 0.15) 0%, rgba(52, 211, 153, 0.25) 100%) !important;
        border-left: 4px solid var(--success-color) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
    }

    .stError {
        background: linear-gradient(135deg, rgba(248, 113, 113, 0.15) 0%, rgba(248, 113, 113, 0.25) 100%) !important;
        border-left: 4px solid #f87171 !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
    }

    .stWarning {
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.25) 100%) !important;
        border-left: 4px solid #fbbf24 !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
    }

    /* SÉPARATEURS */
    hr {
        margin: 2rem 0 !important;
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent) !important;
        opacity: 0.5 !important;
        box-shadow: 0 0 10px rgba(129, 140, 248, 0.5);
    }

    /* CONTENEUR DE CARTE */
    .card {
        background: var(--card-background);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px var(--shadow-color), 0 0 40px rgba(129, 140, 248, 0.1);
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }

    /* EXPANDER */
    .streamlit-expanderHeader {
        background-color: var(--card-background) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 10px !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 15px rgba(129, 140, 248, 0.3) !important;
    }

    /* SPINNER */
    .stSpinner > div {
        border-top-color: var(--primary-color) !important;
    }

    /* SCROLLBAR */
    ::-webkit-scrollbar {
        width: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--background-gradient-start);
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary-color), var(--secondary-color));
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-hover);
        box-shadow: 0 0 10px rgba(129, 140, 248, 0.5);
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

    @keyframes glow {
        0%, 100% {
            text-shadow: 0 0 20px rgba(129, 140, 248, 0.5);
        }
        50% {
            text-shadow: 0 0 30px rgba(129, 140, 248, 0.8), 0 0 40px rgba(129, 140, 248, 0.6);
        }
    }

    /* PARTICULES DE FOND (optionnel) */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(circle at 20% 50%, rgba(129, 140, 248, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(244, 114, 182, 0.1) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }

    /* RESPONSIVE */
    @media (max-width: 768px) {
        h1 {
            font-size: 2rem !important;
        }
        
        .card {
            padding: 1rem;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
