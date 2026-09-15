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

**Le jeu publié** — sur `battleship.erwanguillou.me`, ou n'importe où avec `?prod` : Title → Deployment (contre la machine : difficulté, règles,
théâtre) → Match → After action. Pas de menu *Screens*, pas de *Debug*, pas de bouton
de cadrage, pas de split sur Deployment et After action. Les écrans Battle (bac à sable)
et Capture ne sont pas accessibles. En cas de panne (three.js qui ne charge pas, WebGL
absent, erreur, perte du contexte graphique), un message propose de recharger.

**L'atelier** — partout ailleurs (site de test, serveur local), ou avec `?dev` sur le
site publié : tous les écrans, le bac à sable Battle, le tiroir Debug.

Le mode dépend de l'adresse, pas de la branche : le même `index.html` est le jeu sur le
domaine et l'atelier sur le site de test.

## Branches

| | | En ligne |
|---|---|---|
| `main` | Le travail en cours. On y pousse librement. | nulle part |
| `test` | La version à essayer, avec les menus *Screens* et *Debug*. | adresse de test Cloudflare (`…workers.dev`) |
| `prod` | Le jeu publié, sans les outils. | `battleship.erwanguillou.me` |

Le chemin d'une version : `main` → `test` (on essaie en ligne) → `prod` (on publie).

**Passer une version à l'étape suivante** (GitHub Desktop) : *Current branch* → la branche
d'arrivée (`test` ou `prod`) → *Branch* → *Merge into current branch…* → la branche de
départ (`main` ou `test`) → *Push origin*. Cloudflare redéploie tout seul (~1 min).
Revenir ensuite sur `main` pour continuer à travailler.

**Revenir en arrière** : remettre `prod` sur le commit de la version précédente et pousser.

## Mise en ligne (Cloudflare)

Le jeu est servi par un **Worker Cloudflare en fichiers statiques** (`battleship-duo`),
relié à ce dépôt : un push sur `prod` met à jour le site publié, un push sur `test`
met à jour l'adresse de test.

- `wrangler.toml` — nom du Worker et dossier servi (la racine du dépôt)
- `.assetsignore` — ce qui n'est **pas** mis en ligne : README, design system, règles,
  maquettes `ui-partie/`, fichiers de configuration

Mise en place (une fois), dans le tableau de bord Cloudflare :

1. *Workers & Pages* → *Create* → importer un dépôt Git → `erwan-design/dead-reckoning`.
   Nom du projet : `battleship-duo` (le même que dans `wrangler.toml`). Pas de commande
   de build ; commande de déploiement : `npx wrangler deploy`.
2. Le Worker créé → *Settings* → *Build* → *Branch control* : branche de production = `prod` ;
   activer les builds des autres branches (*non-production branch builds*), pour que `test`
   ait son adresse de prévisualisation (visible dans *Deployments*, en `…workers.dev`).
3. *Settings* → *Domains & Routes* → *Add* → *Custom domain* → `battleship.erwanguillou.me`.
   La zone `erwanguillou.me` est déjà chez Cloudflare : l'enregistrement DNS est créé tout seul.

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
