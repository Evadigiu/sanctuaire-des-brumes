// ============================================================
// LE PLAN DU PARCOURS
// Fabrique automatiquement depuis le cahier de contenu.
// Ne pas modifier a la main : relancer fabriquer-les-pages.py.
// ============================================================
const PARCOURS = {
  "pages": {
    "E01": "8055/",
    "E02": "1965/",
    "E16": "8017/",
    "E03": "3215/",
    "E04": "3208/",
    "E05": "6120/",
    "E06": "8048/",
    "E07": "7157/",
    "E08": "1959/",
    "E09": "6116/",
    "E10": "8023/",
    "E11": "1871/",
    "E12": "1868/",
    "E13": "3182/",
    "E14": "3177/",
    "E15": "6025/"
  },
  "noms": {
    "E01": "LE COMMISSAIRE JEAN",
    "E02": "LA COLLÈGUE SOIGNEUSE",
    "E16": "Greg, version sens B",
    "E03": "SOPHIE, CHEFFE DE LA SÉCURITÉ",
    "E04": "L'ENCLOS DES LOUPS",
    "E05": "LA PASSANTE",
    "E06": "QUIZ ANIMALIER",
    "E07": "VÉTÉRINAIRE",
    "E08": "Indice : le panneau d'empreinte",
    "E09": "Greg, version sens A",
    "E10": "Bill",
    "E11": "Indice : Le sac du botaniste",
    "E12": "Appel du commissaire",
    "E13": "Bureau de Greg",
    "E14": "LE BOTANISTE",
    "E15": "La serre"
  },
  "ordre": {
    "A": {
      "E01": 1,
      "E02": 2,
      "E03": 3,
      "E04": 4,
      "E05": 5,
      "E06": 6,
      "E07": 7,
      "E08": 8,
      "E09": 9,
      "E10": 10,
      "E11": 11,
      "E12": 12,
      "E13": 13,
      "E14": 14,
      "E15": 15
    },
    "B": {
      "E01": 1,
      "E02": 8,
      "E03": 7,
      "E04": 9,
      "E05": 10,
      "E06": 11,
      "E07": 12,
      "E08": 13,
      "E10": 3,
      "E11": 4,
      "E12": 5,
      "E13": 6,
      "E14": 14,
      "E15": 15,
      "E16": 2
    }
  },
  "secours": {
    "8055": "E01",
    "1965": "E02",
    "8017": "E16",
    "3215": "E03",
    "3208": "E04",
    "6120": "E05",
    "8048": "E06",
    "7157": "E07",
    "1959": "E08",
    "6116": "E09",
    "8023": "E10",
    "1871": "E11",
    "1868": "E12",
    "3182": "E13",
    "3177": "E14",
    "6025": "E15"
  },
  "lisibles": {
    "E01": "le commissaire Jean",
    "E02": "la collègue soigneuse",
    "E16": "Greg",
    "E03": "Sophie, la cheffe de la sécurité",
    "E04": "l'enclos des loups",
    "E05": "la passante",
    "E06": "le quiz animalier",
    "E07": "le vétérinaire",
    "E08": "le panneau d'empreinte",
    "E09": "Greg",
    "E10": "Bill",
    "E11": "le sac du botaniste",
    "E12": "l'appel du commissaire",
    "E13": "le bureau de Greg",
    "E14": "le botaniste",
    "E15": "la serre"
  },
  "vers": {
    "A": {
      "E02": {
        "de": "E01",
        "texte": "Rendez-vous au bureau des soigneurs, à côté des ours polaires, pour interroger votre premier témoin."
      },
      "E03": {
        "de": "E02",
        "texte": "Rendez-vous à l'aire de pique-nique en face des ours polaires pour observer les caméras de surveillance du Parc."
      },
      "E04": {
        "de": "E03",
        "texte": "Rendez-vous au niveau du haut de l'enclos des loups pour la suite de l'enquête"
      },
      "E05": {
        "de": "E04",
        "texte": "Rendez-vous au fond de l'impasse, au-dessus de l'enclos des loups, pour interroger votre prochain témoin"
      },
      "E06": {
        "de": "E05",
        "texte": "Rendez-vous devant la panthère de l'amour pour un quiz animalier"
      },
      "E07": {
        "de": "E06",
        "texte": "Enfoncez-vous dans la forêt pour la suite de l'enquête"
      },
      "E08": {
        "de": "E07",
        "texte": "Tableau des empreintes"
      },
      "E09": {
        "de": "E08",
        "texte": "Rendez-vous au point GPS pour interroger votre prochain témoin."
      },
      "E10": {
        "de": "E09",
        "texte": "Traversez la grande volière pour rencontrer Bill."
      },
      "E11": {
        "de": "E10",
        "texte": "Avant d'aller vérifier le bureau de Greg, rendez-vous au point GPS"
      },
      "E12": {
        "de": "E11",
        "texte": "Suivez le chemin indiqué pour poursuivre l'enquête"
      },
      "E13": {
        "de": "E12",
        "texte": "Poursuivez jusqu'au bureau de Greg"
      },
      "E14": {
        "de": "E13",
        "texte": "Rendez-vous au Jardin des Iris."
      },
      "E15": {
        "de": "E14",
        "texte": "Pénétrez dans la serre"
      }
    },
    "B": {
      "E16": {
        "de": "E01",
        "texte": "Rendez-vous au repère sur la carte pour interroger votre premier témoin."
      },
      "E04": {
        "de": "E02",
        "texte": "Rendez-vous au niveau du haut de l'enclos des loups pour la suite de l'enquête"
      },
      "E10": {
        "de": "E16",
        "texte": "Traversez la grande volière pour rencontrer Bill."
      },
      "E02": {
        "de": "E03",
        "texte": "Rendez-vous au point GPS pour interroger votre prochain témoin."
      },
      "E05": {
        "de": "E04",
        "texte": "Rendez-vous au fond de l'impasse, au-dessus de l'enclos des loups, pour interroger votre prochain témoin"
      },
      "E06": {
        "de": "E05",
        "texte": "Rendez-vous devant la panthère de l'amour pour un quiz animalier"
      },
      "E07": {
        "de": "E06",
        "texte": "Enfoncez-vous dans la forêt pour la suite de l'enquête"
      },
      "E08": {
        "de": "E07",
        "texte": "Tableau des empreintes"
      },
      "E14": {
        "de": "E08",
        "texte": "Rendez-vous au Jardin des Iris."
      },
      "E11": {
        "de": "E10",
        "texte": "Avant d'aller vérifier le bureau de Greg, rendez-vous au point GPS"
      },
      "E12": {
        "de": "E11",
        "texte": "Suivez le chemin indiqué pour poursuivre l'enquête"
      },
      "E13": {
        "de": "E12",
        "texte": "Poursuivez jusqu'au bureau de Greg"
      },
      "E03": {
        "de": "E13",
        "texte": "Suivez le chemin indiqué pour aller interroger votre prochain témoin. Des indices se cachent sur la route."
      },
      "E15": {
        "de": "E14",
        "texte": "Pénétrez dans la serre"
      }
    }
  },
  "photos": {
    "E04": [
      "enclos-des-loups.webp",
      "Votre prochaine étape : l'enclos des loups"
    ]
  }
};
