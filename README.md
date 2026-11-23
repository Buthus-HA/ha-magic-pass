# Magic Pass pour Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/Buthus-HA/ha-magic-pass/actions/workflows/validate.yaml/badge.svg)](https://github.com/Buthus-HA/ha-magic-pass/actions/workflows/validate.yaml)

*[English below](#english)*

Intégration **non officielle** qui affiche l'état des ~95 stations du [Magic Pass](https://www.magicpass.ch) (Suisse, France, Italie) dans Home Assistant, triées par temps de trajet depuis chez vous, avec la neige fraîche, la météo et une note sur 10.

## Fonctionnalités

- **Carte de tableau de bord incluse** (`custom:magic-pass-card`), sans ressource à ajouter à la main :
  tuiles « Domaines ouverts », « Meilleure < 2 h » et « Mise à jour », recherche par station, canton ou pays,
  filtre « Ouvertes seulement », tri sur chaque colonne, clic sur une ligne pour ouvrir la page de la station.
- Pour chaque station : temps de trajet en voiture, nombre de pistes, part de pistes vertes et bleues,
  statut et prochaine date d'ouverture, remontées et km ouverts, % ouvert, neige sur 72 h, météo du jour, note /10.
- **Capteurs** : stations ouvertes, stations ouvertes à proximité, meilleure station (avec sa note et son trajet), dernière mise à jour.
- **Un capteur par station** pour celles que vous choisissez dans les options (état `open` / `partial` / `closed` et tous les détails en attributs).
- **Événement** `magic_pass_station_opened` quand une station ouvre, pour vos automatisations.
- Traductions françaises, anglaises et allemandes.

## Installation

### HACS (recommandé)
1. HACS → menu ⋮ → **Dépôts personnalisés** → ajoutez `https://github.com/Buthus-HA/ha-magic-pass`, catégorie **Intégration**.
2. Installez **Magic Pass**, puis redémarrez Home Assistant.
3. **Paramètres → Appareils et services → Ajouter une intégration → Magic Pass**.

### Manuelle
Copiez `custom_components/magic_pass` dans le dossier `config/custom_components/` de Home Assistant, redémarrez, puis ajoutez l'intégration.

## Configuration

| Réglage | Par défaut | Rôle |
|---|---|---|
| Point de départ | position de la maison | Origine des temps de trajet |
| Temps de trajet maximal | 120 min | Limite pour « Meilleure station » et « Stations ouvertes à proximité » |
| Intervalle de mise à jour | 30 min | Fréquence de lecture de magicpass.ch (minimum 15 min) |
| Stations exposées comme capteurs | aucune | Options seulement : crée un capteur par station choisie |

## Carte

```yaml
type: custom:magic-pass-card
# options facultatives
title: Mes stations
only_open: false        # case « Ouvertes seulement » cochée au départ
only_favorites: false   # case « Favoris seulement » cochée au départ (affichée si favorites est renseigné)
hide_tiles: false
favorites:
  - Charmey
  - Moléson
```

Lecture des couleurs :
- **Statut** : pastille verte si la station est ouverte, rouge si elle est fermée (avec la date d'ouverture prévue).
- **Km ouverts** : rouge si la station est fermée ou si moins de 20 % du domaine est ouvert, orange entre 20 et 66 %, vert au-delà
  (calcul sur les km de pistes, ou sur les remontées si la station ne publie pas de km).

## Exemple d'automatisation

```yaml
triggers:
  - trigger: event
    event_type: magic_pass_station_opened
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.travel is not none and trigger.event.data.travel <= 90 }}"
actions:
  - action: notify.mobile_app_mon_telephone
    data:
      title: "⛷️ {{ trigger.event.data.name }} ouvre"
      message: "{{ trigger.event.data.lifts }} remontées, {{ trigger.event.data.travel }} min de route."
```

## Sources des données et limites

| Donnée | Source | Fréquence |
|---|---|---|
| Ouverture, remontées, km, dates | page publique [magicpass.ch/fr/stations/opening](https://www.magicpass.ch/fr/stations/opening) | à chaque mise à jour |
| Cantons / pays | filtres de la même page | 1×/semaine |
| Coordonnées, pistes, %V+B | carte publique [map.magicpass.ch](https://map.magicpass.ch) | 1×/semaine |
| Temps de trajet | serveur de démonstration [OSRM](https://project-osrm.org) (OpenStreetMap), sans trafic | 1×/14 jours ou si le point de départ change |
| Neige 72 h, météo | [Open-Meteo](https://open-meteo.com) (usage non commercial) | 1×/heure |

- Ce projet n'est **ni affilié ni approuvé par Magic Pass**. Il lit des pages publiques ; si le site change, l'intégration peut cesser de fonctionner jusqu'à une mise à jour.
- La neige et la météo sont calculées au point de la station sur la carte (souvent le village) : il tombe souvent davantage en altitude.
- Le nombre de pistes et le %V+B sont absents pour les stations peu détaillées sur la carte officielle.
- Si OSRM ne répond pas, les trajets sont estimés à vol d'oiseau (signalés par « ≈ »).
- Note /10 : 40 % ouverture, 30 % neige fraîche (20 cm = maximum), 20 % météo, 10 % trajet. Une station fermée vaut 0.

---

## English

**Unofficial** integration showing the ~95 [Magic Pass](https://www.magicpass.ch) resorts in Home Assistant, sorted by driving time from home, with fresh snow, weather and a score out of 10.

- Bundled dashboard card `custom:magic-pass-card` (no manual resource needed): search, "open only" filter, sortable columns.
- Sensors: open resorts, open resorts nearby, best resort (score, travel time), last update; optional one sensor per chosen resort.
- Event `magic_pass_station_opened` when a resort opens.
- Install through HACS as a custom repository (category *Integration*), restart, then add **Magic Pass** under *Settings → Devices & services*.
- Data: public magicpass.ch pages, the public Magic Pass map, the OSRM demo server (driving times, no traffic, cached 14 days) and Open-Meteo (non-commercial use, cached 1 hour). Not affiliated with or endorsed by Magic Pass.

## Licence

MIT
