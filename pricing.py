# -*- coding: utf-8 -*-
"""
Module de pricing adapté pour app.py
Compatible avec la structure existante + calcul de la vraie marge
"""

# ============================================================================
# CONSTANTES DE PRIX
# ============================================================================

# Prix de vente TTC
PRIX_TTC = {
    'coussins': {
        65: 35,
        80: 44,
        90: 48,
        'valise': 70,
        'auto': 0  # Calculé selon la taille optimale
    },
    'supports': {
        'banquette': 250,
        'banquette_angle': 250,
        'accoudoir': 225,
        'dossier': 250
    },
    'accessoires': {
        'coussin_deco': 15,
        'traversin': 30,
        'surmatelas': 80
    }
}

# Coefficients mousse TTC
COEF_MOUSSE_TTC = {
    'D25': 16 * 25,
    'D30': 16 * 30,
    'HR35': 16 * 37,
    'HR45': 16 * 47
}

# Prix tissu TTC
PRIX_TISSU_PETIT_TTC = 74   # Si largeur + épaisseur*2 <= 140cm
PRIX_TISSU_GRAND_TTC = 105  # Si largeur + épaisseur*2 > 140cm

# Coûts de revient HT (ce qu'on appelait "marge" avant)
COUT_REVIENT_HT = {
    'coussins': {
        65: 14,
        80: 17,
        90: 17.5,
        'valise': 25
    },
    'supports': {
        'banquette': 113,      # <= 200cm
        'banquette_long': 121,  # > 200cm
        'banquette_angle': 104.2,
        'accoudoir': 73,
        'dossier': 155.2,      # <= 200cm
        'dossier_long': 176    # > 200cm
    },
    'accessoires': {
        'coussin_deco': 9.5,
        'traversin': 11.6,
        'surmatelas': 31
    },
    'arrondis': 6.05
}

# Coefficients mousse coût HT
COEF_MOUSSE_COUT_HT = {
    'D25': 157.5,
    'D30': 188,
    'HR35': 192,
    'HR45': 245
}

# Prix tissu coût HT
PRIX_TISSU_PETIT_COUT_HT = 11.2
PRIX_TISSU_GRAND_COUT_HT = 16.16
SUPPLEMENT_TISSU_COUT_HT = 15

# ============================================================================
# FONCTIONS DE CALCUL
# ============================================================================

def calculer_prix_mousse_tissu_ttc(longueur, largeur, epaisseur, type_mousse):
    """Calcule le prix TTC mousse + tissu pour une banquette"""
    volume_m3 = (longueur * largeur * epaisseur) / 1000000
    coef = COEF_MOUSSE_TTC.get(type_mousse, COEF_MOUSSE_TTC['D25'])
    prix_mousse = volume_m3 * coef
    
    condition = largeur + (epaisseur * 2)
    if condition > 140:
        prix_tissu = (longueur / 100) * PRIX_TISSU_GRAND_TTC
    else:
        prix_tissu = (longueur / 100) * PRIX_TISSU_PETIT_TTC
    
    return prix_mousse + prix_tissu


def calculer_cout_mousse_tissu_ht(longueur, largeur, epaisseur, type_mousse):
    """Calcule le coût de revient HT mousse + tissu pour une banquette"""
    volume_m3 = (longueur * largeur * epaisseur) / 1000000
    coef = COEF_MOUSSE_COUT_HT.get(type_mousse, COEF_MOUSSE_COUT_HT['D25'])
    cout_mousse = volume_m3 * coef
    
    condition = 2 + largeur + (epaisseur * 2)
    if condition <= 140:
        cout_tissu = ((longueur / 100) * PRIX_TISSU_PETIT_COUT_HT) + SUPPLEMENT_TISSU_COUT_HT
    else:
        cout_tissu = ((longueur / 100) * PRIX_TISSU_GRAND_COUT_HT) + SUPPLEMENT_TISSU_COUT_HT
    
    return cout_mousse + cout_tissu


def estimer_nombre_banquettes(type_canape, tx, ty, tz):
    """Estime le nombre de banquettes selon le type de canapé"""
    if "Simple" in type_canape:
        return 1
    elif "L" in type_canape:
        return 2
    elif "U" in type_canape:
        return 3
    return 1


def estimer_nombre_coussins(type_canape, tx, ty, tz, profondeur, type_coussins):
    """Estime le nombre et la taille des coussins"""
    # Estimation basique - sera plus précise avec le wrapper canapefullv77
    if type_coussins == "auto":
        largeur_totale = tx
        if "L" in type_canape or "U" in type_canape:
            largeur_totale += (ty if ty else 0)
        if "U" in type_canape and tz:
            largeur_totale += tz
        
        # Estimation de la taille optimale
        if largeur_totale < 200:
            taille = 65
        elif largeur_totale < 350:
            taille = 80
        else:
            taille = 90
        
        nb_coussins = max(2, int(largeur_totale / taille))
        return nb_coussins, taille
    else:
        # Type fixe spécifié
        try:
            taille = int(type_coussins)
            nb_coussins = max(2, int(tx / taille))
            return nb_coussins, taille
        except:
            return 4, 80  # Valeur par défaut


