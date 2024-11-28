# API-algorithmes-traitement-de-maillage-pour-Blender

**Clonage du dépôt**
```console
git clone --recursive https://github.com/DevDarkstar/API-algorithmes-traitement-de-maillage-pour-Blender.git
```
**Compilation**
```console
./setup.bash
```
L'extension Blender générée est une archive compressée au format .zip et se situe dans le dossier *api_traitements_maillage*.  
  
Nécessite d'avoir au préalable un environnement de développement CGAL (installation de gmp, mpfr et de la bibliothèque Boost) pour pouvoir compiler le programme. De plus, pour que le module Python généré soit reconnu par Blender, la version de Python utilisée par Pybind11 lors de la compilation doit être similaire à celle utilisée par Blender en interne (mêmes versions majeure et mineure).
*(En cours de développement)*
