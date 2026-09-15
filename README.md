# Dead Reckoning

Un diorama naval interactif rendu en temps réel dans le navigateur : une bataille navale
repensée en table de commandement, sur une mer ouverte éclairée par un soleil rasant.

Tout est **généré au runtime**. Aucune texture, aucun modèle, aucun asset externe —
les coques, les voiles, l'eau, le ciel, la fumée et les ombres sont calculés au chargement
ou dans les shaders.

## Lancer

Le projet tient dans un seul fichier. Il suffit de l'ouvrir :

```bash
open index.html
```

Ou, si le navigateur bloque quelque chose en `file://` :

```bash
python3 -m http.server 4747
```

puis http://localhost:4747

## Les trois fichiers

| | |
|---|---|
| `index.html` | Le jeu. Un seul fichier, three.js depuis un CDN. Publié, c'est le jeu seul ; en local, c'est l'atelier avec tous les écrans (menu *Screens*). |
| `design-system.html` | Le langage de l'app — surfaces, encres, les deux camps, contrôles, mouvement. Toute valeur qui y figure est celle qui tourne. |
| `rules-of-engagement.html` | La logique de jeu v1 : chaque coque est une batterie, un tour en une touche, expliqué sur une partie jouée coup par coup. |

Les trois s'ouvrent directement dans un navigateur, sans build.

## Deux modes, un fichier

**Le jeu publié** — sur `battleship.erwanguillou.me` (ou en local avec `?prod`) :
Title → Deployment (contre la machine : difficulté, règles, théâtre) → Match → After action.
Pas de menu *Screens*, pas de *Debug*, pas de bouton de cadrage, pas de split sur
Deployment et After action. Les écrans Battle (bac à sable) et Capture ne sont pas
accessibles. En cas de panne (three.js qui ne charge pas, WebGL absent, erreur,
perte du contexte graphique), un message propose de recharger.

**L'atelier** — partout ailleurs, ou avec `?dev` sur le site publié : tous les écrans,
le bac à sable Battle, le tiroir Debug.

## Mise en ligne

Le site est servi par **GitHub Pages** depuis la racine de la branche `main`.
Le fichier `CNAME` porte le domaine, `.nojekyll` sert les fichiers tels quels.

À faire une fois :

1. **DNS** (chez le registrar de `erwanguillou.me`) : un enregistrement `CNAME`
   `battleship` → `erwan-design.github.io`
2. **GitHub** → dépôt `dead-reckoning` → *Settings* → *Pages* :
   *Source* = *Deploy from a branch*, branche `main`, dossier `/ (root)` ;
   *Custom domain* = `battleship.erwanguillou.me` ; cocher *Enforce HTTPS*
   (disponible quelques minutes après la vérification du DNS)

Ensuite, chaque push sur `main` met le jeu à jour.

## Ce qu'il y a dedans

**Un seul fichier HTML**, `index.html`, et three.js chargé depuis un CDN. Rien d'autre.

- **Eau** — houle de Gerstner, plan tessellé en fonction de la distance, sillages,
  marques de tir, grille de jeu tracée dans le shader
- **Ombres** — capsules analytiques plutôt qu'une shadow map, plus des ombres 2D
  projetées pour les balises
- **Post-traitement** — bloom écrit à la main, tonemap ACES, étalonnage bi-ton,
  vignettage, grain, encodage sRGB manuel
- **Deux flottes** — moderne (destroyer, porte-avions, croiseur, escorteur, sous-marin)
  et XVIIe siècle (galion, flûte, vaisseau de ligne, pinasse, ketch), avec coques,
  gréements et voiles entièrement paramétriques
- **Trois environnements** — Galion, Squall, Nuit, en fondu croisé
- **Son** — WebAudio procédural : bruit rose filtré, effet Doppler, retard à la distance

## Les commandes

Le HUD est à droite de l'écran.

| | |
|---|---|
| **Plateau** | bascule entre votre formation et le plateau adverse |
| **Radar** | balayage sur le plot |
| **Contacts** | les échos ne s'allument que sous le faisceau |
| **Impacts** | le relevé des tirs |
| **Son** | coupe ou rétablit le bus audio |
| **Missile / Catapulte / Strike / Sink** | les manœuvres |
| **Reset** | remet le plateau à zéro |
| **Scène / Caméra** | ouvrent leurs menus |

Navigation : glisser pour orbiter, molette pour la distance, maj-glisser pour déplacer,
`r` pour revenir au cadrage d'origine.

## Direction artistique

3D stylisée réaliste-douce, géométrie lisse sans facettes visibles, un seul soleil très
bas avec de longues ombres douces, partage chaud/froid entre lumière et ombre, fondu
atmosphérique marqué vers l'horizon, et des accents sombres épars sur un grand champ
lumineux presque vide.