def calculer_prix_total(type_canape, tx, ty, tz, profondeur,
                       type_coussins, type_mousse, epaisseur,
                       acc_left, acc_right, acc_bas,
                       dossier_left, dossier_bas, dossier_right,
                       nb_coussins_deco, nb_traversins_supp,
                       has_surmatelas, has_meridienne):
    """
    Calcule le prix total TTC et le coût de revient HT
    Compatible avec la structure de app.py
    
    Returns:
        dict avec tous les détails + la VRAIE marge
    """
    
    details = {}
    prix_ttc_total = 0
    cout_revient_ht_total = 0
    
    # ========================================================================
    # BANQUETTES (Mousse + Tissu + Support)
    # ========================================================================
    
    nb_banquettes = estimer_nombre_banquettes(type_canape, tx, ty, tz)
    
    # Estimation des dimensions des banquettes
    banquettes_dims = []
    if "Simple" in type_canape:
        banquettes_dims = [(tx, profondeur)]
    elif "L" in type_canape:
        banquettes_dims = [(tx, profondeur), (ty if ty else 150, profondeur)]
    elif "U" in type_canape:
        banquettes_dims = [
            (tx, profondeur),
            (ty if ty else 150, profondeur),
            (tz if tz else 150, profondeur)
        ]
    
    prix_banquettes_ttc = 0
    cout_banquettes_ht = 0
    
    for i, (longueur, largeur) in enumerate(banquettes_dims, 1):
        # Prix mousse + tissu TTC
        prix_mt = calculer_prix_mousse_tissu_ttc(longueur, largeur, epaisseur, type_mousse)
        prix_banquettes_ttc += prix_mt
        
        # Coût mousse + tissu HT
        cout_mt = calculer_cout_mousse_tissu_ht(longueur, largeur, epaisseur, type_mousse)
        cout_banquettes_ht += cout_mt
        
        # Support
        est_angle = ("Angle" in type_canape or "LF" in type_canape or "U2F" in type_canape) and i > 1
        if est_angle:
            prix_banquettes_ttc += PRIX_TTC['supports']['banquette_angle']
            cout_banquettes_ht += COUT_REVIENT_HT['supports']['banquette_angle']
        else:
            prix_banquettes_ttc += PRIX_TTC['supports']['banquette']
            if longueur <= 200:
                cout_banquettes_ht += COUT_REVIENT_HT['supports']['banquette']
            else:
                cout_banquettes_ht += COUT_REVIENT_HT['supports']['banquette_long']
    
    details['Banquettes (mousse + tissu + support)'] = round(prix_banquettes_ttc, 2)
    prix_ttc_total += prix_banquettes_ttc
    cout_revient_ht_total += cout_banquettes_ht
    
    # ========================================================================
    # DOSSIERS
    # ========================================================================
    
    nb_dossiers = 0
    if dossier_left:
        nb_dossiers += 1
    if dossier_bas:
        nb_dossiers += 1
    if dossier_right:
        nb_dossiers += 1
    
    prix_dossiers_ttc = nb_dossiers * PRIX_TTC['supports']['dossier']
    details['Dossiers'] = prix_dossiers_ttc
    prix_ttc_total += prix_dossiers_ttc
    
    # Coût dossiers HT (on prend la moyenne)
    cout_dossiers_ht = nb_dossiers * COUT_REVIENT_HT['supports']['dossier']
    cout_revient_ht_total += cout_dossiers_ht
    
    # ========================================================================
    # ACCOUDOIRS
    # ========================================================================
    
    nb_accoudoirs = 0
    if acc_left:
        nb_accoudoirs += 1
    if acc_right:
        nb_accoudoirs += 1
    if acc_bas:
        nb_accoudoirs += 1
    
    prix_accoudoirs_ttc = nb_accoudoirs * PRIX_TTC['supports']['accoudoir']
    details['Accoudoirs'] = prix_accoudoirs_ttc
    prix_ttc_total += prix_accoudoirs_ttc
    
    cout_accoudoirs_ht = nb_accoudoirs * COUT_REVIENT_HT['supports']['accoudoir']
    cout_revient_ht_total += cout_accoudoirs_ht
    
    # ========================================================================
    # COUSSINS
    # ========================================================================
    
    nb_coussins, taille_coussin = estimer_nombre_coussins(
        type_canape, tx, ty, tz, profondeur, type_coussins
    )
    
    # Ajustement si méridienne
    if has_meridienne:
        nb_coussins = max(1, nb_coussins - 1)
    
    prix_unitaire_coussin = PRIX_TTC['coussins'].get(taille_coussin, PRIX_TTC['coussins'][80])
    prix_coussins_ttc = nb_coussins * prix_unitaire_coussin
    details[f'Coussins {taille_coussin}cm (×{nb_coussins})'] = prix_coussins_ttc
    prix_ttc_total += prix_coussins_ttc
    
    cout_unitaire_coussin = COUT_REVIENT_HT['coussins'].get(taille_coussin, COUT_REVIENT_HT['coussins'][80])
    cout_coussins_ht = nb_coussins * cout_unitaire_coussin
    cout_revient_ht_total += cout_coussins_ht
    
    # ========================================================================
    # ACCESSOIRES
    # ========================================================================
    
    # Coussins déco
    if nb_coussins_deco > 0:
        prix_deco = nb_coussins_deco * PRIX_TTC['accessoires']['coussin_deco']
        details[f'Coussins déco (×{nb_coussins_deco})'] = prix_deco
        prix_ttc_total += prix_deco
        
        cout_deco = nb_coussins_deco * COUT_REVIENT_HT['accessoires']['coussin_deco']
        cout_revient_ht_total += cout_deco
    
    # Traversins
    if nb_traversins_supp > 0:
        prix_trav = nb_traversins_supp * PRIX_TTC['accessoires']['traversin']
        details[f'Traversins (×{nb_traversins_supp})'] = prix_trav
        prix_ttc_total += prix_trav
        
        cout_trav = nb_traversins_supp * COUT_REVIENT_HT['accessoires']['traversin']
        cout_revient_ht_total += cout_trav
    
    # Surmatelas
    if has_surmatelas:
        prix_surmat = PRIX_TTC['accessoires']['surmatelas']
        details['Surmatelas'] = prix_surmat
        prix_ttc_total += prix_surmat
        
        cout_surmat = COUT_REVIENT_HT['accessoires']['surmatelas']
        cout_revient_ht_total += cout_surmat
    
    # ========================================================================
    # ARRONDIS (coût uniquement)
    # ========================================================================
    
    cout_revient_ht_total += COUT_REVIENT_HT['arrondis']
    
    # ========================================================================
    # CALCULS FINAUX
    # ========================================================================
    
    # Sous-total et TVA
    sous_total = prix_ttc_total / 1.2
    tva = prix_ttc_total - sous_total
    
    # CALCUL DE LA VRAIE MARGE
    prix_ht = prix_ttc_total / 1.2
    marge_ht = prix_ht - cout_revient_ht_total
    taux_marge = (marge_ht / prix_ht * 100) if prix_ht > 0 else 0
    
    return {
        'details': details,
        'sous_total': round(sous_total, 2),
        'tva': round(tva, 2),
        'total_ttc': round(prix_ttc_total, 2),
        
        # NOUVEAUX champs pour la vraie marge
        'prix_ht': round(prix_ht, 2),
        'cout_revient_ht': round(cout_revient_ht_total, 2),
        'marge_ht': round(marge_ht, 2),
        'taux_marge': round(taux_marge, 1),
        
        # Informations complémentaires
        'nb_banquettes': nb_banquettes,
        'nb_dossiers': nb_dossiers,
        'nb_accoudoirs': nb_accoudoirs,
        'nb_coussins': nb_coussins,
        'taille_coussins': taille_coussin
    }


