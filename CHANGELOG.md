# Changelog

## 0.2.2 — 2026-11-23
- Événement `magic_pass_station_opened` : nouveaux champs `pedestrian` (ouverture piétons uniquement) et `kind`.
- L'événement est aussi émis quand une station ouverte aux piétons ouvre ses pistes.
- Capteurs par station : nouvel attribut `pedestrian_only`.

## 0.2.1 — 2026-11-23
- Icône de l'intégration (dossier `brand/`, affichée à partir de Home Assistant 2026.3).

## 0.2.0 — 2026-11-23
- Carte : case « Favoris seulement » (option `only_favorites`).
- Carte : pastille verte/rouge devant le statut d'ouverture.
- Carte : colonne « Km ouverts » colorée selon la part du domaine ouverte (rouge < 20 %, orange 20–66 %, vert > 66 %).
- La version n'est plus définie qu'à un seul endroit (`manifest.json`).

## 0.1.0
- Version initiale.
