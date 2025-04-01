# API-algorithmes-traitement-de-maillage-pour-Blender

### Prérequis *(Linux)*
  * *cmake* pour la compilation;
  * *gmp*, *mpfr* et *boost* pour l'environement CGAL.
```console
sudo apt-get install libgmp-dev libmpfr-dev libboost-all-dev
```
 
### Clonage du dépôt
```console
git clone --recursive https://github.com/DevDarkstar/API-algorithmes-traitement-de-maillage-pour-Blender.git
```
### Compilation
```console
./setup.bash
```
L'extension Blender générée est une archive compressée au format .zip et se situe dans le dossier *api_traitements_maillage*.  

⚠️**Important** : pour que le module Python généré soit reconnu par Blender, la version de Python utilisée par Pybind11 lors de la compilation doit être similaire à celle utilisée par Blender en interne (mêmes versions majeure et mineure).

### Installation
L'ajout de l'extension dans Blender nécessite d'avoir préalablement installé le module *PyMeshLab* via l'exécution du script *install_pymeshlab.py* dans l'onglet *Scripting* du logiciel.
Une fois l'installation du module effectuée et Blender redémarré, vous pouvez installer l'extension (archive au format .zip).

*(En cours de développement)*