# ============================================================================
# CLASSE POUR COMPATIBILITÉ AVEC NOUVEAU CODE
# ============================================================================

class CanapePricing:
    """Classe de compatibilité pour le nouveau système"""
    
    def __init__(self):
        pass
    
    def calculer_devis_complet(self, configuration):
        """Méthode de compatibilité avec le nouveau système"""
        # Convertir la configuration en paramètres pour calculer_prix_total
        # Cette méthode sera utilisée si vous voulez migrer vers le nouveau système
        pass


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    # Test rapide
    resultat = calculer_prix_total(
        type_canape="Simple (S)",
        tx=280,
        ty=None,
        tz=None,
        profondeur=70,
        type_coussins="auto",
        type_mousse="D25",
        epaisseur=25,
        acc_left=True,
        acc_right=True,
        acc_bas=False,
        dossier_left=False,
        dossier_bas=True,
        dossier_right=False,
        nb_coussins_deco=2,
        nb_traversins_supp=0,
        has_surmatelas=False,
        has_meridienne=False
    )
    
    print("=" * 60)
    print("TEST DU MODULE PRICING")
    print("=" * 60)
    print(f"Prix TTC total      : {resultat['total_ttc']}€")
    print(f"Prix HT             : {resultat['prix_ht']}€")
    print(f"Coût de revient HT  : {resultat['cout_revient_ht']}€")
    print(f"MARGE HT            : {resultat['marge_ht']}€")
    print(f"Taux de marge       : {resultat['taux_marge']}%")
    print("\nDétails :")
    for item, prix in resultat['details'].items():
        print(f"  • {item}: {prix}€")

